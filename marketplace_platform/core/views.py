import json
import os
import difflib
from collections import defaultdict
from django.db.models import Q, Sum, Subquery, OuterRef, Prefetch, Avg, Count, F
from django.apps import apps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.http import Http404, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
from .models import User, Product, ProductBatch, Order, OrderProduct, Review, OrderStatusHistory
from core.forms import LoginForm, ProductForm, ProductBatchForm, SignupForm, CheckoutForm, ReviewForm
from core.permissions import MANAGE_MODEL_ACCESS, get_all_models, management_access_required
from core.utils import get_management_context, get_recurring_orders_context, handle_management_post
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

MANAGEMENT_SEARCH_FIELDS = {
    'Product':    (['name', 'category', 'description'],
                   lambda obj: f"{obj.category} · £{obj.price}"),
    'Order':      (['order_status', 'special_instructions'],
                   lambda obj: f"{obj.order_status} · £{obj.total_price}"),
    'User':       (['email', 'first_name', 'last_name'],
                   lambda obj: obj.email),
    'StoryPost':  (['title', 'body'],
                   lambda obj: ""),
    'Recipe':     (['title', 'description'],
                   lambda obj: ""),
    'Payment':    (['status'],
                   lambda obj: f"£{obj.amount} · {obj.status}"),
}
MODEL_INSTRUCTIONS = {
    # 'User': 'Display individuals interacting with the platform (customers, producers, admins). Handles authentication, contact details and role types.',  
    # 'Product': 'Display the physical items available for purchase. Stores core details like name, current price, description, and active stock levels.',  
    'Order': 'Select a row to manage order details. Tracks the delivery details, total cost, assigned customer and the current overall progression status. <br> Select a heading to alternate between sort direction.', 
    # 'OrderProduct': 'Displays the bridge connecting an Order to specific Products. Captures the exact quantity purchased and locks in the price of the item at the exact time of checkout.',
    # 'StoryPost': 'Display blog-style updates or news posts created by the producer to share behind-the-scenes content or announcements with customers.',  
    # 'Recipe': 'Display and manage recipes.',  
    # 'RecipeIngredients': 'The bridge connecting a Recipe to the Products (or general ingredients) required to make it, including the exact measurements needed.', 
    'Review': 'Display customer feedback. Contains a text evaluation and a rating score attached to a specific Product or Recipe.',
    # 'Payment': 'Records a financial transaction attempt via a payment gateway (like Stripe). Stores the transaction ID, amount charged, and whether it succeeded or failed.', 
    # 'OrderPayment': 'The link mapping a specific Payment record to a specific Order. Useful if an order has multiple payment attempts, refunds, or split payments.',  
    # 'OrderStatusHistory': 'An audit log that tracks the lifecycle of an Order. Records exactly when a status changed (e.g., PENDING to READY), who changed it, and any optional notes.'
}

STATUS_SEQUENCE = ['PENDING', 'CONFIRMED', 'READY', 'DELIVERED']

@login_required
def update_cart_ajax(request, product_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        delta = int(data.get('delta', 1))
        cart = request.session.get('cart', {})
        pid = str(product_id)

        new_qty = cart.get(pid, 0) + delta
        if new_qty <= 0:
            cart.pop(pid, None)
        else:
            # Enforce max_order_qty cap for standard customers
            is_bulk_buyer = getattr(request.user, 'category', None) in ('Restaurant', 'Community')
            if not is_bulk_buyer:
                try:
                    batch = ProductBatch.objects.get(pk=product_id)
                    if batch.max_order_qty is not None:
                        new_qty = min(new_qty, batch.max_order_qty)
                except ProductBatch.DoesNotExist:
                    pass
            cart[pid] = new_qty

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
        batches = ProductBatch.objects.select_related('product__producer').filter(id__in=cart.keys())
        for batch in batches:
            qty = cart.get(str(batch.id), 0)
            subtotal = float(batch.price) * qty
            total_price += subtotal
            producer = batch.product.producer
            cart_items_data.append({
                'id': str(batch.id),
                'name': batch.name,
                'price': float(batch.price),
                'quantity': qty,
                'subtotal': round(subtotal, 2),
                'image': batch.image.url if batch.image else None,
                'producer': getattr(producer, 'organisation_name', None) or str(producer),
                'producer_id': str(producer.id),
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
    ).exclude(recurrence_type='None').prefetch_related('orderproduct_set__batch__product')

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
def modify_recurring_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == 'POST':
        # Create a brand new one-off order for next occurrence only
        for order_product in order.orderproduct_set.all():
            new_quantity = int(request.POST.get(f'qty_{order_product.id}', order_product.numPurchased))
            order_product.numPurchased = new_quantity
            order_product.save()
        order.recurrence_type = request.POST.get('recurrence_type', order.recurrence_type)
        next_date = get_next_occurrence(order)
        new_order = Order.objects.create(
            customer=request.user,
            total_price=order.total_price,
            delivery_date=timezone.make_aware(
                timezone.datetime.combine(
                    next_date, timezone.datetime.min.time())
            ),
            order_status='PENDING',
            recurrence_type='None',
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
def pause_recurring_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if request.method == 'POST':
        order.paused = not order.paused
        order.save()
        state = "paused" if order.paused else "resumed"
        messages.success(request, f"Recurring order {state}.")
    return redirect('orders')

@login_required
def delete_recurring_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if request.method == 'POST':
        order.delete()
        messages.success(request, "Recurring order deleted.")
    return redirect('orders')

@login_required
def orders(request):
    orders = Order.objects.filter(customer=request.user).order_by('-order_date')
    print(orders)
    return render(request, 'orders.html', {
        'orders': orders,
        'orders_with_next': get_recurring_orders_context(request.user)
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'order_detail.html', {'order': order})


@login_required
def reorder(request, order_id):
    old_order = get_object_or_404(Order, id=order_id, customer=request.user)
    print("\n", old_order)
    cart = {}
    names = []
    # Get all OrderProduct rows for this order and fetch their related Product
    for order_product in old_order.orderproduct_set.select_related('batch__product').all():
        cart[str(order_product.batch.id)] = order_product.numPurchased
        names.append(f"{order_product.numPurchased} {order_product.batch.product.name}")
    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, f"Added to cart: {', '.join(names)}.")
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
        batch = get_object_or_404(ProductBatch.objects.select_related('product__producer'), id=pid)
        total_price += batch.price * qty
        cart_items.append({'product': batch, 'quantity': qty})

    groups = defaultdict(list)
    for item in cart_items:
        producer = item['product'].product.producer
        groups[producer].append(item)
    cart_by_producer = [{'producer': p, 'items': items} for p, items in groups.items()]

    min_delivery_date = (timezone.now() + timedelta(hours=48)
                         ).strftime('%Y-%m-%dT%H:%M')
    checkout_fee = total_price * Decimal('0.05')
    total_price += checkout_fee

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            recurrence_type = request.POST.get('recurrence_type', 'None')
            recurrence_day = request.POST.get('recurrence_day', None)
            try:
                with transaction.atomic():
                    # Lock all batch rows for the duration of this transaction
                    batch_ids = [str(item['product'].pk) for item in cart_items]
                    locked = {
                        str(b.pk): b
                        for b in ProductBatch.objects.select_for_update().filter(pk__in=batch_ids)
                    }

                    # Check every item has enough stock before touching anything
                    short = []
                    for item in cart_items:
                        b = locked[str(item['product'].pk)]
                        if b.stock < item['quantity']:
                            short.append(
                                f"{item['product'].name}: only {b.stock} available, you requested {item['quantity']}"
                            )
                    if short:
                        raise ValueError(short)

                    new_order = Order.objects.create(
                        customer=request.user,
                        total_price=round(total_price, 2),
                        delivery_date=form.cleaned_data['delivery_date'],
                        order_status='PENDING',
                        recurrence_type=recurrence_type,
                        recurrence_day=int(recurrence_day) if recurrence_day and recurrence_type != 'None' else None,
                    )

                    for item in cart_items:
                        batch = item['product']
                        qty = item['quantity']
                        OrderProduct.objects.create(
                            order=new_order,
                            batch=batch,
                            numPurchased=qty,
                            price_at_purchase=batch.price,
                        )
                        ProductBatch.objects.filter(pk=batch.pk).update(stock=F('stock') - qty)

                    request.session['cart'] = {}
                    messages.success(request, "Order placed successfully!")
                    return redirect('orders')

            except ValueError as e:
                for msg in e.args[0]:
                    messages.error(request, msg)
    else:
        form = CheckoutForm()

    return render(request, 'checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'cart_by_producer': cart_by_producer,
        'total_price': total_price,
        'min_delivery_date': min_delivery_date,
        'user_address': request.user.address,
        'user_postcode': request.user.postcode
    })


def home_view(request):
    cart = request.session.get('cart', {})
    total_price = 0
    if cart:
        batches = ProductBatch.objects.filter(id__in=cart.keys())
        for batch in batches:
            qty = cart.get(str(batch.id), 0)
            total_price += float(batch.price) * qty

    in_stock_batches_qs = ProductBatch.objects.filter(stock__gt=0).order_by('quality_class')

    class_a_image = ProductBatch.objects.filter(
        product=OuterRef('pk'), quality_class='A'
    ).order_by('-created_at')

    items = Product.objects.select_related('producer').prefetch_related(
        Prefetch('batches', queryset=in_stock_batches_qs, to_attr='in_stock_batches')
    ).annotate(
        total_stock=Sum('batches__stock'),
        primary_image=Subquery(class_a_image.values('image')[:1]),
        avg_rating=Avg('review__rating'),
        review_count=Count('review'),
    ).filter(total_stock__gt=0)

    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__organisation_name__icontains=q)
        )

    categories = request.GET.getlist('category')
    if categories:
        items = items.filter(category__in=categories)

    if request.GET.get('discounted'):
        items = items.filter(batches__surplus=True).distinct()

    if request.GET.get('organic'):
        items = items.filter(organic=True)

    if request.GET.get('in_season'):
        items = items.filter(
            batches__availability__in=['Available', 'Available All Year']
        ).distinct()

    exclude_allergens = request.GET.getlist('exclude_allergen')
    for allergen in exclude_allergens:
        items = items.exclude(allergens__contains=[allergen])

    suggestion = None
    if q and not items.exists():
        all_names = list(Product.objects.values_list('name', flat=True))
        matches = difflib.get_close_matches(q, all_names, n=1, cutoff=0.6)
        if matches:
            suggestion = matches[0]

    total_count = items.count()
    paginator = Paginator(items, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    items_list = list(page_obj)

    def _batch_dict(b, unit=''):
        return {
            'id': str(b.id),
            'quality_class': b.quality_class,
            'price': str(b.price),
            'unit': unit,
            'stock': b.stock,
            'best_before': str(b.best_before),
            'image': f'/media/{b.image}' if b.image else None,
            'surplus': b.surplus,
            'discount': str(b.discount_percentage),
            'availability': b.availability,
            'seasonStart': b.seasonStart,
            'seasonEnd': b.seasonEnd,
            'max_order_qty': b.max_order_qty,
        }

    batch_data = {
        str(item.id): [_batch_dict(b, item.unit) for b in item.in_stock_batches]
        for item in items_list
    }

    for item in items_list:
        batches = item.in_stock_batches
        if batches:
            prices = [float(b.price) for b in batches]
            lo = min(prices)
            hi = max(prices)
            item.price_display = f'From £{lo:.2f}' if lo != hi else f'£{lo:.2f}'
        else:
            item.price_display = f'£{item.price}'

    product_ids = [item.id for item in items_list]
    reviews_qs = Review.objects.filter(product_id__in=product_ids).select_related('user').order_by('-date_posted')
    review_data = {}
    for r in reviews_qs:
        pid = str(r.product_id)
        if pid not in review_data:
            review_data[pid] = []
        if True:
            review_data[pid].append({
                'rating': r.rating,
                'title': r.title,
                'content': r.content,
                'date': r.date_posted.strftime('%d %b %Y'),
                'author': 'Anonymous' if r.anonymous else (r.user.full_name or r.user.email),
            })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [{
            'id': str(item.id),
            'name': item.name,
            'price': str(item.price),
            'price_display': item.price_display,
            'image': f'/media/{item.primary_image}' if item.primary_image else None,
            'allergens': item.allergens,
            'description': item.description,
            'category': item.category,
            'organic': item.organic,
            'producer': item.producer.organisation_name,
            'organic_description': item.producer.organic_description,
            'avg_rating': round(item.avg_rating, 1) if item.avg_rating else None,
            'review_count': item.review_count,
        } for item in items_list]
        return JsonResponse({
            'items': data,
            'count': total_count,
            'suggestion': suggestion,
            'batch_data': batch_data,
            'review_data': review_data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
        })

    allergen_list = [
        'Celery', 'Gluten', 'Crustaceans', 'Eggs', 'Fish', 'Lupin', 'Milk',
        'Molluscs', 'Mustard', 'Nuts', 'Peanuts', 'Sesame', 'Soya', 'Sulphites',
    ]
    return render(request, 'home.html', {
        'items': items_list,
        'batch_data': batch_data,
        'review_data': review_data,
        'cart_items': cart,
        'cart_total_price': round(total_price, 2),
        'selected_categories': categories,
        'in_stock': request.GET.get('in_stock'),
        'discounted': request.GET.get('discounted'),
        'organic': request.GET.get('organic'),
        'in_season': request.GET.get('in_season'),
        'exclude_allergens': exclude_allergens,
        'allergen_list': allergen_list,
        'search_query': q,
        'suggestion': suggestion,
        'page_obj': page_obj,
        'total_count': total_count,
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


@login_required
def clear_notifications(request):
    if request.method == 'POST':
        keys = request.POST.getlist('keys')
        dismissed = set(request.session.get('dismissed_notifications', []))
        dismissed.update(keys)
        request.session['dismissed_notifications'] = list(dismissed)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_data = form.cleaned_data
            email = login_data.get('email')
            password = login_data.get('password')
            remember_me = login_data.get('remember_me')

            # Check if these credentials match a user in the DB
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                messages.success(request, f"Welcome back, {email}!")
                return redirect('home')  # Go to the marketplace
            else:
                messages.error(request, "username or password is incorrect")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

@login_required
def upload_item(request):
    products = Product.objects.filter(producer=request.user).order_by('name')
    active_tab = 'new'

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'new_product':
            active_tab = 'new'
            allergens = request.POST.getlist('allergens')

            product, created = Product.objects.get_or_create(
                name=request.POST.get('name', '').strip(),
                defaults={
                    'producer': request.user,
                    'category': request.POST.get('category', 'Vegetable'),
                    'description': request.POST.get('description', ''),
                    'price': Decimal(request.POST.get('price') or '0'),
                    'unit': request.POST.get('unit', 'kg'),
                    'stock_alert_threshold': 0,
                    'allergens': allergens,
                    'organic': 'organic' in request.POST,
                }
            )
            image = request.FILES.get('image')
            if image and created:
                from datetime import date, timedelta
                ProductBatch.objects.create(
                    product=product,
                    quality_class='A',
                    stock=1,
                    best_before=date.today() + timedelta(days=365),
                    image=image,
                )
            if created:
                messages.success(request, f'"{product.name}" was created successfully!')
            else:
                messages.warning(request, f'A product named "{product.name}" already exists.')
            return redirect('inventory_upload')

        elif form_type == 'new_batch':
            active_tab = 'batch'
            product = get_object_or_404(Product, id=request.POST.get('product_id'))
            quality_class = request.POST.get('quality_class', 'B')
            surplus = quality_class == 'Discounted'
            ref_batch = product.batches.filter(quality_class='A').order_by('-created_at').first() \
                        or product.batches.order_by('-created_at').first()
            season_start = ref_batch.seasonStart if ref_batch else 'January'
            season_end = ref_batch.seasonEnd if ref_batch else 'December'
            class_discounts = {'A': Decimal('0'), 'B': Decimal('15'), 'C': Decimal('30'), 'D': Decimal('45'), 'Discounted': Decimal('50')}
            if quality_class == 'Discounted':
                discount_pct = Decimal(request.POST.get('discount_percentage') or '50')
            else:
                discount_pct = class_discounts.get(quality_class, Decimal('0'))
            harvest_date = request.POST.get('harvest_date') or None
            ProductBatch.objects.create(
                product=product,
                quality_class=quality_class,
                stock=int(request.POST.get('stock') or 1),
                harvest_date=harvest_date,
                best_before=request.POST.get('best_before'),
                seasonStart=season_start,
                seasonEnd=season_end,
                surplus=surplus,
                discount_percentage=discount_pct,
                discount_note=request.POST.get('discount_note', ''),
                image=request.FILES.get('image'),
                max_order_qty=int(request.POST['max_order_qty']) if request.POST.get('max_order_qty') else None,
                surplus_discount_percentage=Decimal(request.POST.get('surplus_discount_percentage') or '20'),
            )
            return redirect('home')

    allergen_list = [
        'Celery', 'Gluten', 'Crustaceans', 'Eggs', 'Fish', 'Lupin', 'Milk',
        'Molluscs', 'Mustard', 'Nuts', 'Peanuts', 'Sesame', 'Soya', 'Sulphites',
    ]
    return render(request, 'inventory_upload.html', {
        'months': Product.Months.choices,
        'products': products,
        'active_tab': active_tab,
        'allergen_list': allergen_list,
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
            remember_me = form.cleaned_data.get('remember_me')
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
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 weeks
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

@login_required
def invoice_view(request, order_code=None):
    order_qs = Order.objects.filter(customer=request.user).prefetch_related(
        'orderproduct_set__batch__product', 'customer')
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
            line_total = item.numPurchased * item.price_at_purchase
            subtotal += line_total
            invoice_items.append({
                'name': item.batch.name,
                'producer': item.batch.producer,
                'quantity': item.numPurchased,
                'price': item.price_at_purchase,
                'line_total': line_total,
                'details': item.batch.description,
                'best_before': item.batch.best_before,
            })
        commission_amount = subtotal * (commission_rate / Decimal('100.00'))
        total = subtotal + commission_amount

    context = {
        'order': order,
        'invoice_items': invoice_items,
        'subtotal': subtotal,
        'commission_rate': commission_rate,
        'commission_amount': commission_amount,
        'total': total,
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'includes/orders/invoice_modal_content.html', context)
    return render(request, 'invoice.html', context)


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
    model_display_names = [app_config.get_model(name)._meta.verbose_name_plural.title() for name in model_names]
    print(model_names)
    print(f"{user_category} - {allowed_models}")

    print(f"\n[management_view] Selected model is: {selected_model_name}")

    if selected_model_name == 'Order':
        auto_update_order_statuses()

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
                'Order':     {'orderproduct__batch__product__producer': request.user},
                'StoryPost': {'user': request.user},
                'Recipe':    {'user': request.user},
            }.get(selected_model_name, {})
            distinct = selected_model_name == 'Order' # Only need one product
            # Specify Order as read-only, excludiong order_status for Producers
            if selected_model_name == 'Order':
                order_model = app_config.get_model('Order')
                readonly_fields = {field.name for field in 
                                   order_model._meta.fields if field.name != 'order_status'}
            # Remove id selection fields for producer
            elif selected_model_name in ('Product', 'StoryPost', 'Recipe'): 
                owner_field = 'producer' if selected_model_name == 'Product' else 'user'
                readonly_fields = {owner_field}

        selected_model = app_config.get_model(selected_model_name)
        selected_data = get_management_context(
            request, selected_model, selected_model_name,
            add_new, row_filter, distinct, readonly_fields)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'includes/management/management_table_fragment.html', {
            'selected_data': selected_data,
            'selected_model_name': selected_model_name,
        })
    instructions = MODEL_INSTRUCTIONS.get(selected_model_name, '')
    return render(
        request, 'management.html', {
            'model_names': model_names,
            'model_display_names': model_display_names,
            'selected_model_name': selected_model_name,
            'selected_data': selected_data,
            'model_instructions': instructions,
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
        items = order.orderproduct_set.all().select_related('batch__product')

        receipt_data = []
        for item in items:
            stock_now = item.batch.stock
            receipt_data.append({
                'name': item.batch.product.name,
                'quality_class': item.batch.get_quality_class_display(),
                'best_before': item.batch.best_before.strftime('%Y-%m-%d') if item.batch.best_before else '',
                'batch_number': item.batch.batch_number,
                'qty': item.numPurchased,
                'price': f"{item.batch.price:.2f}",
                'total': f"{item.numPurchased * item.batch.price:.2f}",
                'stock_now': stock_now,
                'stock_after': stock_now - item.numPurchased,
            })
        data = {
            'status': order.order_status,
            'advance_url': f"/management/order/{order_id}/advance/" if order.order_status in ('PENDING', 'CONFIRMED') else None,
            'next_status': {'PENDING': 'CONFIRMED', 'CONFIRMED': 'READY'}.get(order.order_status),
            'customer_name': order.customer.full_name or order.customer.email,
            'customer_type': order.customer.category,
            'email': order.customer.email,
            'phone': order.customer.phone,
            'address': f"{order.customer.address}, {order.customer.postcode}" if order.customer.address and order.customer.postcode else '',
            'instructions': order.special_instructions,
            'order_date': order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else '',
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else '',
            'recurrence': f"{order.get_recurrence_day_display()} ({order.recurrence_type})" if order.recurrence_type != 'None' else '',
            'total_price': f"{order.total_price:.2f}",
            'receipt': receipt_data
        }
        data['status_history'] = [
            {
                'from': h.from_status,
                'to': h.to_status,
                'by': h.changed_by.email if h.changed_by else '—',
                'at': h.changed_at.strftime('%d %b %Y %H:%M'),
                'note': h.note,
            }
            for h in order.status_history.all()
        ]
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


def auto_update_order_statuses():
    """Auto-update orders when their delivery date has passed."""
    now = timezone.now()

    # READY => DELIVERED
    ready_due = Order.objects.filter(order_status='READY', delivery_date__lte=now)
    histories = [
        OrderStatusHistory(order=o, from_status='READY', to_status='DELIVERED',
                           changed_by=None, note='Auto-delivered: delivery date reached.')
        for o in ready_due
    ]
    OrderStatusHistory.objects.bulk_create(histories)
    ready_due.update(order_status='DELIVERED')

    # PENDING => CANCELLED (producer never acknowledged)
    unacknowledged = Order.objects.filter(order_status='PENDING', delivery_date__lte=now)
    histories = [
        OrderStatusHistory(order=o, from_status='PENDING', to_status='CANCELLED',
                           changed_by=None, note='Auto-cancelled: delivery date passed without acknowledgement.')
        for o in unacknowledged
    ]
    OrderStatusHistory.objects.bulk_create(histories)
    unacknowledged.update(order_status='CANCELLED')


@management_access_required
def advance_order_status(request, order_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    # Producer can only advance orders that contain their products
    if not request.user.is_superuser and getattr(request.user, 'category', None) == 'Producer':
        if not order.products.filter(product__producer=request.user).exists():
            return JsonResponse({'error': 'Access denied'}, status=403)

    current = order.order_status
    try:
        next_status = STATUS_SEQUENCE[STATUS_SEQUENCE.index(current) + 1]
    except (ValueError, IndexError):
        return JsonResponse({'error': 'Already at final status'}, status=400)

    note = request.POST.get('note', '').strip()
    OrderStatusHistory.objects.create(
        order=order,
        from_status=current,
        to_status=next_status,
        changed_by=request.user,
        note=note,
    )
    order.order_status = next_status
    order.save(update_fields=['order_status'])
    messages.success(request, f"Order {str(order_id)[:8]} advanced to {next_status.title()}.")
    return redirect(request.META.get('HTTP_REFERER', 'management'))


@login_required
@login_required
def profile_view(request):
    """Display the logged-in user's profile page."""
    product_count = None
    if request.user.category == 'Producer':
        product_count = Product.objects.filter(producer=request.user).count()

    if request.method == 'POST' and request.user.category == 'Producer':
        request.user.organic_description = request.POST.get('organic_description', '').strip()
        request.user.save(update_fields=['organic_description'])
        messages.success(request, 'Organic certification updated.')
        return redirect('profile')

    return render(request, 'profile.html', {'product_count': product_count})


def terms_view(request):
    """Display the terms and conditions / cookie policy page."""
    return render(request, 'terms.html')


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.category == User.Category.PRODUCER:
        if product.producer == request.user:
            messages.error(request, "You cannot review your own products.")
            return redirect("orders")

    delivered_purchase = OrderProduct.objects.filter(
        product=product,
        order__customer=request.user,
        order__order_status=Order.Status.DELIVERED
    ).exists()

    if not delivered_purchase:
        messages.error(request, "You can only review products from delivered orders.")
        return redirect("orders")

    if Review.objects.filter(user=request.user, product=product).exists():
        messages.info(request, "You've already reviewed this product.")
        return redirect("orders")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review submitted!")
            return redirect("orders")
    else:
        form = ReviewForm()

    return render(request, "review_form.html", {"form": form, "product": product})


@management_access_required
def management_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    app_config = apps.get_app_config('core')
    is_superuser = request.user.is_superuser
    user_category = getattr(request.user, 'category', None)
    allowed_models = get_all_models() if is_superuser else MANAGE_MODEL_ACCESS.get(user_category, [])
    if callable(allowed_models):
        allowed_models = allowed_models()

    results = []
    for model_name, (fields, detail_fn) in MANAGEMENT_SEARCH_FIELDS.items():
        if model_name not in allowed_models:
            continue
        model = app_config.get_model(model_name)
        query = Q()
        for f in fields:
            query |= Q(**{f'{f}__icontains': q})
        qs = model.objects.filter(query)
        # Producer scoping
        if not is_superuser and user_category == 'Producer':
            if model_name == 'Product':
                qs = qs.filter(producer=request.user)
            elif model_name in ('StoryPost', 'Recipe'):
                qs = qs.filter(user=request.user)
        for obj in qs[:5]:
            results.append({
                'model': model_name,
                'model_label': model._meta.verbose_name_plural.title(),
                'id': str(obj.pk),
                'label': str(obj),
                'detail': detail_fn(obj),
            })

    return JsonResponse({'results': results})
