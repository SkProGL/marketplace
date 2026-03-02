from django.shortcuts import render, redirect
from core.forms import LoginForm, ItemForm
from .models import Item
# Create your views here.

def home_view(request):
    items = Item.objects.all() # Fetch all items from Postgres
    return render(request, 'home.html', {'items': items})
def login_view(request):
    form = LoginForm()
    return render(request, 'login.html', {'form': form})
def upload_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES) # request.FILES handles the image
        if form.is_valid():
            form.save()
            return redirect('home') # Redirect after successful upload
    else:
        form = ItemForm()
    return render(request, 'inventory_upload.html', {'form': form})