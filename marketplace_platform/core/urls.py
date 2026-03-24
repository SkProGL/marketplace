# app/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('inventory_upload/', views.upload_item, name='inventory_upload'),
    path('invoice/<str:order_code>/', views.invoice_view, name='invoice'),
    path('community/', views.community, name='community'),
    # Recurring order URLS
    path('orders/recurring/', views.recurring_orders, name='recurring_orders'),
    path('orders/recurring/<uuid:order_id>/modify/', views.modify_next_occurrence, name='modify_next_occurrence'),
    # Order URLs
    path('order_history/', views.order_history, name='order_history'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/reorder/', views.reorder, name='reorder'),
    # Checkout URLs
    path('add-to-cart/<uuid:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/contents/', views.cart_contents, name='cart_contents'),
    path('cart/update/<uuid:product_id>/', views.update_cart_ajax, name='update_cart_ajax'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout, name='checkout'),
    # Management URLs
    path('management/', views.management_view, name="management"),
    path('profile/', views.profile_view, name='profile'),
    path('terms/', views.terms_view, name='terms'),
    path('management/order/<uuid:order_id>/order_summary/', views.get_order_summary_json, name='order_summary'),
] 
