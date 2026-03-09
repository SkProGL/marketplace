from django.apps import AppConfig
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid
from django.utils import timezone

def handle_management_post(request, app_config, selected_model_name):
    """
    Handles Create, Update and Delete POST requests for management view.
    """
    model = app_config.get_model(selected_model_name)
    target_record_id = request.POST.get('record_id')

    # CREATE
    if 'add_entry' in request.POST:
        fields = {}
        
        # Define default values for each field type
        default_values = {
            models.IntegerField: 0,
            models.DecimalField: 0.00,
            models.FloatField: 0.0,
            models.BooleanField: False,
            models.DateTimeField: timezone.now(),
            models.DateField: timezone.now().date(),
            models.CharField: "---",
            models.TextField: "---",
        }

        for field in model._meta.fields:
            if not field.blank and not field.null and not field.primary_key:
                # Handle unique CharFields (such as username)
                if field.unique and isinstance(field, models.CharField):
                    unique_id = uuid.uuid4().hex
                    fields[field.name] = f"{selected_model_name}_{unique_id[:10]}"
                    continue

                # Handle Foreign Keys
                if isinstance(field, models.ForeignKey):
                    fields[field.name] = field.related_model.objects.first()
                    continue

                if getattr(field, 'choices', None):
                    fields[field.name] = field.choices[0][0]
                    continue
                
                if field.has_default():
                    fields[field.name] = field.get_default()
                    continue

                # Match againts dict of defaults
                for field_class, default_val in default_values.items():
                    if isinstance(field, field_class):
                        fields[field.name] = default_val
                        break

        if selected_model_name == 'User':
            # Built-in method for creating AbstractUser
            user = model.objects.create_user(**fields)
            user.set_password('password') 
            user.save()
        else:
            # Unpack details to create new model object instance
            model.objects.create(**fields)
        return True
    
    # DELETE
    elif 'delete_id' in request.POST:
        try:
            model.objects.filter(pk=target_record_id).delete()
        except Exception as e:
            print(f"FAILED TO DELETE: {e}")

    # UPDATE
    elif 'update_id' in request.POST and target_record_id:
        try:
            # Fetch specific record
            record = model.objects.get(pk=target_record_id )
            
            for field in model._meta.fields:
                # Construct the exact name of the input box from your HTML
                input_name = f"cell_{target_record_id }_{field.name}"
                # print(f"{request.POST})
                
                if input_name in request.POST:
                    raw_value = request.POST.get(input_name)
                    # Field specific handling

                    # Skip password
                    # TODO add proper password form
                    if field.name == 'password':
                        continue
                    
                    # FKs
                    if isinstance(field, models.ForeignKey):
                        # Django expects the ID
                        if raw_value:
                            setattr(record, f"{field.name}_id", raw_value)    

                    # Dates
                    elif isinstance(field, (models.DateField, models.DateTimeField)):
                        if not raw_value: 
                            if field.null: # If the database allows it to be empty
                                setattr(record, field.name, None)
                        else:
                            setattr(record, field.name, raw_value)
                    # Arrays
                    elif isinstance(field, ArrayField):
                        # Strip out any brackets or quotes
                        cleaned_str = raw_value.strip("[]'\" ")
                        if cleaned_str:
                            # Split by comma into a list
                            array_val = [item.strip() for item in cleaned_str.split(',')]
                            setattr(record, field.name, array_val)
                        else:
                            # if empty, save empty list
                            setattr(record, field.name, list())
                    # Bools
                    elif isinstance(field, models.BooleanField):
                        # Convert to boolean
                        bool_val = str(raw_value).strip().lower() in ['true', '1', 'yes']
                        setattr(record, field.name, bool_val)
                    else:
                        setattr(record, field.name, raw_value)
            record.save()
            return True
        except Exception as e:
            print(f"Failed to update: {e}")
            return False
    return False

def get_management_context(selected_model):
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

    rows = []
    for record in records:
        row_cells = []
        for field_name in final_headers:
            field = selected_model._meta.get_field(field_name)
            is_fk = isinstance(field, models.ForeignKey)
            is_bool = isinstance(field, models.BooleanField)
            is_date = isinstance(field, (models.DateTimeField, models.DateField))
            is_choice = bool(getattr(field, 'choices', None)) # Extract choices as defined in models

            raw_val = getattr(record, field.name)
            # Convert obects into strings
            if is_date and raw_val:
                display_val = raw_val.strftime('%Y-%m-%d')
            #TODO Add password reset logic
            elif field_name == 'password':
                display_val = "********"  
            else:
                display_val = raw_val

            cell_data = {
                'name': field.name,
                'value': display_val,
                'is_fk': is_fk,
                'is_bool': is_bool,
                'is_date': is_date,
                'is_choice': is_choice,
            }
            
            if is_fk:
                cell_data['fk_id'] = str(getattr(record, f"{field.name}_id"))
                cell_data['options'] = foreign_key_options[field.name]
            if is_choice:
                cell_data['choice_options'] = field.choices

            row_cells.append(cell_data)

        rows.append({'id': record.pk, 'cells': row_cells})
            
    return {'headers': final_headers, 'rows': rows}
    