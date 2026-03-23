
from core.utils import get_low_stock_products, get_pending_orders

def get_producer_alerts(request):
    """Pass incoming order and stock warning counts for given user"""
    warning_count = 0
    error_count = 0
    pending_orders_count = 0
    if request.user.is_authenticated and getattr(request.user, 'category', None) == 'Producer':
        low_stock_products = get_low_stock_products(request.user)
        pending_orders_count = get_pending_orders(request.user).count()
        for product in low_stock_products:
            if product.stock == 0:
                error_count += 1
            else:
                warning_count +=1


    return {'stock_alert': {'warning_count': warning_count, 'error_count': error_count, 'pending_order_count': pending_orders_count}}
