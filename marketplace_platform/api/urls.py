from django.urls import path
from .views import ai_generate

urlpatterns = [
    path("ai/", ai_generate),
]
