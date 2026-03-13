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
    path('orders/', views.order_history_view, name='order_history'),
    path('community/', views.community_view, name='community'),
    path('community/add-recipe/', views.add_recipe_view, name='add_recipe'),
    path('community/add-story/', views.add_story_view, name='add_story'),
    path('community/save/<uuid:recipe_id>/', views.save_recipe_view, name='save_recipe'),
]
