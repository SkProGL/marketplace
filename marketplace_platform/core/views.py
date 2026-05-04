import json
import difflib
from django.db.models import Q, Sum, Min, Subquery, OuterRef
from django.apps import apps
from django.shortcuts import render, get_object_or_404, redirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from core.forms import LoginForm, ProductForm, ProductBatchForm, SignupForm, CheckoutForm
from core.permissions import MANAGE_MODEL_ACCESS, get_all_models, management_access_required
from core.utils import get_management_context, handle_management_post
from .models import User, Product, ProductBatch, Order, OrderProduct
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# Create your views here.
User = get_user_model()
import json

@login_required
def update_cart_ajax(request, product_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        delta = int(data.get('delta', 1))
        cart = request.session.get('cart', {})
        pid = str(product_id)

        cart[pid] = cart.get(pid, 0) + delta
        if cart[pid] <= 0:
            del cart[pid]

        request.session['cart'] = cart
        request.session.modified = True

        # Build full cart item list for the drawer
        cart_items_data = []
        total_price = 0
        if cart:
            batches = ProductBatch.objects.select_related('product').filter(id__in=cart.keys())
            for batch in batches:
                qty = cart.get(str(batch.id), 0)
                subtotal = float(batch.price) * qty
                total_price += subtotal
                cart_items_data.append({
                    'id': str(batch.id),
                    'name': batch.name,
                    'price': float(batch.price),
                    'quantity': qty,
                    'subtotal': round(subtotal, 2),
                    'image': batch.image.url if batch.image else None,
                })

        return JsonResponse({
            'quantity': cart.get(pid, 0),
            'total_items': sum(cart.values()),
            'total_price': round(total_price, 2),
            'cart_items': cart_items_data,
        })


@login_required
def cart_contents(request):
    cart = request.session.get('cart', {})
    cart_items_data = []
    total_price = 0
    if cart:
        batches = ProductBatch.objects.select_related('product').filter(id__in=cart.keys())
        for batch in batches:
            qty = cart.get(str(batch.id), 0)
            subtotal = float(batch.price) * qty
            total_price += subtotal
            cart_items_data.append({
                'id': str(batch.id),
                'name': batch.name,
                'price': float(batch.price),
                'quantity': qty,
                'subtotal': round(subtotal, 2),
                'image': batch.image.url if batch.image else None,
            })
    return JsonResponse({
        'total_items': sum(cart.values()),
        'total_price': round(total_price, 2),
        'cart_items': cart_items_data,
    })


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
                timezone.datetime.combine(
                    next_date, timezone.datetime.min.time())
            ),
            order_status='PENDING',
            recurring=False,  # This is a one-off modification, not a template
        )

        # Copy items with updated quantities from POST
        for op in order.orderproduct_set.all():
            new_qty = int(request.POST.get(f'qty_{op.id}', op.numPurchased))
            OrderProduct.objects.create(
                order=new_order,
                batch=op.batch,
                numPurchased=new_qty,
                price_at_purchase=op.price_at_purchase,
            )

        messages.success(
            request, "Next occurrence updated. The recurring template is unchanged.")
        return redirect('recurring_orders')

    return render(request, 'modify_occurrence.html', {
        'order': order,
        'next_date': get_next_occurrence(order),
        'items': order.orderproduct_set.all(),
    })


@login_required
def order_history(request):
    # Fetch orders for the logged-in user, sorted by most recent first
    orders = Order.objects.filter(
        customer=request.user).order_by('-order_date')
    return render(request, 'order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'order_detail.html', {'order': order})


@login_required
def reorder(request, order_id):
    old_order = get_object_or_404(Order, id=order_id, customer=request.user)
    # Logic to add items to cart would go here
    # Check availability and add to session or Cart model
    return redirect('checkout')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})

    # If memory is empty, kick them back home
    if not cart:
        messages.error(request, "You haven't selected any items.")
        return redirect('home')

    # 1. Gather all batches and calculate the total price
    total_price = 0
    cart_items = []

    for pid, qty in cart.items():
        batch = get_object_or_404(ProductBatch, id=pid)
        total_price += batch.price * qty
        cart_items.append({'product': batch, 'quantity': qty})

    min_delivery_date = (timezone.now() + timedelta(hours=48)
                         ).strftime('%Y-%m-%dT%H:%M')
    checkout_fee = total_price * Decimal('0.05')
    total_price += checkout_fee

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
                total_price=round(total_price, 2),
                delivery_date=form.cleaned_data['delivery_date'],
                order_status='PENDING',
                recurring=is_recurring,
                recurrence_type=recurrence_type if is_recurring else 'None',
                recurrence_day=int(
                    recurrence_day) if is_recurring and recurrence_day else None,
            )

            # 3. Loop through the memory to link ALL items to this order
            for item in cart_items:
                batch = item['product']
                OrderProduct.objects.create(
                    order=new_order,
                    batch=batch,
                    numPurchased=item['quantity'],
                    price_at_purchase=batch.price,
                )

            # Clear the memory now that the order is placed!
            request.session['cart'] = {}

            messages.success(request, "Order placed successfully!")
            return redirect('order_history')
    else:
        form = CheckoutForm()

    return render(request, 'checkout.html', {
        'form': form,
        'cart_items': cart_items,  # Pass the list to HTML so you can show what they are buying
        'total_price': total_price,
        'min_delivery_date': min_delivery_date,
        'user_address': request.user.address,
        'user_postcode': request.user.postcode
    })


def home_view(request):
    cart = request.session.get('cart', {})
    # Calculate total price
    total_price = 0
    if cart:
        batches = ProductBatch.objects.filter(id__in=cart.keys())
        for batch in batches:
            qty = cart.get(str(batch.id), 0)
            total_price += float(batch.price) * qty

    # Latest batch subqueries — pick the most recently created batch per product
    latest = ProductBatch.objects.filter(
        product=OuterRef('pk')
    ).order_by('-created_at')

    items = Product.objects.select_related('producer').annotate(
        total_stock=Sum('batches__stock'),
        primary_batch_id=Subquery(latest.values('id')[:1]),
        min_price=Min('batches__price'),
        primary_image=Subquery(latest.values('image')[:1]),
        primary_availability=Subquery(latest.values('availability')[:1]),
        primary_season_start=Subquery(latest.values('seasonStart')[:1]),
        primary_season_end=Subquery(latest.values('seasonEnd')[:1]),
        primary_quality=Subquery(latest.values('quality_class')[:1]),
        primary_surplus=Subquery(latest.values('surplus')[:1]),
        primary_discount=Subquery(latest.values('discount_percentage')[:1]),
    ).filter(total_stock__gt=0)

    # Text search
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__organisation_name__icontains=q)
        )

    # Category filter (multiple checkboxes)
    categories = request.GET.getlist('category')
    if categories:
        items = items.filter(category__in=categories)

    # In stock filter — already enforced by total_stock__gt=0 above
    # Discounted filter
    if request.GET.get('discounted'):
        items = items.filter(batches__surplus=True).distinct()

    # In season filter
    if request.GET.get('in_season'):
        items = items.filter(
            batches__availability__in=['Available', 'Available All Year']
        ).distinct()

    # Spell suggestion: if a search returned no results, suggest the closest product name
    suggestion = None
    if q and not items.exists():
        all_names = list(Product.objects.values_list('name', flat=True))
        matches = difflib.get_close_matches(q, all_names, n=1, cutoff=0.6)
        if matches:
            suggestion = matches[0]

    # AJAX based search
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [{
            'id': str(item.primary_batch_id),
            'name': item.name,
            'price': str(item.min_price),
            'image': f'/media/{item.primary_image}' if item.primary_image else None,
            'allergens': item.allergens,
            'description': item.description,
            'category': item.category,
            'availability': item.primary_availability,
            'seasonStart': item.primary_season_start,
            'seasonEnd': item.primary_season_end,
            'organic': item.organic,
            'producer': item.producer.organisation_name,
            'quality_class': item.primary_quality,
            'surplus': item.primary_surplus,
            'discount': str(item.primary_discount or 0),
        } for item in items]
        return JsonResponse({'items': data, 'count': len(data), 'suggestion': suggestion})

    return render(request, 'home.html', {
        'items': items,
        'items': items,
        'cart_items': cart,
        'cart_total_price': round(total_price, 2),
        'selected_categories': categories,
        'in_stock': request.GET.get('in_stock'),
        'discounted': request.GET.get('discounted'),
        'in_season': request.GET.get('in_season'),
        'search_query': q,
        'suggestion': suggestion,
    })

    
def add_to_cart(request, product_id):
    if request.method == 'POST':
        # Get the current memory, or start a blank dictionary
        cart = request.session.get('cart', {})

        quantity = int(request.POST.get('quantity', 1))
        pid = str(product_id)  # Session keys must be strings

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
        product_form = ProductForm(request.POST)
        batch_form = ProductBatchForm(request.POST, request.FILES)
        if product_form.is_valid() and batch_form.is_valid():
            producer = User.objects.get(pk=request.user.pk)
            # Find existing product template or create a new one
            product, _ = Product.objects.get_or_create(
                producer=producer,
                name=product_form.cleaned_data['name'],
                defaults={
                    'category': product_form.cleaned_data['category'],
                    'description': product_form.cleaned_data['description'],
                    'unit': product_form.cleaned_data['unit'],
                    'food_miles': product_form.cleaned_data['food_miles'],
                    'allergens': product_form.cleaned_data['allergens'],
                    'organic': product_form.cleaned_data['organic'],
                }
            )
            batch = batch_form.save(commit=False)
            batch.product = product
            batch.save()
            return redirect('home')
        else:
            print(f"\033[43m\033[30m{product_form.errors=} {batch_form.errors=}\033[0m")
    else:
        product_form = ProductForm()
        batch_form = ProductBatchForm()

    return render(request, 'inventory_upload.html', {
        'product_form': product_form,
        'batch_form': batch_form,
        'months': Product.Months.choices,
    })


@login_required
def add_batch(request):
    producer = request.user
    products = Product.objects.filter(producer=producer).order_by('name')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id, producer=producer)
        batch_form = ProductBatchForm(request.POST, request.FILES)
        if batch_form.is_valid():
            batch = batch_form.save(commit=False)
            batch.product = product
            batch.save()
            return redirect('home')
        else:
            print(f"\033[43m\033[30m{batch_form.errors=}\033[0m")
    else:
        batch_form = ProductBatchForm()

    return render(request, 'add_batch.html', {
        'products': products,
        'batch_form': batch_form,
        'months': Product.Months.choices,
    })


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


def invoice_view(request, order_code=None):
    order_qs = Order.objects.filter(customer=request.user).prefetch_related(
        'orderproduct_set__product', 'customer')
    if order_code:
        order = order_qs.filter(id__startswith=order_code).order_by(
            'order_date').first()
    else:
        order = order_qs.order_by('order_date').first()

    invoice_items = []
    subtotal = Decimal('0.00')
    commission_rate = Decimal('5.00')
    commission_amount = Decimal('0.00')
    total = Decimal('0.00')

    if order:
        items = order.orderproduct_set.all()
        for item in items:
            line_total = item.numPurchased * item.product.price
            subtotal += line_total
            invoice_items.append({
                'name': item.product.name,
                'producer': item.product.producer,
                'quantity': item.numPurchased,
                'price': item.product.price,
                'line_total': line_total,
                'details': item.product.description,
                'best_before': item.product.best_before,
            })
        commission_amount = subtotal * (commission_rate / Decimal('100.00'))
        total = subtotal + commission_amount

    return render(request, 'invoice.html', {
        'order': order,
        'invoice_items': invoice_items,
        'subtotal': subtotal,
        'commission_rate': commission_rate,
        'commission_amount': commission_amount,
        'total': total,
    })


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
            messages.error(
                request, f"Access denied.\n {user_category} cannot access this model.")
            return redirect('management')

    # Filter returned models based on allowed_models
    model_names = [model.__name__ for model in app_config.get_models(
    ) if model.__name__ in allowed_models]
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
        if not is_superuser and user_category == 'Producer':
            # Get producer account specific rows for selected model
            row_filter = {
                'Product':   {'producer': request.user},
                # Order ownership identified via bridging Order => OrderProduct => Product => Producer
                'Order':     {'orderproduct__product__producer': request.user},
                'StoryPost': {'user': request.user},
                'Recipe':    {'user': request.user},
            }.get(selected_model_name, {})
            distinct = selected_model_name == 'Order'  # Only need one product
            # Specify Order as read-only, excludiong order_status for Producers
            if selected_model_name == 'Order':
                order_model = app_config.get_model('Order')
                readonly_fields = {
                    field.name for field in order_model._meta.fields if field.name != 'order_status'}
            # Remove id selection fields for producer
            elif selected_model_name in ('Product', 'StoryPost', 'Recipe'):
                owner_field = 'producer' if selected_model_name == 'Product' else 'user'
                readonly_fields = {owner_field}

        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(
            request, selected_model, selected_model_name, add_new, row_filter, distinct, readonly_fields)

    return render(
        request, 'management.html', {
            'model_names': model_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
        })


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


@login_required
def profile_view(request):
    """Display the logged-in user's profile page."""
    product_count = None
    if request.user.category == 'Producer':
        product_count = Product.objects.filter(producer=request.user).count()
    return render(request, 'profile.html', {'product_count': product_count})


def terms_view(request):
    """Display the terms and conditions / cookie policy page."""
    return render(request, 'terms.html')
