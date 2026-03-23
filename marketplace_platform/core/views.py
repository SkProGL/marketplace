from django.apps import apps
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from core.forms import LoginForm, ProductForm, SignupForm
from core.utils import get_low_stock_products, get_management_context, handle_management_post
from core.permissions import MANAGE_MODEL_ACCESS, get_all_models, management_access_required
from django.db import models
from .models import Order, Product
from django.contrib.auth.decorators import login_required

User = get_user_model()


def home_view(request):
    items = Product.objects.all()  # Fetch all items from Postgres
    return render(request, 'home.html', {'items': items})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_data = form.cleaned_data
            email = login_data.get('email')
            password = login_data.get('password')

            # Check if these credentials match a user in the DB
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {email}!")
                return redirect('home')  # Go to the marketplace
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

@login_required
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
                "username": getattr(user, "username", ""),
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "postcode": user.postcode,
                "category": user.category,
                "organisation_name": user.organisation_name,
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

@management_access_required
# Equivalent to: 
# management_view = management_access_required(management_view)
def management_view(request: HttpResponse):
    # Construct list of model names
    # Pull specific records for selected model for display
    
    app_config = apps.get_app_config('core')
    selected_model_name = request.GET.get('model')  
    is_superuser = request.user.is_superuser
    # RBAC - Control access base on user category
    if is_superuser:
        allowed_models = get_all_models()
        user_category = "superuser"
    else:
        user_category = getattr(request.user, 'category', None)
        allowed_models = MANAGE_MODEL_ACCESS.get(user_category, [])
        if callable(allowed_models):
            allowed_models = allowed_models()

        # Ensure that user cnanot bypass filtering via URL
        if selected_model_name and selected_model_name not in allowed_models:
            messages.error(request, f"Access denied.\n {user_category} cannot access this model.")
            return redirect('management')
    
    # Filter returned models based on allowed_models
    model_names = [model.__name__ for model in app_config.get_models() if model.__name__ in allowed_models]
    print(model_names)
    print(f"{user_category} - {allowed_models}")

    print(f"\n[management_view] Selected model is: {selected_model_name}")

    # Handle POST actions (Create, Update & Delete)
    if request.method == 'POST' and selected_model_name:
        success = handle_management_post(
            request, app_config, selected_model_name)
        if success:
            # Draft attempts to update record are cachedin session for continued editing
            # Pop this cached data on successful modification
            cached_update_attempts = request.session.get(
                'cached_update_attempt', {})
            cached_update_attempts.pop(selected_model_name, None)
            request.session.modified = True
            return redirect(f"{request.path}?model={selected_model_name}")

    # Fetch data for Read display
    # Set flag if new draft row has been created
    cached_update_attempt = request.session.get(
        'cached_update_attempt', {}).get(selected_model_name, {})
    add_new = request.GET.get(
        'draft') == 'true' or 'draft' in cached_update_attempt
    selected_data = None
    row_filter = {}
    distinct = False
    readonly_fields = set()
    if selected_model_name:
        # Producer specific handling
        if not is_superuser and user_category == 'Producer' :
            # Get producer account specific rows for selected model
            row_filter = {
                'Product':   {'producer': request.user},
                'Order':     {'orderproduct__product__producer': request.user}, # Order ownership identified via bridging Order => OrderProduct => Product => Producer
                'StoryPost': {'user': request.user},
                'Recipe':    {'user': request.user},
            }.get(selected_model_name, {})
            distinct = selected_model_name == 'Order' # Only need one product
            # Specify Order as read-only, excludiong order_status for Producers
            if selected_model_name == 'Order':
                order_model = app_config.get_model('Order')
                readonly_fields = {field.name for field in order_model._meta.fields if field.name != 'order_status'}
            # Remove id selection fields for producer
            elif selected_model_name in ('Product', 'StoryPost', 'Recipe'): 
                owner_field = 'producer' if selected_model_name == 'Product' else 'user'
                readonly_fields = {owner_field}

        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(request, selected_model, selected_model_name, add_new, row_filter, distinct, readonly_fields)
        
    return render(
        request, 'management.html', {
            'model_names': model_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
        })

@login_required
def order_history(request):
    return render(request, 'order_history.html')

@login_required
def community(request):
    return render(request, 'community.html')

@login_required
def get_order_summary_json(request, order_id):
    """
    For expanded Order view in management panel.
    Extract order_id from URL parameter as defined in urls.
    Return Json data contained comprehensive order details.
    """
    try:
        # Use select_related to fetch all related fk models for speed
        order = Order.objects.select_related('customer').get(pk=order_id)

        # Get products attached to this order for receipt
        items = order.orderproduct_set.all().select_related('product')

        receipt_data = []
        for item in items:
            receipt_data.append({
                'name': item.product.name,
                'qty': item.numPurchased,
                'price': f"{item.product.price:.2f}",
                'total': f"{item.numPurchased * item.product.price:.2f}"
            })

        data = {
            'status': order.order_status,
            'customer_name': order.customer.username,
            'customer_type': order.customer.category,
            'email': order.customer.email,
            'phone': order.customer.phone,
            'address': f"{order.customer.address}, {order.customer.postcode}" if order.customer.address and order.customer.postcode else '',
            'instructions': order.special_instructions,
            'order_date': order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else '',
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else '',
            'recurrence': f"{order.get_recurrence_day_display()} ({order.recurrence_type})" if order.recurring else '',
            'total_price': f"{order.total_price:.2f}",
            'receipt': receipt_data
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': e}, status=404)

