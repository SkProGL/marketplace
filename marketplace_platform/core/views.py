import json
import difflib
from collections import defaultdict
from django.db.models import Q, Sum, Subquery, OuterRef, Prefetch, Avg, Count, F
from django.apps import apps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, update_session_auth_hash
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from .models import Complaint, User, Product, ProductBatch, Order, ProducerOrder, OrderProduct, Review, OrderStatusHistory, Recipe, RecipeIngredients, StoryPost, FavouriteRecipe, Payment
from core.forms import ComplaintForm, LoginForm, ProductForm, ProductBatchForm, SignupForm, CheckoutForm, ReviewForm, ProfileEditForm, RecipeForm, StoryPostForm
from core.permissions import MANAGE_MODEL_ACCESS, get_all_models, management_access_required
from core.utils import get_management_context, get_recurring_orders_context, handle_management_post, food_mile_session_builder, calculate_distance, get_producer_food_miles, apply_surplus_if_due, SURPLUS_DAYS
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
from datetime import time, timedelta, date as date_type, datetime as datetime_type


MANAGEMENT_SEARCH_FIELDS = {
    'Product':    (['name', 'category', 'description'],
                   lambda obj: f"{obj.category} · £{obj.price}"),
    'Order':      (['order_status', 'special_instructions'],
                   lambda obj: f"{obj.order_status} · £{obj.total_price}"),
    'User':       (['email', 'first_name', 'last_name'],
                   lambda obj: obj.email),
    'StoryPost':  (['content'],
                   lambda obj: ""),
    'Recipe':     (['title', 'description'],
                   lambda obj: ""),
    'Payment':    (['status'],
                   lambda obj: f"£{obj.amount} · {obj.status}"),
}
MODEL_INSTRUCTIONS = {
    'User': 'Select password field buttons to set, or send reset link for, new password for respective user.',  
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
    else:
        batches = []
    for batch in batches:
        qty = cart.get(str(batch.id), 0)
        subtotal = float(batch.price) * qty
        total_price += subtotal

        producer = batch.product.producer

        food_miles = None
        coords = request.session.get("user_coords")

        if coords:
            food_miles = get_producer_food_miles(
                producer,
                (coords["lat"], coords["lon"])
            )

        cart_items_data.append({
            'id': str(batch.id),
            'name': batch.name,
            'price': float(batch.price),
            'quantity': qty,
            'subtotal': round(subtotal, 2),
            'image': batch.image.url if batch.image else None,
            'producer': getattr(producer, 'organisation_name', None) or str(producer),
            'producer_id': str(producer.id),
            'food_miles': float(food_miles) if food_miles is not None else None,
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
    return redirect('orders')


@login_required
def modify_recurring_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if request.method == 'POST':
        order.recurrence_type = request.POST.get('recurrence_type', order.recurrence_type)
        recurrence_day = request.POST.get('recurrence_day')
        if recurrence_day:
            order.recurrence_day = int(recurrence_day)
        order.save(update_fields=['recurrence_type', 'recurrence_day'])

        for op in order.orderproduct_set.all():
            new_qty = int(request.POST.get(f'qty_{op.id}', op.numPurchased))
            if new_qty != op.numPurchased:
                op.numPurchased = new_qty
                op.save(update_fields=['numPurchased'])

        messages.success(request, "Recurring order updated.")
        return redirect('orders')

    return redirect('orders')
   
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
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if request.method == 'POST' and order.order_status == 'PENDING':
        with transaction.atomic():
            for op in order.orderproduct_set.select_related('batch').all():
                ProductBatch.objects.filter(pk=op.batch_id).update(stock=F('stock') + op.numPurchased)
            order.delete()
        messages.success(request, "Order cancelled and stock restored.")
    else:
        messages.error(request, "Only pending orders can be cancelled.")
    return redirect('orders')


@login_required
def orders(request):
    qs = (Order.objects
          .filter(customer=request.user)
          .order_by('-order_date')
          .prefetch_related(
              'orderproduct_set__batch__product__producer',
              'producer_orders__status_history',
          ))
    paginator = Paginator(qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'orders.html', {
        'orders': page_obj,
        'page_obj': page_obj,
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
def loading(request):
    next_url = request.GET.get('next', '/orders/')
    return render(request, 'loading.html', {'next_url': next_url})

@login_required
def checkout(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "You haven't selected any items.")
        return redirect('home')

    total_price = Decimal('0.00')
    cart_items = []

    producer_miles_cache = {}

    for pid, qty in cart.items():

        batch = get_object_or_404(
            ProductBatch.objects.select_related('product__producer'),
            id=pid
        )

        producer = batch.product.producer

        if producer.id not in producer_miles_cache:

            if request.session.get("user_coords"):

                coords = request.session["user_coords"]

                producer_miles_cache[producer.id] = get_producer_food_miles(
                    producer,
                    (coords["lat"], coords["lon"])
                )

            else:
                producer_miles_cache[producer.id] = 0

        food_miles = producer_miles_cache[producer.id]

        subtotal = batch.price * qty
        total_price += subtotal

        cart_items.append({
            'product': batch,
            'quantity': qty,
            'food_miles': food_miles,
        })

    groups = defaultdict(list)

    for item in cart_items:
        producer = item['product'].product.producer
        groups[producer].append(item)

    cart_by_producer = []
    total_commission = Decimal('0.00')

    for producer, items in groups.items():

        subtotal = sum(
            item['product'].price * item['quantity']
            for item in items
        )

        commission = (
            subtotal * Decimal('0.05')
        ).quantize(Decimal('0.01'))

        cart_by_producer.append({
            'producer': producer,
            'items': items,
            'subtotal': subtotal,
            'commission': commission,
        })

        total_commission += commission

    min_delivery_date = (
        timezone.now().date() + timedelta(days=2)
    ).strftime('%Y-%m-%d')

    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            total_food_miles = sum(
                item['food_miles'] or 0
                for item in cart_items
            )

            min_date = date_type.today() + timedelta(days=2)

            producer_dates = {}
            date_errors = []

            for group in cart_by_producer:

                pid = str(group['producer'].id)

                raw = request.POST.get(
                    f'delivery_date_{pid}',
                    ''
                ).strip()

                producer_name = (
                    group['producer'].organisation_name
                    or str(group['producer'])
                )

                try:
                    d = date_type.fromisoformat(raw)

                    if d < min_date:
                        date_errors.append(
                            f"Delivery date for {producer_name} "
                            f"must be at least 48 hours from now."
                        )
                    else:
                        producer_dates[pid] = d

                except ValueError:
                    date_errors.append(
                        f"Please select a valid delivery date "
                        f"for {producer_name}."
                    )

            if date_errors:

                for msg in date_errors:
                    messages.error(request, msg)

            else:

                recurrence_type = request.POST.get(
                    'recurrence_type',
                    'None'
                )

                recurrence_day = request.POST.get(
                    'recurrence_day',
                    None
                )

                earliest_date = min(producer_dates.values())

                try:

                    with transaction.atomic():

                        batch_ids = [
                            str(item['product'].pk)
                            for item in cart_items
                        ]

                        locked = {
                            str(b.pk): b
                            for b in ProductBatch.objects
                            .select_for_update()
                            .filter(pk__in=batch_ids)
                        }

                        short = []

                        for item in cart_items:

                            b = locked[str(item['product'].pk)]

                            if b.stock < item['quantity']:

                                short.append(
                                    f"{item['product'].name}: "
                                    f"only {b.stock} available, "
                                    f"you requested "
                                    f"{item['quantity']}"
                                )

                        if short:
                            raise ValueError(short)

                        new_order = Order.objects.create(
                            customer=request.user,
                            total_price=round(total_price, 2),
                            food_miles=round(total_food_miles, 2),
                            delivery_date=timezone.make_aware(
                                datetime_type.combine(
                                    earliest_date,
                                    datetime_type.min.time()
                                )
                            ),
                            delivery_address=form.cleaned_data[
                                'delivery_address'
                            ],
                            delivery_postcode=form.cleaned_data[
                                'delivery_postcode'
                            ],
                            order_status='PENDING',
                            recurrence_type=recurrence_type,
                            recurrence_day=(
                                int(recurrence_day)
                                if recurrence_day
                                and recurrence_type != 'None'
                                else None
                            ),
                        )

                        producer_orders = {}

                        producer_subtotals = defaultdict(
                            Decimal
                        )

                        for item in cart_items:

                            batch = item['product']

                            producer = batch.product.producer

                            pid = str(producer.id)

                            if producer.id not in producer_orders:

                                producer_orders[producer.id] = (
                                    ProducerOrder.objects.create(
                                        order=new_order,
                                        producer=producer,
                                        order_status='PENDING',
                                        delivery_date=timezone.make_aware(
                                            datetime_type.combine(
                                                producer_dates[pid],
                                                datetime_type.min.time()
                                            )
                                        ),
                                    )
                                )
                            OrderProduct.objects.create(
                                order=new_order,
                                producer_order=producer_orders[
                                    producer.id
                                ],
                                batch=batch,
                                numPurchased=item['quantity'],
                                price_at_purchase=batch.price,
                            )

                            producer_subtotals[
                                producer.id
                            ] += (
                                batch.price * item['quantity']
                            )

                            ProductBatch.objects.filter(
                                pk=batch.pk
                            ).update(
                                stock=F('stock') - item['quantity']
                            )

                        now = timezone.now()

                        for prod_id, prod_order in producer_orders.items():

                            prod_subtotal = producer_subtotals[
                                prod_id
                            ]

                            producer_amount = (
                                prod_subtotal * Decimal('0.95')
                            ).quantize(Decimal('0.01'))

                            Payment.objects.create(
                                producer=prod_order.producer,
                                order=new_order,
                                amount=producer_amount,
                                status=Payment.Status.PROCESSED,
                                processed_at=now,
                            )

                        request.session['cart'] = {}

                        confirm_url = reverse(
                            'order_confirmation',
                            args=[new_order.id]
                        )

                        return redirect(
                            f'/loading/?next={confirm_url}'
                        )

                except ValueError as e:

                    for msg in e.args[0]:
                        messages.error(request, msg)

    else:
        form = CheckoutForm()

    return render(request, 'checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'cart_by_producer': cart_by_producer,
        'total_commission': total_commission,
        'total_price': total_price,
        'min_delivery_date': min_delivery_date,
        'user_address': request.user.address,
        'user_postcode': request.user.postcode
    })

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    items = order.orderproduct_set.select_related('batch__product__producer').all()

    producer_order_dates = {
        str(po.producer_id): po.delivery_date
        for po in ProducerOrder.objects.filter(order=order)
    }

    groups = defaultdict(list)
    for op in items:
        producer = op.batch.product.producer
        groups[producer].append(op)

    cart_by_producer = []
    total_commission = Decimal('0')
    for producer, ops in groups.items():
        subtotal = sum(op.price_at_purchase * op.numPurchased for op in ops)
        commission = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
        total_commission += commission
        cart_by_producer.append({
            'producer': producer,
            'items': ops,
            'subtotal': subtotal,
            'commission': commission,
            'producer_payment': (subtotal * Decimal('0.95')).quantize(Decimal('0.01')),
            'delivery_date': producer_order_dates.get(str(producer.id)),
        })

    payment_processed = Payment.objects.filter(order=order, status=Payment.Status.PROCESSED).exists()

    return render(request, 'order_confirmation.html', {
        'order': order,
        'cart_by_producer': cart_by_producer,
        'total_commission': total_commission,
        'payment_processed': payment_processed,
    })


def home_view(request):
    cart = request.session.get('cart', {})
    total_price = 0
    if cart:
        batches = ProductBatch.objects.filter(id__in=cart.keys())
        for batch in batches:
            qty = cart.get(str(batch.id), 0)
            total_price += float(batch.price) * qty

    min_best_before = date_type.today() + timedelta(days=2)
    in_stock_batches_qs = ProductBatch.objects.filter(
        stock__gt=0,
        best_before__gt=min_best_before,
        availability__in=['Available', 'Available All Year'],
    ).order_by('quality_class')

    class_a_image = ProductBatch.objects.filter(
        product=OuterRef('pk'), quality_class='A'
    ).order_by('-created_at')

    items = Product.objects.select_related('producer').prefetch_related(
        Prefetch('batches', queryset=in_stock_batches_qs, to_attr='in_stock_batches')
    ).annotate(
        total_stock=Sum('batches__stock'),
        primary_image=Subquery(
            ProductBatch.objects.filter(
                product=OuterRef('pk'),
                image__isnull=False
            ).order_by('id').values('image')[:1]
        ),
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

    producer_id = request.GET.get('producer')
    if producer_id:
        items = items.filter(producer_id=producer_id)

    if request.GET.get('discounted'):
        items = items.filter(batches__surplus=True).distinct()

    if request.GET.get('organic'):
        items = items.filter(organic=True)

    exclude_allergens = request.GET.getlist('exclude_allergen')
    for allergen in exclude_allergens:
        items = items.exclude(allergens__contains=[allergen])

    min_miles = request.GET.get("min_miles")
    max_miles = request.GET.get("max_miles")
    customer_coords = request.session.get("user_coords")

    min_m = Decimal(min_miles) if min_miles else None
    max_m = Decimal(max_miles) if max_miles else None

    filtered_items = []

    for item in items:
        if customer_coords:
            miles = get_producer_food_miles(
                item.producer,
                (customer_coords["lat"], customer_coords["lon"])
            )
            item.food_miles = miles
        else:
            item.food_miles = None

        if customer_coords and (min_miles or max_miles):
            if item.food_miles is None:
                continue
            if min_m is not None and item.food_miles < min_m:
                continue
            if max_m is not None and item.food_miles > max_m:
                continue

        filtered_items.append(item)

    items = filtered_items
    suggestion = None
    if q and not items:
        all_names = list(Product.objects.values_list('name', flat=True))
        matches = difflib.get_close_matches(q, all_names, n=1, cutoff=0.6)
        if matches:
            suggestion = matches[0]

    total_count = len(items)
    paginator = Paginator(items, 18)
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
            'discount': str(b.effective_discount),
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

    # Build recipe suggestions: product_id -> list of {id, title, season, url}
    recipe_suggestions = {}
    if product_ids:
        ri_qs = RecipeIngredients.objects.filter(
            product_id__in=product_ids
        ).select_related('recipe__user')
        for ri in ri_qs:
            pid = str(ri.product_id)
            if pid not in recipe_suggestions:
                recipe_suggestions[pid] = []
            recipe_suggestions[pid].append({
                'id': str(ri.recipe.id),
                'title': ri.recipe.title,
                'season': ri.recipe.season,
                'producer': ri.recipe.user.organisation_name or ri.recipe.user.full_name or ri.recipe.user.email,
            })
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [{
            'id': str(item.id),
            'name': item.name,
            'price': str(item.price),
            'price_display': item.price_display,
            'image': item.image.url if item.image else None,
            'thumbnail': item.thumbnail.url if item.image else None,
            'allergens': item.allergens,
            'description': item.description,
            'category': item.category,
            'organic': item.organic,
            'producer': item.producer.organisation_name,
            'organic_description': item.producer.organic_description,
            'avg_rating': round(item.avg_rating, 1) if item.avg_rating else None,
            'review_count': item.review_count,
            'food_miles': item.food_miles
        } for item in items_list]
        return JsonResponse({
            'items': data,
            'count': total_count,
            'suggestion': suggestion,
            'batch_data': batch_data,
            'review_data': review_data,
            'recipe_suggestions': recipe_suggestions,
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
        'recipe_suggestions': recipe_suggestions,
        'cart_items': cart,
        'cart_total_price': round(total_price, 2),
        'selected_categories': categories,
        'discounted': request.GET.get('discounted'),
        'organic': request.GET.get('organic'),
        'exclude_allergens': exclude_allergens,
        'allergen_list': allergen_list,
        'search_query': q,
        'suggestion': suggestion,
        'page_obj': page_obj,
        'total_count': total_count,
    })

    
def get_producers_api(request):
    q = request.GET.get('q', '')
    producers = User.objects.filter(category='Producer')
    if q:
        producers = producers.filter(organisation_name__icontains=q)
    producers = producers.values('id', 'organisation_name')
    return JsonResponse(list(producers), safe=False)

@login_required
def add_to_cart(request, product_id):
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
        request.user.notifications_cleared_at = timezone.now()
        request.user.save(update_fields=['notifications_cleared_at'])
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
                request.session.update(food_mile_session_builder(user))
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

            all_year = 'all_year' in request.POST
            season_start = request.POST.get('season_start', 'January')
            season_end = request.POST.get('season_end', 'December')

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
                    'all_year': all_year,
                    'seasonStart': season_start,
                    'seasonEnd': season_end,
                }
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
            surplus_discount_pct = Decimal(request.POST.get('surplus_discount_percentage') or '20')
            best_before_str = request.POST.get('best_before')

            # Resolve final quality class before writing to DB
            if quality_class != 'Discounted' and best_before_str:
                best_before_date = date_type.fromisoformat(best_before_str)
                days = SURPLUS_DAYS.get(product.category, 5)
                if best_before_date <= date_type.today() + timedelta(days=days):
                    quality_class = 'Discounted'

            surplus = quality_class == 'Discounted'
            class_discounts = {'A': Decimal('0'), 'B': Decimal('15'), 'C': Decimal('30'), 'D': Decimal('45'), 'Discounted': Decimal('50')}
            if quality_class == 'Discounted':
                discount_pct = Decimal(request.POST.get('discount_percentage') or str(surplus_discount_pct))
            else:
                discount_pct = class_discounts.get(quality_class, Decimal('0'))

            ref_batch = product.batches.filter(quality_class='A').order_by('-created_at').first() \
                        or product.batches.order_by('-created_at').first()
            season_start = ref_batch.seasonStart if ref_batch else 'January'
            season_end = ref_batch.seasonEnd if ref_batch else 'December'
            harvest_date = request.POST.get('harvest_date') or None
            ProductBatch.objects.create(
                product=product,
                quality_class=quality_class,
                stock=int(request.POST.get('stock') or 1),
                harvest_date=harvest_date,
                best_before=best_before_str,
                seasonStart=season_start,
                seasonEnd=season_end,
                surplus=surplus,
                discount_percentage=discount_pct,
                discount_note=request.POST.get('discount_note', ''),
                image=request.FILES.get('image'),
                max_order_qty=int(request.POST['max_order_qty']) if request.POST.get('max_order_qty') else None,
                surplus_discount_percentage=surplus_discount_pct,
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
            category = form.cleaned_data.get('category')

            if category == User.Category.PRODUCER:
                details = (
                    f"Name: {form.cleaned_data.get('full_name')}\n"
                    f"Email: {form.cleaned_data.get('email')}\n"
                    f"Organisation: {form.cleaned_data.get('organization_name', '')}\n"
                    f"Phone: {form.cleaned_data.get('phone', '')}\n"
                    f"Address: {form.cleaned_data.get('address', '')}, {form.cleaned_data.get('postcode', '')}"
                )
                send_mail(
                    subject="New Producer Application",
                    message=f"A new producer has applied for an account:\n\n{details}",
                    from_email=settings.ADMIN_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
                messages.success(
                    request,
                    "Thank you for applying as a producer! Your application is under review — we'll be in touch by email shortly."
                )
                return redirect("home")

            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.set_expiry(0)
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
        'orderproduct_set__batch__product__producer')
    if order_code:
        order = order_qs.filter(id__startswith=order_code).order_by('order_date').first()
    else:
        order = order_qs.order_by('order_date').first()

    invoice_items = []
    subtotal = Decimal('0.00')
    commission_rate = Decimal('5.00')
    commission_amount = Decimal('0.00')
    total = Decimal('0.00')

    if order:
        for item in order.orderproduct_set.all():
            line_total = item.numPurchased * item.price_at_purchase
            subtotal += line_total
            producer = item.batch.product.producer
            invoice_items.append({
                'name': item.batch.product.name,
                'quality_class': item.batch.quality_class,
                'producer_name': producer.organisation_name or ' '.join(filter(None, [producer.first_name, producer.last_name])) or producer.email,
                'quantity': item.numPurchased,
                'unit_price': item.price_at_purchase,
                'line_total': line_total,
                'best_before': item.batch.best_before,
                'unit': item.batch.product.unit,
            })
        commission_amount = subtotal * (commission_rate / Decimal('100.00'))
        total = subtotal

    customer_name = None
    if order:
        c = order.customer
        full = ' '.join(filter(None, [c.first_name, c.last_name]))
        customer_name = c.organisation_name or full or c.email

    context = {
        'order': order,
        'customer_name': customer_name,
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
    modal_id_field = None
    if selected_model_name:
        # For the Order model, show one ProducerOrder row per producer slice
        # so each producer's status is independent and admins see per-producer rows
        if selected_model_name == 'Order':
            if is_superuser:
                selected_model = app_config.get_model('Order')
                readonly_fields = {'customer', 'total_price', 'order_status'}
                selected_data = get_management_context(
                    request, selected_model, 'Order',
                    add_new=False, row_filter={}, distinct=False,
                    readonly_fields=readonly_fields)
            else:
                selected_model = app_config.get_model('ProducerOrder')
                readonly_fields = {'order', 'producer'}
                selected_data = get_management_context(
                    request, selected_model, 'ProducerOrder',
                    add_new=False, row_filter={'producer': request.user},
                    distinct=False, readonly_fields=readonly_fields)
        else:
            # Producer specific handling for non-Order models
            if not is_superuser and user_category == 'Producer':
                row_filter = {
                    'Product':      {'producer': request.user},
                    'ProductBatch': {'product__producer': request.user},
                    'StoryPost':    {'user': request.user},
                    'Recipe':       {'user': request.user},
                }.get(selected_model_name, {})
                if selected_model_name in ('Product', 'StoryPost', 'Recipe'):
                    owner_field = 'producer' if selected_model_name == 'Product' else 'user'
                    readonly_fields = {owner_field}
                elif selected_model_name == 'ProductBatch':
                    readonly_fields = {'product'}

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
    recipes = Recipe.objects.select_related('user').prefetch_related('recipeingredients_set__product').order_by('-id')
    stories = StoryPost.objects.select_related('user').order_by('-date_posted')
    return render(request, 'community.html', {
        'recipes': recipes,
        'stories': stories,
    })


@login_required
def recipe_detail(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    ingredients = recipe.recipeingredients_set.select_related('product').all()
    is_favourite = (
        request.user.is_authenticated and
        FavouriteRecipe.objects.filter(user=request.user, recipe=recipe).exists()
    )
    return render(request, 'recipe_detail.html', {
        'recipe': recipe,
        'ingredients': ingredients,
        'is_favourite': is_favourite,
    })


@login_required
def add_recipe(request):
    if request.user.category != User.Category.PRODUCER:
        messages.error(request, "Only producers can create recipes.")
        return redirect('community')

    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        ingredient_ids = request.POST.getlist('ingredient_ids')
        quantities = request.POST.getlist('ingredient_quantities')
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            for pid, qty in zip(ingredient_ids, quantities):
                if pid:
                    try:
                        product = Product.objects.get(pk=pid, producer=request.user)
                        RecipeIngredients.objects.get_or_create(
                            recipe=recipe, product=product,
                            defaults={'quantity': qty or ''}
                        )
                    except Product.DoesNotExist:
                        pass
            messages.success(request, f'Recipe "{recipe.title}" published!')
            return redirect('community')
    else:
        form = RecipeForm()

    producer_products = Product.objects.filter(producer=request.user).order_by('name')
    return render(request, 'recipe_form.html', {
        'form': form,
        'producer_products': producer_products,
        'action': 'Create',
    })


@login_required
def edit_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        ingredient_ids = request.POST.getlist('ingredient_ids')
        quantities = request.POST.getlist('ingredient_quantities')
        if form.is_valid():
            form.save()
            recipe.recipeingredients_set.all().delete()
            for pid, qty in zip(ingredient_ids, quantities):
                if pid:
                    try:
                        product = Product.objects.get(pk=pid, producer=request.user)
                        RecipeIngredients.objects.create(recipe=recipe, product=product, quantity=qty or '')
                    except Product.DoesNotExist:
                        pass
            messages.success(request, "Recipe updated.")
            return redirect('community')
    else:
        form = RecipeForm(instance=recipe)

    producer_products = Product.objects.filter(producer=request.user).order_by('name')
    existing_ingredients = list(recipe.recipeingredients_set.select_related('product').all())
    return render(request, 'recipe_form.html', {
        'form': form,
        'producer_products': producer_products,
        'existing_ingredients': existing_ingredients,
        'action': 'Edit',
        'recipe': recipe,
    })


@login_required
def delete_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)
    if request.method == 'POST':
        recipe.delete()
        messages.success(request, "Recipe deleted.")
    return redirect('community')


@login_required
def add_story(request):
    if request.user.category != User.Category.PRODUCER:
        messages.error(request, "Only producers can post farm stories.")
        return redirect('community')

    if request.method == 'POST':
        form = StoryPostForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.user = request.user
            story.save()
            messages.success(request, "Farm story published!")
            return redirect('community')
    else:
        form = StoryPostForm()

    return render(request, 'story_form.html', {'form': form, 'action': 'Create'})


@login_required
def edit_story(request, story_id):
    story = get_object_or_404(StoryPost, id=story_id, user=request.user)
    if request.method == 'POST':
        form = StoryPostForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, "Story updated.")
            return redirect('community')
    else:
        form = StoryPostForm(instance=story)

    return render(request, 'story_form.html', {'form': form, 'action': 'Edit', 'story': story})


@login_required
def delete_story(request, story_id):
    story = get_object_or_404(StoryPost, id=story_id, user=request.user)
    if request.method == 'POST':
        story.delete()
        messages.success(request, "Story deleted.")
    return redirect('community')


@login_required
def story_detail(request, story_id):
    story = get_object_or_404(StoryPost, id=story_id)
    return render(request, 'story_detail.html', {'story': story})


@login_required
def toggle_favourite_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    fav, created = FavouriteRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        fav.delete()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'community'
    return redirect(next_url)


@login_required
def report_content(request):
    if request.method == 'POST':
        content_type = request.POST.get('content_type')
        content_id = request.POST.get('content_id')
        if content_type == 'recipe':
            Recipe.objects.filter(id=content_id).update(is_flagged=True)
        elif content_type == 'story':
            StoryPost.objects.filter(id=content_id).update(is_flagged=True)
        messages.success(request, "Content reported. Our team will review it shortly.")
    return redirect(request.POST.get('next') or 'community')


def producer_profile_public(request, producer_id):
    producer = get_object_or_404(User, id=producer_id, category=User.Category.PRODUCER)
    recipes = Recipe.objects.filter(user=producer).prefetch_related('recipeingredients_set__product').order_by('-id')
    stories = StoryPost.objects.filter(user=producer).order_by('-date_posted')
    products = Product.objects.filter(producer=producer).prefetch_related('batches')
    return render(request, 'producer_profile_public.html', {
        'producer': producer,
        'recipes': recipes,
        'stories': stories,
        'products': products,
    })


@login_required
def get_order_summary_json(request, order_id):
    """
    Returns order summary data for the management modal.
    Producers see only their ProducerOrder slice; superusers see all items combined.
    """
    try:
        is_producer = not request.user.is_superuser and getattr(request.user, 'category', None) == 'Producer'

        # order_id may be a ProducerOrder UUID (from table rows) or an Order UUID (legacy)
        clicked_po = None
        try:
            clicked_po = ProducerOrder.objects.select_related('order__customer').get(pk=order_id)
            order = clicked_po.order
        except ProducerOrder.DoesNotExist:
            order = Order.objects.select_related('customer').get(pk=order_id)

        # Resolve which ProducerOrder(s) to draw from
        producer_orders_data = None
        if is_producer:
            po = clicked_po or order.producer_orders.get(producer=request.user)
            status = po.order_status
            advance_url = f"/management/order/{po.id}/advance/" if status in ('PENDING', 'CONFIRMED') else None
            next_status = {'PENDING': 'CONFIRMED', 'CONFIRMED': 'READY'}.get(status)
            items = list(po.items.select_related('batch__product__producer'))
            history_qs = po.status_history.all()
        else:
            status = order.order_status
            advance_url = None
            next_status = None
            all_pos = order.producer_orders.select_related('producer').order_by('delivery_date')
            producer_orders_data = []
            for sub_po in all_pos:
                sub_status = sub_po.order_status
                sub_advance = f"/management/order/{sub_po.id}/advance/" if sub_status in ('PENDING', 'CONFIRMED') else None
                sub_next = {'PENDING': 'CONFIRMED', 'CONFIRMED': 'READY'}.get(sub_status)
                prod = sub_po.producer
                sub_history = sub_po.status_history.select_related('changed_by').order_by('changed_at')
                producer_orders_data.append({
                    'id': str(sub_po.id),
                    'producer': prod.organisation_name or prod.full_name or prod.email,
                    'status': sub_status,
                    'delivery_date': sub_po.delivery_date.strftime('%Y-%m-%d') if sub_po.delivery_date else '',
                    'advance_url': sub_advance,
                    'next_status': sub_next,
                    'history': [
                        {
                            'from': h.from_status,
                            'to': h.to_status,
                            'by': h.changed_by.email if h.changed_by else '—',
                            'at': h.changed_at.strftime('%d %b %Y %H:%M'),
                            'note': h.note,
                        }
                        for h in sub_history
                    ],
                })
            items = list(order.orderproduct_set.select_related('batch__product__producer'))
            history_qs = []  # history is embedded per-producer in producer_orders_data

        receipt_data = []
        for item in items:
            stock_now = item.batch.stock
            entry = {
                'name': item.batch.product.name,
                'quality_class': item.batch.get_quality_class_display(),
                'best_before': item.batch.best_before.strftime('%Y-%m-%d') if item.batch.best_before else '',
                'batch_number': item.batch.batch_number,
                'qty': item.numPurchased,
                'price': f"{item.batch.price:.2f}",
                'total': f"{item.numPurchased * item.batch.price:.2f}",
                'stock_now': stock_now,
                'stock_after': stock_now - item.numPurchased,
            }
            if not is_producer:
                p = item.batch.product.producer
                entry['producer'] = p.organisation_name or p.full_name or p.email
            receipt_data.append(entry)

        visible_total = sum(item.numPurchased * item.batch.price for item in items)
        effective_delivery = (po.delivery_date if is_producer else None) or order.delivery_date
        data = {
            'status': status,
            'advance_url': advance_url,
            'next_status': next_status,
            'producer_orders': producer_orders_data,
            'customer_name': order.customer.full_name or order.customer.email,
            'customer_type': order.customer.category,
            'email': order.customer.email,
            'phone': order.customer.phone,
            'address': f"{order.customer.address}, {order.customer.postcode}" if order.customer.address and order.customer.postcode else '',
            'instructions': order.special_instructions,
            'order_date': order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else '',
            'delivery_date': effective_delivery.strftime('%Y-%m-%d') if effective_delivery else '',
            'recurrence': f"{order.get_recurrence_day_display()} ({order.recurrence_type})" if order.recurrence_type != 'None' else '',
            'total_price': f"{order.total_price:.2f}",
            'visible_total': f"{visible_total:.2f}",
            'show_producer_col': not is_producer,
            'receipt': receipt_data,
            'status_history': [
                {
                    'from': h.from_status,
                    'to': h.to_status,
                    'by': h.changed_by.email if h.changed_by else '—',
                    'at': h.changed_at.strftime('%d %b %Y %H:%M'),
                    'note': h.note,
                }
                for h in history_qs
            ],
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


def auto_update_order_statuses():
    """Auto-update ProducerOrders when delivery date has passed, then sync parent Order."""
    now = timezone.now()

    ready_due = ProducerOrder.objects.filter(order_status='READY', delivery_date__lte=now).select_related('order')
    OrderStatusHistory.objects.bulk_create([
        OrderStatusHistory(producer_order=po, from_status='READY', to_status='DELIVERED',
                           changed_by=None, note='Auto-delivered: delivery date reached.')
        for po in ready_due
    ])
    affected_orders = set(po.order_id for po in ready_due)
    ready_due.update(order_status='DELIVERED')

    unacknowledged = ProducerOrder.objects.filter(
        order_status__in=('PENDING', 'CONFIRMED'), delivery_date__lte=now
    ).select_related('order')
    OrderStatusHistory.objects.bulk_create([
        OrderStatusHistory(producer_order=po, from_status=po.order_status, to_status='CANCELLED',
                           changed_by=None, note='Auto-cancelled: delivery date passed without fulfilment.')
        for po in unacknowledged
    ])
    affected_orders |= set(po.order_id for po in unacknowledged)
    unacknowledged.update(order_status='CANCELLED')

    for order in Order.objects.filter(id__in=affected_orders):
        order.sync_status()


@management_access_required
def advance_order_status(request, producer_order_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        po = ProducerOrder.objects.select_related('order', 'producer').get(pk=producer_order_id)
    except ProducerOrder.DoesNotExist:
        return JsonResponse({'error': 'ProducerOrder not found'}, status=404)

    if not request.user.is_superuser and po.producer != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    current = po.order_status
    try:
        next_status = STATUS_SEQUENCE[STATUS_SEQUENCE.index(current) + 1]
    except (ValueError, IndexError):
        return JsonResponse({'error': 'Already at final status'}, status=400)

    note = request.POST.get('note', '').strip()
    OrderStatusHistory.objects.create(
        producer_order=po,
        from_status=current,
        to_status=next_status,
        changed_by=request.user,
        note=note,
    )
    po.order_status = next_status
    po.save(update_fields=['order_status'])
    po.order.sync_status()
    messages.success(request, f"Order {str(producer_order_id)[:8]} advanced to {next_status.title()}.")
    return redirect(request.META.get('HTTP_REFERER', 'management'))


@login_required
def profile_view(request):
    """Display the logged-in user's profile page."""
    product_count = None
    recipes = None
    stories = None
    recipe_count = 0
    story_count = 0
    saved_recipes = None

    if request.user.category == 'Producer':
        product_count = Product.objects.filter(producer=request.user).count()
        recipes = Recipe.objects.filter(user=request.user).order_by('-id')
        stories = StoryPost.objects.filter(user=request.user).order_by('-date_posted')
        recipe_count = recipes.count()
        story_count = stories.count()
    else:
        saved_recipes = FavouriteRecipe.objects.filter(
            user=request.user
        ).select_related('recipe__user').order_by('-saved_at')

    if request.method == 'POST' and request.user.category == 'Producer':
        request.user.organic_description = request.POST.get('organic_description', '').strip()
        request.user.save(update_fields=['organic_description'])
        messages.success(request, 'Organic certification updated.')
        return redirect('profile')

    return render(request, 'profile.html', {
        'product_count': product_count,
        'recipes': recipes,
        'stories': stories,
        'recipe_count': recipe_count,
        'story_count': story_count,
        'saved_recipes': saved_recipes,
    })



@login_required
def edit_profile(request):
    category = getattr(request.user, 'category', None)
    if request.method == "POST":
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user, category=category)
        password_form = PasswordChangeForm(request.user, request.POST)

        if "update_profile" in request.POST:
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")

        elif "change_password" in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect("profile")

    else:
        profile_form = ProfileEditForm(instance=request.user, category=category)
        password_form = PasswordChangeForm(request.user)

    return render(request, "edit_profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })


def terms_view(request):
    """Display the terms and conditions / cookie policy page."""
    return render(request, 'terms.html')


def submit_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            if request.user.is_authenticated:
                complaint.submitted_by = request.user
            complaint.save()
            messages.success(request, "Your complaint has been submitted. Our compliance team will review it shortly.")
            return redirect('home')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {'name': request.user.full_name or '', 'email': request.user.email}
        form = ComplaintForm(initial=initial)
    return render(request, 'complaint_form.html', {'form': form})


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.category == User.Category.PRODUCER:
        if product.producer == request.user:
            messages.error(request, "You cannot review your own products.")
            return redirect("orders")

    delivered_purchase = OrderProduct.objects.filter(
        batch__product=product,
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


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated.")
            return redirect("orders")
    else:
        form = ReviewForm(instance=review)
    return render(request, "edit_review.html", {"form": form, "product": review.product})


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
    return redirect("orders")


@login_required
def finance_view(request):
    user = request.user
    is_admin = user.is_superuser or user.category == 'Admin'
    

    date_from = request.GET.get('from')
    date_to = request.GET.get('to')

    payments = Payment.objects.select_related('producer', 'order').all()

    # Only filter if user provides dates
    if date_from:
        date_from = parse_date(date_from)
        date_from_dt = timezone.make_aware(datetime_type.combine(date_from, time.min))
        payments = payments.filter(created_at__gte=date_from_dt)

    if date_to:
        date_to = parse_date(date_to)
        date_to_dt = timezone.make_aware(datetime_type.combine(date_to, time.max))
        payments = payments.filter(created_at__lte=date_to_dt)

    payments = payments.order_by('-created_at')
    
    if not is_admin:
        payments = payments.filter(producer=user)
        
    # Generate CSV if requested
    if request.GET.get('format') == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="finance_report_{date_from}_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Order ID', 'Producer', 'Order Total', 'Commission (5%)', 'Net Payment (95%)', 'Status'])
        
        for p in payments:
            order_total = p.order.total_price
            commission = (order_total * Decimal('0.05')).quantize(Decimal('0.01'))
            net = (order_total * Decimal('0.95')).quantize(Decimal('0.01'))
            writer.writerow([
                p.created_at.strftime('%Y-%m-%d'),
                str(p.order.id)[:8],
                p.producer.organisation_name or p.producer.email,
                order_total,
                commission,
                net,
                p.status
            ])
        return response
    print(Payment.objects.count())
    print(Payment.objects.first().created_at)
    # Prepare data for template
    report_data = []
    total_network_commission = Decimal('0')
    total_producer_payout = Decimal('0')
    
    for p in payments:
        order_total = p.order.total_price
        commission = (order_total * Decimal('0.05')).quantize(Decimal('0.01'))
        net = (order_total * Decimal('0.95')).quantize(Decimal('0.01'))
        total_network_commission += commission
        total_producer_payout += net
        
        report_data.append({
            'date': p.created_at,
            'order_id': str(p.order.id),
            'producer': p.producer.organisation_name or p.producer.email,
            'order_total': order_total,
            'commission': commission,
            'producer_payment': net,
            'status': p.status,
        })
        
    context = {
        'report_data': report_data,
        'total_network_commission': total_network_commission,
        'total_producer_payout': total_producer_payout,
        'date_from': date_from,
        'date_to': date_to,
        'is_admin': is_admin,
    }
    
    return render(request, 'finance.html', context)
