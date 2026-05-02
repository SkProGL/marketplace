from django.urls import path
from .views import ai_generate, meal_search

urlpatterns = [
    path("meals/", meal_search),
    path("ai/", ai_generate),
]
