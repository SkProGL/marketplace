from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from core.forms import LoginForm, ProductForm
from .models import User, Product, Order, Recipe, User
from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
import uuid
from django.contrib.postgres.fields import ArrayField

User = get_user_model()


def home_view(request):
    items = Product.objects.all()  # Fetch all items from Postgres
    return render(request, 'home.html', {'items': items})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Check if these credentials match a user in the DB
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('home')  # Go to the marketplace
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def upload_item(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            print("FORM VALID ✅")
            product = form.save(commit=False)
            if request.user.is_authenticated:
                product.producer = User.objects.get(pk=request.user.pk)
                product.save()
                return redirect('home')
            else:
                return HttpResponse("You must be logged in to upload.")
        else:
            print("FORM ERRORS ❌", form.errors)
    else:
        form = ProductForm()
    return render(request, 'inventory_upload.html', {'form': form})


def signup_view(request):
    return render(request, 'signup.html')


def invoice_view(request):
    return render(request, 'invoice.html')

def management_view(request):
    # Construct list of model names
    app_config = apps.get_app_config('core')
    model_names= [model.__name__ for model in app_config.get_models()]

    # Pull specific records for selected model
    selected_model_name = request.GET.get('model')
    selected_data = None

    # CRUD actions
    if request.method == 'POST' and selected_model_name:
        model = app_config.get_model(selected_model_name)
        
        # DELETE
        if 'delete_id' in request.POST:
            try:
                model.objects.filter(pk=request.POST.get('delete_id')).delete()
            except Exception as e:
                print(f"FAILED TO DELETE: {e}")

        # CREATE
        elif 'add_entry' in request.POST:
            fields = {}
            
            # Define default values for each field type
            default_values = {
                models.IntegerField: 0,
                models.DecimalField: 0.00,
                models.FloatField: 0.0,
                models.BooleanField: False,
                models.DateTimeField: timezone.now(),
                models.DateField: timezone.now().date(),
                models.CharField: "New CharField",
                models.TextField: "New TextField",
            }

            for field in model._meta.fields:
                if not field.blank and not field.null and not field.primary_key:
                    # Handle unique CharFields (such as username)
                    if field.unique and isinstance(field, models.CharField):
                        unique_id = uuid.uuid4().hex
                        fields[field.name] = f"{selected_model_name.lower()}_{unique_id[:10]}"
                        continue

                    # Handle Foreign Keys
                    if isinstance(field, models.ForeignKey):
                        fields[field.name] = field.related_model.objects.first()
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
            return redirect(f"{request.path}?model={selected_model_name}")

        # UPDATE
        elif 'update_id' in request.POST:
            record_id = request.POST.get('update_id')  
            try:
                # Fetch specific record
                record = model.objects.get(pk=record_id)
                
                for field in model._meta.fields:
                    # Construct the exact name of the input box from your HTML
                    input_name = f"cell_{record_id}_{field.name}"
                    # print(f"{request.POST})
                    
                    if input_name in request.POST:
                        raw_value = request.POST.get(input_name)
                        # Field specific handling
                        if isinstance(field, models.ForeignKey):
                            # For ForeignKeys, Django expects the ID
                            if raw_value:
                                setattr(record, f"{field.name}_id", raw_value)    

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

                        elif isinstance(field, models.BooleanField):
                            # Convert to boolean
                            bool_val = str(raw_value).strip().lower() in ['true', '1', 'yes']
                            setattr(record, field.name, bool_val)
                        else:
                            setattr(record, field.name, raw_value)
                record.save()
                
            except Exception as e:
                print(f"Failed to update: {e}")
                
            return redirect(f"{request.path}?model={selected_model_name}")
        
    # Get specified model contents for display
    if selected_model_name:
        model = app_config.get_model(selected_model_name)
        fields = model._meta.fields
        headers = [field.name for field in model._meta.fields]
        records = model.objects.all()
        
        # Fetch FKs for drop-down selection
        foreign_key_options = {}
        for field in fields:
            if isinstance(field, models.ForeignKey):
                # Stores as list of tuples: (ID, String)
                foreign_key_options[field.name] = [(str(obj.pk), str(obj)) for obj in field.related_model.objects.all()]

        rows = []
        for record in records:
            row_cells = []
            for field in fields:
                is_fk = isinstance(field, models.ForeignKey)

                raw_val = getattr(record, field.name)
                # Convert obects into strings
                if isinstance(field, models.DateTimeField) and raw_val:
                    display_val = raw_val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(field, models.DateField) and raw_val:
                    display_val = raw_val.strftime('%Y-%m-%d')
                else:
                    display_val = raw_val
                cell_data = {
                    
                    'name': field.name,
                    'value': display_val,
                    'is_fk': is_fk
                }
                if is_fk:
                    cell_data['fk_id'] = str(getattr(record, f"{field.name}_id"))
                    cell_data['options'] = foreign_key_options[field.name]
                
                row_cells.append(cell_data)

            rows.append({'id': record.pk, 'cells': row_cells})
                
        selected_data = {'headers': headers, 'rows': rows}

    return render(request, 'management.html', {
            'model_names': model_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
        })

