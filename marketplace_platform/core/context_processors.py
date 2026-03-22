# core/context_processors.py

def cart_processor(request):
    """Calculates the total number of individual items in the cart."""
    cart = request.session.get('cart', {})
    
    # Sum up all the quantities (the values in the dictionary)
    total_items = sum(cart.values())
    
    # This makes 'cart_total_items' available 
    return {'cart_total_items': total_items}