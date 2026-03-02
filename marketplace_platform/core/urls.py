# app/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'), 
    path('inventory_upload/', views.upload_item, name='inventory_upload'), 
] 