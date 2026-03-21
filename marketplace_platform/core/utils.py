from django.apps import AppConfig
from django.db import models
from django.contrib import messages
from django.contrib.postgres.fields import ArrayField
from django.http import HttpRequest
from django.utils import timezone
from typing import Type, Any
from django.forms import modelform_factory
from django.utils.safestring import mark_safe

READONLY_FIELDS = ['id', 'date_joined', 'last_login']

def create_draft_entry(headers, selected_model: Type[models.Model], previous_data=None ) -> dict[str, Any]:
    """
    Generates the default data for a blank "Draft" row with default values.
    Sets id to "NEW" to signal creation of new entry on update.

    This allows for modification of the entry before submission to DB, 
    bypassing the need for extensive default value handling.
    """
    previous_data = previous_data or {}
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
        if field_name in previous_data:
            base_value = previous_data[field_name]
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
        })

    # Set id to NEW to flag as new entry on update
    return {'id': 'NEW', 'cells': draft_cells}


def handle_management_post(request: HttpRequest, app_config: AppConfig, selected_model_name):
    """
    Handles Update and Delete POST requests for management view.
    Update - Ensure that data added is clean and fits model field constraitns.
    """
    model = app_config.get_model(selected_model_name)
   
    # DELETE
    if 'delete' in request.POST:
        delete_id = request.POST.get('delete')

        if delete_id == 'NEW':
            previous_attempt = request.session.get('previous_attempt', {})
            previous_attempt.get(selected_model_name, {}).pop('NEW', None)
            request.session.modified = True
            messages.info(request, "Draft discarded.")
            return True 
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
            exclude_fields = ['id', 'password', 'date_joined', 'last_login']
            DynamicForm = modelform_factory(model, exclude=exclude_fields)

            #Extract unqiue row_ids and iterate through rows
            # Row ids are of format 'cell_b502c12b-...-b717b0e04c1d_<field_name>'
            # print(request.POST.keys())
            row_ids = set(key.split('_')[1] for key in request.POST.keys() if key.startswith('cell_'))
            print(f"[handle_management_post: UPDATE] FOUND {len(row_ids)} row ids.")

            previous_attempts = request.session.setdefault('previous_attempt', {})
            previous_attempts.setdefault(selected_model_name, {})
            request.session.modified = True

            for row_id in row_ids:
                is_new_record = (row_id == 'NEW') # Flag for creating new entry

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
                    instance = model()
                else:
                    instance = model.objects.get(pk=row_id)

                # Apply data to form
                form = DynamicForm(row_data, instance=instance)
                # Use built-in data validation
                if form.is_valid():
                    # Force trigger on pw change
                    password_provided = bool(selected_model_name == 'User' and row_data.get('password'))
                    
                    # Validate if something has changed
                    if form.has_changed() or is_new_record or password_provided:
                        saved_record = form.save(commit=False)
                        
                        # User - Validate password and apply built-in password hashing
                        if selected_model_name == 'User' and password_provided:
                            if row_data.get('password') == row_data.get('confirm_password'):
                                saved_record.set_password(row_data.get('password'))
                            else:
                                messages.error(request, f"Passwords do not match for row {str(row_id)[:8]}.")
                                request.session['previous_attempt'][selected_model_name][str(row_id)] = row_data
                                request.session.modified = True 
                                return False
                        try:
                            saved_record.save()  
                            if is_new_record:
                                messages.success(request, f"New {selected_model_name} created!")
                            else:
                                # Manually include 'password' in the text since it's excluded
                                changed_list = list(form.changed_data)
                                if password_provided:
                                    changed_list.append('password')
                                
                                changes = ",".join(changed_list)
                                messages.success(request, f"Updated row {str(row_id)[:8]}: {changes}")
                        except Exception as e:
                            messages.error(request, f"Update error: {e}")
                            return False
                else:
                    # use built-in django validation error
                    # Must mark_safe to render
                    error_html = mark_safe(f"<b>Error on row {str(row_id)[:8]}:</b><br>{form.errors}")
                    messages.error(request, error_html)
                    
                    # Pass data from update attempt back to continue editing
                    request.session['previous_attempt'][selected_model_name][str(row_id)] = row_data
                    request.session.modified = True 
                    return False

            return True
        
        except Exception as e:
            messages.error(request, f"Update error: {e}")
            return False
    return False

def get_management_context(request, selected_model: Type[models.Model], selected_model_name, add_new=False) -> dict[str, Any]:
    """
    Construct display data for selected model for management view
    """
    
    fields = selected_model._meta.fields
    headers = [field.name for field in selected_model._meta.fields]
    if 'id' in headers:
        headers.remove('id')
        final_headers = ['id'] + headers
    else:
        final_headers = headers
    records = selected_model.objects.all()
    
    # Fetch FKs for drop-down selection
    foreign_key_options = {}
    for field in fields:
        if isinstance(field, models.ForeignKey):
            # Stores as list of tuples: (ID, String)
            foreign_key_options[field.name] = [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()]

    previous_attempt_store = request.session.get('previous_attempt', {}).get(selected_model_name, {})
    rows = []
    for record in records:
        row_id = str(record.pk)
        previous_attempt = previous_attempt_store.get(row_id, {})
        row_cells = []

        for field_name in final_headers:
            field = selected_model._meta.get_field(field_name)

            # If applicable, use values entered from previous attempt
            # Else fallback to db
            if field_name in previous_attempt:
                raw_val = previous_attempt[field_name]
            else:
                raw_val = getattr(record, field_name)

            display_val = format_for_display(field, raw_val)
        
            # Set flags for display
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
                cell_data['fk_id'] = str(getattr(record, f"{field.name}_id"))
                cell_data['options'] = foreign_key_options[field.name]
            if cell_data['is_choice']:
                cell_data['choice_options'] = field.choices

            row_cells.append(cell_data)

        rows.append({'id': record.pk, 'cells': row_cells})

    # Add new draft row
    if add_new:
        draft_data = create_draft_entry(final_headers, selected_model, previous_attempt_store.get('NEW', {}))
        # rows.insert(0, draft_data)
        rows.append(draft_data)

    return {'headers': final_headers, 'rows': rows}
    
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
        if isinstance(field, models.DateTimeField):
            display_value = raw_value.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            display_value = raw_value.strftime('%Y-%m-%d')

    elif field.name == 'password':
        display_value = raw_value[20:25]  
    else:
        display_value = raw_value

    return display_value
        