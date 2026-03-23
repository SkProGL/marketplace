from django.apps import apps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import HttpResponse, JsonResponse
from core.forms import LoginForm, ProductForm, SignupForm, CheckoutForm
from core.utils import get_management_context, handle_management_post
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from .models import User, Product, Order, OrderProduct
from django.utils import timezone
from datetime import timedelta,date
# Create your views here.
User = get_user_model()

def get_next_occurrence(order):
    """Calculate the next delivery date based on recurrence type."""
    today = timezone.now().date()
    base = order.delivery_date.date()
    
    if order.recurrence_type == 'Weekly':
        delta = 7
    elif order.recurrence_type == 'Fortnightly':
        delta = 14
    else:
        return None

    # Keep adding delta until we get a future date
    next_date = base
    while next_date <= today:
        next_date += timedelta(days=delta)
    return next_date

@login_required
def recurring_orders(request):
    orders = Order.objects.filter(
        customer=request.user,
        recurring=True
    ).prefetch_related('orderproduct_set__product')

    orders_with_next = []
    for order in orders:
        orders_with_next.append({
            'order': order,
            'next_date': get_next_occurrence(order),
            'items': order.orderproduct_set.all(),
        })

    return render(request, 'recurring_orders.html', {
        'orders_with_next': orders_with_next
    })

@login_required
def modify_next_occurrence(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == 'POST':
        # Create a brand new one-off order for next occurrence only
        next_date = get_next_occurrence(order)
        new_order = Order.objects.create(
            customer=request.user,
            total_price=order.total_price,
            delivery_date=timezone.make_aware(
                timezone.datetime.combine(next_date, timezone.datetime.min.time())
            ),
            order_status='PENDING',
            recurring=False,  # This is a one-off modification, not a template
        )

        # Copy items with updated quantities from POST
        for op in order.orderproduct_set.all():
            new_qty = int(request.POST.get(f'qty_{op.id}', op.numPurchased))
            OrderProduct.objects.create(
                order=new_order,
                product=op.product,
                numPurchased=new_qty,
            )

        messages.success(request, "Next occurrence updated. The recurring template is unchanged.")
        return redirect('recurring_orders')

    return render(request, 'modify_occurrence.html', {
        'order': order,
        'next_date': get_next_occurrence(order),
        'items': order.orderproduct_set.all(),
    })
    
@login_required
def order_history(request):
    # Fetch orders for the logged-in user, sorted by most recent first
    orders = Order.objects.filter(customer=request.user).order_by('-order_date')
    return render(request, 'order_management.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def reorder(request, order_id):
    old_order = get_object_or_404(Order, id=order_id, customer=request.user)
    # Logic to add items to cart would go here
    # Check availability and add to session or Cart model
    return redirect('cart')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    
    # If memory is empty, kick them back home
    if not cart:
        messages.error(request, "You haven't selected any items.")
        return redirect('home')

    # 1. Gather all products and calculate the total price
    total_price = 0
    cart_items = []
    
    for pid, qty in cart.items():
        product = get_object_or_404(Product, id=pid)
        total_price += product.price * qty
        cart_items.append({'product': product, 'quantity': qty})

    min_delivery_date = (timezone.now() + timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M')

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Read recurring fields from POST
            is_recurring = request.POST.get('recurring') == 'true'
            recurrence_type = request.POST.get('recurrence_type', 'None')
            recurrence_day = request.POST.get('recurrence_day', None)
            # 2. Create the ONE main Order
            new_order = Order.objects.create(
                customer=request.user,
                total_price=total_price,
                delivery_date=form.cleaned_data['delivery_date'],
                order_status='PENDING',
                recurring=is_recurring,
                recurrence_type=recurrence_type if is_recurring else 'None',
                recurrence_day=int(recurrence_day) if is_recurring and recurrence_day else None,
            )
            
            # 3. Loop through the memory to link ALL items to this order
            for item in cart_items:
                OrderProduct.objects.create(
                    order=new_order,
                    product=item['product'],
                    numPurchased=item['quantity']
                )
            
            # Clear the memory now that the order is placed!
            request.session['cart'] = {}
            
            messages.success(request, "Order placed successfully!")
            return redirect('order_history')
    else:
        form = CheckoutForm()

    return render(request, 'checkout.html', {
        'form': form, 
        'cart_items': cart_items, # Pass the list to HTML so you can show what they are buying
        'total_price': total_price,
        'min_delivery_date': min_delivery_date,
        'user_address': request.user.address,
        'user_postcode': request.user.postcode
    })
    
def home_view(request):
    items = Product.objects.all()  # Fetch all items from Postgres
    return render(request, 'home.html', {'items': items})

def add_to_cart(request, product_id):
    if request.method == 'POST':
        # Get the current memory, or start a blank dictionary
        cart = request.session.get('cart', {})
        
        quantity = int(request.POST.get('quantity', 1))
        pid = str(product_id) # Session keys must be strings

        # Add or update the quantity
        if pid in cart:
            cart[pid] += quantity
        else:
            cart[pid] = quantity

        # Save it back to the session
        request.session['cart'] = cart
        messages.success(request, "Item added!")
        
    return redirect('home')

def clear_cart(request):
    request.session['cart'] = {}
    messages.success(request, "Cart cleared.")
    return redirect('home')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_data = form.cleaned_data
            username = login_data.get('username')
            password = login_data.get('password')

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

def management_view(request: HttpResponse):
    # Construct list of model names
    # Pull specific records for selected model for display
    app_config = apps.get_app_config('core')
    model_names = [model.__name__ for model in app_config.get_models()]
    selected_model_name = request.GET.get('model')
    print(f"\n[management_view] Selected model is: {selected_model_name}")

    # Handle POST actions (Create, Update & Delete)
    if request.method == 'POST' and selected_model_name:
        success = handle_management_post(request, app_config, selected_model_name)
        if success:        
            # Draft attempts to update record are cachedin session for continued editing
            # Pop this cached data on successful modification
            cached_update_attempts = request.session.get('cached_update_attempt', {})
            cached_update_attempts.pop(selected_model_name, None)
            request.session.modified = True
            return redirect(f"{request.path}?model={selected_model_name}")
        
    # Fetch data for Read display
    # Set flag if new draft row has been created 
    cached_update_attempt = request.session.get('cached_update_attempt', {}).get(selected_model_name, {})
    add_new = request.GET.get('draft') == 'true' or 'draft' in cached_update_attempt
    selected_data = None
    if selected_model_name:
        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(request, selected_model, selected_model_name, add_new)
    

    return render(
            request, 'management.html', {
            'model_names': model_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
        })


def order_history(request):
    return render(request, 'order_history.html')


def community(request):
    return render(request, 'community.html')

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