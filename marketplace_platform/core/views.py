from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from core.forms import LoginForm, ProductForm
from core.utils import get_management_context, handle_management_post
from .models import User, Product, Order, Recipe, User
from django.apps import apps
from django.contrib.auth import get_user_model

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
    # Pull specific records for selected model
    app_config = apps.get_app_config('core')
    model_names= [model.__name__ for model in app_config.get_models()]
    selected_model_name = request.GET.get('model')

    # Handle POST actions (Create, Update & Delete)
    if request.method == 'POST' and selected_model_name:
        success = handle_management_post(request, app_config, selected_model_name)
        if success:        
            return redirect(f"{request.path}?model={selected_model_name}")
        
    # Fetch data for display
    selected_data = None
    if selected_model_name:
        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(selected_model)
    
    return render(request, 'management.html', {
            'model_names': model_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
        })

