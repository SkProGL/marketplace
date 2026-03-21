from django.apps import apps
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import HttpResponse
from django.shortcuts import redirect, render

from core.forms import LoginForm, ProductForm, SignupForm
from core.utils import get_management_context, handle_management_post
from .models import Product

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
            print(f"\033[42m\033[30mform valid\033[0m")
            product = form.save(commit=False)
            if request.user.is_authenticated:
                product.producer = User.objects.get(pk=request.user.pk)
                product.save()
                return redirect('home')
            else:
                return HttpResponse("You must be logged in to upload.")
        else:
            print(f"\033[43m\033[30m{form.errors=}\033[0m")

    else:
        form = ProductForm()
    return render(request, 'inventory_upload.html', {'form': form})


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            print("SIGNUP SUCCESS")

            print(f"\033[42m\033[30msignup success\033[0m")
            print("Created user:", {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "postcode": user.postcode,
                "category": user.category,
            })
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("home")

        print(f"\033[43m\033[30msignup failed\033[0m")
        print("post data:", dict(request.POST))
        print("form errors:", form.errors)
        print("non field errors:", form.non_field_errors())
        messages.error(request, "Signup failed. Please fix the errors below.")
    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})


def invoice_view(request):
    return render(request, 'invoice.html')


def management_view(request):
    # Construct list of model names
    # Pull specific records for selected model
    app_config = apps.get_app_config('core')
    model_names = [model.__name__ for model in app_config.get_models()]
    selected_model_name = request.GET.get('model')

    # Handle POST actions (Create, Update & Delete)
    if request.method == 'POST' and selected_model_name:
        success = handle_management_post(
            request, app_config, selected_model_name)
        if success:
            # Pop attempt record on success
            previous_attempt = request.session.get('previous_attempt', {})
            previous_attempt.pop(selected_model_name, None)
            request.session.modified = True
            return redirect(f"{request.path}?model={selected_model_name}")

    # Fetch data for display
    # Set flag if new draft row has been created
    previous_attempts = request.session.get(
        'previous_attempt', {}).get(selected_model_name, {})
    add_new = request.GET.get(
        'new_row') == 'true' or 'NEW' in previous_attempts
    selected_data = None
    if selected_model_name:
        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(
            request, selected_model, selected_model_name, add_new)

    return render(request, 'management.html', {
        'model_names': model_names,
        'selected_model_name': selected_model_name,
        'selected_data': selected_data,
    })


def order_history(request):
    return render(request, 'order_history.html')


def community(request):
    return render(request, 'community.html')
