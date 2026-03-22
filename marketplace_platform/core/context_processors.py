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

    for order in Order.objects.filter(orderproduct__product__producer=request.user, order_status=Order.Status.PENDING).select_related("customer").prefetch_related("orderproduct__product").order_by("delivery_date"):
        first_item = order.orderproduct_set.select_related("product").first()
        if not first_item:
            continue
        alerts.append({
            "icon": "bag-check-fill",
            "colour": "success",
            "message": f"New order: {first_item.product.name} × {first_item.numPurchased} from {order.customer.username}",
            "link_url": "management",
            "link_label": "View orders",
        })

    return {"navbar_alerts": alerts, "navbar_alert_count": len(alerts)}
