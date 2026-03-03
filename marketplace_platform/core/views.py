from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from core.forms import LoginForm, ProductForm
from .models import User, Product, Order, Recipe, User
from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone

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
    # For CRUD model selection 
    # TODO: Convert from brute force load
    models = apps.get_app_config('core').get_models()

    db_data= {} 
    
    # Extract ALL data for display, for now
    for model in models:
        model_name = model.__name__
        headers = [field.name for field in model._meta.fields]
        records = model.objects.all()
        
        # Build records
        rows = []
        for record in records:
            row_values = [getattr(record, h) for h in headers]
            rows.append({
                'id': record.pk,
                'cells': row_values
            })

        db_data[model_name] = {
            'headers': headers,
            'rows': rows,
        }

    # Pull specific records for selected models
    selected_model = request.GET.get('model')

    # Select data for specified model
    selected_data = db_data.get(selected_model)


    # CRUD actions
    if request.method == 'POST' and selected_model:
        
        model = apps.get_model('core', selected_model)
        
        # DELETE
        if 'delete_id' in request.POST:
            model.objects.filter(pk=request.POST.get('delete_id')).delete()

            
        # CREATE
        # TODO: Resolve this temporary workaround to more robust solution
        elif 'add_entry' in request.POST:
            model = apps.get_model('core', selected_model)
            
            # Get a dummy user for the mandatory FKs
            first_user = User.objects.first()
            first_prod = Product.objects.first()
            first_order = Order.objects.first()

            params = {}
            
            # Logic to satisfy the database constraints
            if selected_model == 'Order':
                params = {
                    'customer': first_user, 
                    'product': first_prod, 
                    'num_purchased': 1, 
                    'total_price': 0, 
                    'delivery_date': timezone.now()
                }
            elif selected_model == 'Product':
                params = {'producer': first_user, 'name': "New Product", 'price': 0, 'food_miles': 0, 'stock': 0}
            elif selected_model == 'Review':
                params = {'user': first_user, 'order': first_order, 'rating': 5, 'title': "New Review"}
            elif selected_model == 'StoryPost':
                params = {'user': first_user, 'content': "Content", 'image': "path/to/image", 'date_posted': timezone.now()}
            elif selected_model == 'Recipe':
                new_recipe = model.objects.create(
                        user=first_user, 
                        title="New Recipe", 
                        description="Description", 
                        instructions="Instructions", 
                        season=Recipe.Season.SPRING
                    )               
                if first_prod:
                    new_recipe.ingredients.add(first_prod)
                return redirect(f"{request.path}?model={selected_model}")
            elif hasattr(model, 'user'): 
                params = {'user': first_user, 'title': "New item", 'content': "...", 'description': "..."}

            # if no pre-existing user, create one
            if first_user:
                model.objects.create(**params) # ** => unpack

        return redirect(f"{request.path}?model={selected_model}")


    content = {
            'db_data': db_data,
            'selected_model': selected_model,
            'selected_data': selected_data, # This contains 'records' and 'headers'
        }

    return render(request, 'management.html', content)

