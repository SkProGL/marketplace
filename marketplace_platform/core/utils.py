from django.apps import AppConfig
from django.db import models
from django.contrib import messages
from django.contrib.postgres.fields import ArrayField
from django.http import HttpRequest
from django.utils import timezone
from typing import Type, Any
from django.forms import modelform_factory
from django.utils.safestring import mark_safe
from django.http import HttpRequest

READONLY_FIELDS = ['id', 'date_joined', 'last_login']

def create_draft_entry(headers, selected_model: Type[models.Model], cached_update_attempt=None ) -> dict[str, Any]:
    """
    Generates the default data for a blank "Draft" row with default values.
    Sets id to "draft" to signal creation of new entry on update.

    This allows for modification of the entry before submission to DB, 
    bypassing the need for extensive default value handling.
    """
    # Convert none to {}
    # cached_update_attempt = cached_update_attempt or {}
    draft_cells = []

    # Define default values for each field type
    default_values = {
        models.IntegerField: 0,
        models.DecimalField: 0.00,
        models.FloatField: 0.0,
        models.BooleanField: False,
        models.DateTimeField: timezone.now(),
        models.DateField: timezone.now().date(),
        models.CharField: "",
        models.TextField: "", 
        ArrayField: [],
    }

    for field_name in headers:
        field = selected_model._meta.get_field(field_name)

        # Use data from previous attempt or default as defined in models.py, otherwise defer to default defined above
        if field_name in cached_update_attempt:
            base_value = cached_update_attempt[field_name]
        elif field.has_default():
            base_value = field.get_default()
        else:
            for field_class, default_val in default_values.items():
                if isinstance(field, field_class):
                    base_value = default_val
                    break
        
        # Get field name, values and set appropriate flags for correct display 
        draft_cells.append({
            'name': field.name,
            'value': base_value, 
            'is_fk': isinstance(field, models.ForeignKey),
            'is_bool': isinstance(field, models.BooleanField),
            'is_date': isinstance(field, (models.DateTimeField, models.DateField)),
            'is_choice': bool(getattr(field, 'choices', None)),
            'options': [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()] if isinstance(field, models.ForeignKey) else [],
            'choice_options': field.choices if hasattr(field, 'choices') else [],
            'is_readonly': field_name in READONLY_FIELDS,
            'is_password': field.name == 'password',
            'is_new': True,
        })

    # Set id to draft to flag as new entry on update
    return {'id': 'draft', 'cells': draft_cells}


def handle_management_post(request: HttpRequest, app_config: AppConfig, selected_model_name):
    """
    Handles Update and Delete POST requests for management view.
    Update - Ensure that data added is clean and fits model field constraitns.
    """
    model = app_config.get_model(selected_model_name)
   
    # DELETE
    if 'delete' in request.POST:
        delete_id = request.POST.get('delete')

        if delete_id == 'draft':
            # If deleting a draft  entry, simply pop the session update attempt 
            cached_update_attempt = request.session.get('cached_update_attempt', {})
            cached_update_attempt.get(selected_model_name, {}).pop('draft', None)
            request.session.modified = True
            messages.info(request, "Draft discarded.")
            return True 
        else:
            try:
                model.objects.filter(pk=delete_id).delete()
                messages.warning(request, f"Row {delete_id} deleted.")
                return True
            except Exception as e:
                print(f"FAILED TO DELETE: {e}")
                return False
            
    # UPDATE
    elif 'update' in request.POST:
        try:
            # Create a dynamic form class for current model
            # Exclude ID and 'password' for special handling
            exclude_fields = ['id', 'password', 'date_joined', 'last_login', 'products']
            DynamicForm = modelform_factory(model, exclude=exclude_fields)

            #Extract unqiue row_ids and iterate through rows
            # Row ids are of format 'cell_b502c12b-...-b717b0e04c1d_<field_name>'
            # print(request.POST.keys())
            row_ids = set(key.split('_')[1] for key in request.POST.keys() if key.startswith('cell_'))
            print(f"[handle_management_post: UPDATE] FOUND {len(row_ids)} row ids.")

            # Grab data if applicable, otherwise initialise store for update attempt
            # setdefautl here either extracts if key exists; or creates (as empty dict) if it does not.
            cached_update_attempt = request.session.setdefault('cached_update_attempt', {})
            cached_update_attempt.setdefault(selected_model_name, {})
            request.session.modified = True

            for row_id in row_ids:
                is_new_record = (row_id == 'draft') # Flag for creating new entry

                # Use record prefix to extract the field names
                # Append key/values pairs to row_data 
                row_data = {}
                prefix = f"cell_{row_id}_"
                for key, value in request.POST.items():
                    if key.startswith(prefix):
                        field_name = key.split(prefix)[1]
                        row_data[field_name] = value
                print(f"\n {row_data}\n")

                if is_new_record:
                    model_instance = model()
                else:
                    model_instance = model.objects.get(pk=row_id)

                # Apply data to model form
                form = DynamicForm(row_data, instance=model_instance)

                # Use built-in data validation
                if form.is_valid():
                    # Force trigger on pw change
                    password_provided = bool(selected_model_name == 'User' and row_data.get('password'))
                    
                    # Validate if something has changed
                    if form.has_changed() or is_new_record or password_provided:
                        saved_record = form.save(commit=False)         

                        # User - Validate entered passwords and apply built-in password hashing
                        if selected_model_name == 'User' and password_provided:
                            if row_data.get('password') == row_data.get('confirm_password'):
                                saved_record.set_password(row_data.get('password'))
                            else:
                                messages.error(request, f"Passwords do not match for row {str(row_id)[:8]}.")
                                # Store data from update attempt to continue editing
                                request.session['cached_update_attempt'][selected_model_name][str(row_id)] = row_data
                                request.session.modified = True 
                                return False
                        try:
                            saved_record.save()  
                            if is_new_record:
                                messages.success(request, f"New {selected_model_name} created!")
                            else:
                                # Signal success field updates
                                # Manually include 'password' in the text since it's excluded
                                changed_list = list(form.changed_data)
                                if password_provided:
                                    changed_list.append('password')
                                
                                changes = ",".join(changed_list)
                                messages.success(request, f"Updated row {str(row_id)[:8]}: {changes}")
                            # Clear update attempt on success
                            cached_update_attempt = request.session.get('cached_update_attempt', {})
                            cached_update_attempt.pop(selected_model_name, None)
                            request.session.modified = True
                        except Exception as e:
                            messages.error(request, f"Update error: {e}")
                            return False
                else:
                    # Signal unsuccesful field updates using built-in django validation error
                    # Must mark_safe to render to html
                    error_html = mark_safe(f"<b>Error on row {str(row_id)[:8]}:</b><br>{form.errors}")
                    messages.error(request, error_html)
                    
                    # Store data from update attempt to continue editing
                    request.session['cached_update_attempt'][selected_model_name][str(row_id)] = row_data
                    request.session.modified = True 
                    return False
        
            return True
        
        except Exception as e:
            messages.error(request, f"Update error: {e}")
            return False
    return False

def get_management_context(request:HttpRequest, selected_model: Type[models.Model], selected_model_name, add_new=False) -> dict[str, Any]:
    """
    Construct display data for selected model for management view table.
    Additionally handles row sorting logic.
    """
    
    # Construct headeres for selected mdoels
    fields = selected_model._meta.fields
    headers = [field.name for field in selected_model._meta.fields]
    if 'id' in headers:
        headers.remove('id')
        final_headers = ['id'] + headers
    else:
        final_headers = headers

    # Extract all records from model
    records = selected_model.objects.all()

    # Sorting logic  
    # Extract direction and header to sort by
    sort_field = request.GET.get('sortby')
    sort_direction = request.GET.get('direction', 'ascending')
    
    # Reorder records based on direction and field
    if sort_field:
        if sort_direction == 'descending':
            records = records.order_by(f'-{sort_field}')
        else:
            records = records.order_by(sort_field)

    # Fetch FKs for drop-down selection fields
    foreign_key_options = {}
    for field in fields:
        if isinstance(field, models.ForeignKey):
            # Stores as list of tuples: (ID, String)
            foreign_key_options[field.name] = [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()]

    # Extract previous cached update attempt/s data for model
    cached_update_attempt = request.session.get('cached_update_attempt', {}).get(selected_model_name, {})
    
    # Populate records for display
    rows = []
    for record in records:
        # If applicable, use cell values stored from previous edit attempt in session
        # Else fallback to db
        row_id = str(record.pk)
        cached_row_update_attempt = cached_update_attempt.get(row_id, {})

        row_cells = []
        for field_name in final_headers:
            field = selected_model._meta.get_field(field_name)
            if field_name in cached_row_update_attempt:
                raw_val = cached_row_update_attempt[field_name]
            else:
                raw_val = getattr(record, field_name)

            display_val = format_for_display(field, raw_val)
        
            # Set flags for displaying cells in correct format
            cell_data = {
                'name': field.name,
                'value': display_val,
                'is_fk': isinstance(field, models.ForeignKey),
                'is_bool': isinstance(field, models.BooleanField),
                'is_date':  isinstance(field, (models.DateTimeField, models.DateField)),
                'is_choice': bool(getattr(field, 'choices', None)),
                'is_readonly': field.name in READONLY_FIELDS,
                'is_password': field.name == 'password',
            }
            
            # Define drop-down options
            if cell_data['is_fk']:
                if field_name in cached_row_update_attempt:
                    cell_data['selected_fk_id'] = str(raw_val)
                else:
                    cell_data['selected_fk_id'] = str(getattr(record, f"{field.name}_id"))
                cell_data['fk_options'] = foreign_key_options[field.name]
            if cell_data['is_choice']:
                cell_data['choice_options'] = field.choices

            row_cells.append(cell_data)

        rows.append({'id': record.pk, 'cells': row_cells})

    # If new row button selected, add draft row
    if add_new:
        draft_data = create_draft_entry(final_headers, selected_model, cached_update_attempt.get('draft', {}))
        # rows.insert(0, draft_data) add to top for visibility?
        rows.append(draft_data)

    return {'headers': final_headers, 'rows': rows, 'current_sort': sort_field, 'current_dir': sort_direction}
    
def format_for_display(field, raw_value):
    """
    Clean raw values for display.
    """
    is_date = isinstance(field, (models.DateTimeField, models.DateField))
    is_array = isinstance(raw_value, (list, tuple))
    if raw_value is None:
        return ""
    
    elif is_array:
        display_value =  ",".join(map(str, raw_value))
    
    elif is_date:
        if isinstance(raw_value, str):
            return raw_value
        return raw_value.strftime('%Y-%m-%d')

    elif field.name == 'password':
        display_value = raw_value[20:29] + "..."  
    else:
        display_value = raw_value

    return display_value
        
