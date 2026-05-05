
from core.utils import get_low_stock_products, get_pending_orders
from .models import OrderStatusHistory

def navbar_alerts(request):
    """
    Navigation bar notification bell.
    Producers: low stock + pending orders.
    Customers: order status changes.
    """
    LIMIT = 4
    if not request.user.is_authenticated:
        return {"navbar_alerts": [], "navbar_alert_count": 0, "navbar_total_alert_count": 0}

    dismissed = set(request.session.get('dismissed_notifications', []))
    alerts = []
    category = getattr(request.user, 'category', None)

    if request.user.is_superuser or category in ('Producer', 'Admin'):
        for product in get_low_stock_products(request.user):
            key = f"stock_{product.id}"
            alerts.append({
                "key": key,
                "icon": "exclamation-triangle-fill",
                "colour": "warning" if product.stock > 0 else "danger",
                "message": f"Low stock: {product.name} ({product.stock} left)" if product.stock > 0 else f"No stock: {product.name}",
                "link_url": '/management/?model=Product',
                "link_label": "Manage products",
            })
        for order in get_pending_orders(request.user):
            key = f"order_{order.id}"
            items = order.orderproduct_set.select_related("product")
            item_summary = ", ".join(f"{item.product.name} ({item.numPurchased})" for item in items)
            alerts.append({
                "key": key,
                "icon": "bag-check-fill",
                "colour": "success",
                "message": f"Outstanding order: {item_summary}",
                "link_url": '/management/?model=Order',
                "link_label": "View orders",
            })

    if category == 'Customer':
        recent_changes = (OrderStatusHistory.objects
                          .filter(order__customer=request.user, changed_by__isnull=False)
                          .select_related('order')
                          .order_by('-changed_at')[:5])
        for h in recent_changes:
            key = f"status_{h.id}"
            alerts.append({
                "key": key,
                "icon": "bag-check-fill",
                "colour": "success",
                "message": f"Order status updated: {h.from_status.title()} → {h.to_status.title()}",
                "link_url": '/orders/',
                "link_label": "View your orders",
            })
    visible = [a for a in alerts if a["key"] not in dismissed][-LIMIT:]
    return {"navbar_alerts": visible, "navbar_alert_count": len(visible), "navbar_total_alert_count": len(alerts)}


def get_producer_alerts(request):
    """Notification badges for management panel"""
    warning_count = 0
    error_count = 0
    pending_orders = 0
    if request.user.is_authenticated and getattr(request.user, 'category', None) == 'Producer':
        low_stock_products = get_low_stock_products(request.user)
        pending_orders = get_pending_orders(request.user).count()
        for product in low_stock_products:
            if product.stock == 0:
                error_count += 1
            else:
                warning_count +=1

    return {'stock_alert': {'warning_count': warning_count, 'error_count': error_count, 'pending_orders': pending_orders}}

# core/context_processors.py
from .models import Product
def cart_processor(request):
    cart = request.session.get('cart', {})
    # cart is assumed to be {product_id: {'price': x, 'quantity': y}}
    total_items = sum(cart.values())
    total_price = 0
    if cart:
        products = Product.objects.filter(id__in=cart.keys())
        for product in products:
            quantity = cart.get(str(product.id), 0)
            total_price += product.price * quantity

    return {
        'cart_total_items': total_items,
        'cart_total_price': f"{total_price:.2f}"
    }
