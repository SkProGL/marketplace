from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from core.forms import LoginForm, ProductForm
from .models import User, Product, Order, Recipe, StoryPost
from django.db.models import Count

# Create your views here.
from django.contrib.auth import get_user_model
User = get_user_model()


def home_view(request):
    items = Product.objects.all()  # Fetch all items from Postgres
    return render(request, 'home.html', {'items': items})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Check if these credentials match a user in the DB
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('home')  # Go to the marketplace
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def upload_item(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            if request.user.is_authenticated:
                product.producer = User.objects.get(pk=request.user.pk)
                product.save()
                return redirect('home')
            else:
                return HttpResponse("You must be logged in to upload.")
    else:
        form = ProductForm()
    return render(request, 'inventory_upload.html', {'form': form})


def signup_view(request):
    return render(request, 'signup.html')


def invoice_view(request):
    return render(request, 'invoice.html')

def order_history_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    orders = Order.objects.filter(customer=request.user).order_by('-order_date')
    recommendations = (
        Order.objects.filter(customer=request.user)
        .values('product')
        .annotate(count=Count('product'))
        .order_by('-count')[:3]
    )
    recs_with_products = []
    for r in recommendations:
        recs_with_products.append({
            'product': Product.objects.get(pk=r['product']),
            'count': r['count']
        })
    return render(request, 'order_history.html', {
        'orders': orders,
        'recommendations': recs_with_products
    })


def community_view(request):
    recipes = Recipe.objects.all().order_by('-id')
    stories = StoryPost.objects.all().order_by('-date_posted')
    return render(request, 'community.html', {
        'recipes': recipes,
        'stories': stories
    })