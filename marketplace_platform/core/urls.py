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
    path('management/', views.management_view, name="management")
] 
