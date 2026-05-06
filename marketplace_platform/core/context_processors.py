
from core.utils import get_low_stock_products, get_pending_orders
from .models import OrderStatusHistory, ProductBatch
def navbar_alerts(request):
    """
    Navigation bar notification bell.
    Producers: low stock + pending orders.
    Customers: order status changes.
    """
    LIMIT = 4
    if not request.user.is_authenticated:
        return {"navbar_alerts": [], "navbar_alert_count": 0, "navbar_total_alert_count": 0}

    alerts = []
    category = getattr(request.user, 'category', None)

    if request.user.is_superuser or category in ('Producer', 'Admin'):
        cleared_at = getattr(request.user, 'notifications_cleared_at', None)
        for product in get_low_stock_products(request.user):
            alerts.append({
                "key": f"stock_{product.id}",
                "icon": "exclamation-triangle-fill",
                "colour": "warning" if product.stock > 0 else "danger",
                "message": product.name,
                "message_status": f"{product.stock} left" if product.stock > 0 else "Out of stock",
                "link_url": '/management/?model=Product',
                "link_label": "Manage products",
            })
        pending_qs = get_pending_orders(request.user)
        if cleared_at:
            pending_qs = pending_qs.filter(order_date__gt=cleared_at)
        for order in pending_qs:
            key = f"order_{order.id}"
            items = list(order.orderproduct_set.select_related("batch__product"))
            names = [i.batch.product.name for i in items[:2]]
            suffix = f" +{len(items) - 2} more" if len(items) > 2 else ""
            alerts.append({
                "key": key,
                "icon": "bag-check-fill",
                "colour": "success",
                "message": "Outstanding order:",
                "message_status": ", ".join(names) + suffix,
                "link_url": '/management/?model=Order',
                "link_label": "View orders",
            })

    if category == 'Customer':
        cleared_at = request.user.notifications_cleared_at
        qs_filter = {'order__customer': request.user, 'changed_by__isnull': False}
        if cleared_at:
            qs_filter['changed_at__gt'] = cleared_at
        recent_changes = (OrderStatusHistory.objects
                          .filter(**qs_filter)
                          .select_related('order')
                          .prefetch_related('order__orderproduct_set__batch__product')
                          .order_by('-changed_at')[:5])
        for h in recent_changes:
            key = f"status_{h.id}"
            items = list(h.order.orderproduct_set.all())
            names = [i.batch.product.name for i in items[:2]]
            suffix = f" +{len(items) - 2} more" if len(items) > 2 else ""
            item_summary = ", ".join(names) + suffix
            alerts.append({
                "key": key,
                "icon": "bag-check-fill",
                "colour": "success",
                "message": f"Your order for {item_summary}:",
                "message_status": f"{h.from_status.title()} → {h.to_status.title()}",
                "note": h.note or "",
                "link_url": '/orders/',
                "link_label": "View your orders",
            })
    visible = alerts[-LIMIT:]
    return {"navbar_alerts": visible, "navbar_alert_count": len(visible), "navbar_total_alert_count": len(alerts)}


def get_producer_alerts(request):
    """Notification badges for management panel"""

    warning_count = 0
    error_count = 0
    pending_orders = 0
    if not request.user.is_authenticated:
        return {'stock_alert': {'warning_count': 0, 'error_count': 0, 'pending_orders': 0, 'total': 0}}

    category = getattr(request.user, 'category', None)
    if not (request.user.is_superuser or category == 'Producer'):
        return {'stock_alert': {'warning_count': 0, 'error_count': 0, 'pending_orders': 0, 'total': 0}}

    pending_orders = get_pending_orders(request.user).count()
    for product in get_low_stock_products(request.user):
        if product.stock == 0:
            error_count += 1
        else:
            warning_count += 1

    total = warning_count + error_count + pending_orders
    return {'stock_alert': {'warning_count': warning_count, 'error_count': error_count, 'pending_orders': pending_orders, 'total': total}}

def cart_processor(request):
    cart = request.session.get('cart', {})
    total_items = sum(cart.values())
    total_price = 0
    if cart:
        batches = ProductBatch.objects.filter(id__in=cart.keys())
        for batch in batches:
            quantity = cart.get(str(batch.id), 0)
            total_price += batch.price * quantity

    return {
        'cart_total_items': total_items,
        'cart_total_price': f"{total_price:.2f}"
    }
