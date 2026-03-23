
from core.utils import get_low_stock_products, get_pending_orders
from django.urls import reverse


def navbar_alerts(request):
    """
    Navigation bar notification bell.
    Pass incoming order and stock warning counts for given user
    """
    # validate that user is authenticated AND a producer
    if not request.user.is_authenticated or getattr(request.user, 'category', None) != 'Producer':
        return {"navbar_alerts": [], "navbar_alert_count": 0}

    alerts = []

    # Iterate over all producer products and append stock alerts (stock threshold or stock == 0)
    for product in get_low_stock_products(request.user):
        alerts.append({
            "icon": "exclamation-triangle-fill",
            "colour": "warning" if product.stock > 0 else "danger",
            "message": f"Low stock: {product.name} ({product.stock} left)" if product.stock > 0 else f"No stock: {product.name}",
            "link_url": '/management/?model=Product',
            "link_label": "Manage products",
        })

    # Iterate through all assigned orders and append pending order alerts
    for order in get_pending_orders(request.user):
        items = order.orderproduct_set.select_related("product")
        # if not items:
        #     continue
        item_summary = ", ".join(f"{item.product.name} x {item.numPurchased}" for item in items)
        alerts.append({
            "icon": "bag-check-fill",
            "colour": "success",
            "message": f"New order: {item_summary} from {order.customer.email}",
            "link_url": '/management/?model=Order',
            "link_label": "View orders",
        })
    return {"navbar_alerts": alerts, "navbar_alert_count": len(alerts)}


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

