from django.shortcuts import render, redirect
from core.forms import LoginForm
# Create your views here.

def home_view(request):
    return render(request, 'home.html') # A simple welcome page
def login_view(request):
    form = LoginForm()
    return render(request, 'login.html', {'form': form})
