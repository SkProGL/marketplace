# app/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('inventory_upload/', views.upload_item, name='inventory_upload'),
    path('invoice/', views.invoice_view, name='invoice'),
    path('order_history/', views.order_history, name='order_history'),
    path('community/', views.community, name='community'),
    # Management URLs
    path('management/', views.management_view, name="management"),
    path('management/order/<uuid:order_id>/order_summary/', views.get_order_summary_json, name='order_summary'),
] 
