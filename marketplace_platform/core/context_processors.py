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