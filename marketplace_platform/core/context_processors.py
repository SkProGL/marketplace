from .models import Product, Order

LOW_STOCK_THRESHOLD = 10

def navbar_alerts(request):
    if not request.user.is_authenticated:
        return {"navbar_alerts": [], "navbar_alert_count": 0}

    alerts = []

    for product in Product.objects.filter(producer=request.user, stock__lt=LOW_STOCK_THRESHOLD).order_by("stock"):
        alerts.append({
            "icon": "exclamation-triangle-fill",
            "colour": "warning",
            "message": f"Low stock: {product.name} ({product.stock} left)",
            "link_url": "management",
            "link_label": "Manage products",
        })

    for order in Order.objects.filter(product__producer=request.user, order_status=Order.Status.PENDING).select_related("customer", "product").order_by("delivery_date"):
        alerts.append({
            "icon": "bag-check-fill",
            "colour": "success",
            "message": f"New order: {order.product.name} × {order.num_purchased} from {order.customer.username}",
            "link_url": "management",
            "link_label": "View orders",
        })

    return {"navbar_alerts": alerts, "navbar_alert_count": len(alerts)}
