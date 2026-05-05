from django.urls import path
from core import views

urlpatterns = [
    # General/Account URLs
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('terms/', views.terms_view, name='terms'),
    path('review/<uuid:product_id>/', views.add_review, name='add_review'),
    path('community/', views.community, name='community'),
    path('inventory_upload/', views.upload_item, name='inventory_upload'),
    # Order URLs
    path('orders/', views.orders, name='orders'),
    path('orders/<uuid:order_id>/reorder/', views.reorder, name='reorder'),
    path('invoice/<str:order_code>/', views.invoice_view, name='invoice'),
    # Recurring order URLS
    path('orders/recurring/<uuid:order_id>/modify/', views.modify_recurring_order, name='modify_recurring_order'),
    path('orders/recurring/<uuid:order_id>/pause/', views.pause_recurring_order, name='pause_recurring_order'),
    path('orders/recurring/<uuid:order_id>/delete/', views.delete_recurring_order, name='delete_recurring_order'),
    # Checkout URLs
    path('add-to-cart/<uuid:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/contents/', views.cart_contents, name='cart_contents'),
    path('cart/update/<uuid:product_id>/', views.update_cart_ajax, name='update_cart_ajax'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    # Management URLs
    path('management/', views.management_view, name="management"),
    path('management/order/<uuid:order_id>/order_summary/', views.get_order_summary_json, name='order_summary'),
    path('management/search/', views.management_search, name='management_search'),
    path('management/order/<uuid:order_id>/advance/', views.advance_order_status, name='advance_order_status'),

] 
