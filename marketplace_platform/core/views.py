from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.db.models import Count
from django.contrib.auth import get_user_model
from .forms import LoginForm, ProductForm, RecipeForm, StoryForm
from .models import User, Product, Order, Recipe, StoryPost, SavedRecipe

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
    season = request.GET.get('season', '')
    recipes = Recipe.objects.all().order_by('-id')
    if season:
        recipes = recipes.filter(season=season)
    stories = StoryPost.objects.all().order_by('-date_posted')
    saved_ids = []
    if request.user.is_authenticated:
        saved_ids = SavedRecipe.objects.filter(user=request.user).values_list('recipe_id', flat=True)
    return render(request, 'community.html', {
        'recipes': recipes,
        'stories': stories,
        'saved_ids': saved_ids,
        'selected_season': season,
    })


def add_recipe_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = RecipeForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            form.save_m2m()
            return redirect('community')
    else:
        form = RecipeForm(user=request.user)
    return render(request, 'add_recipe.html', {'form': form})


def add_story_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.user = request.user
            story.save()
            return redirect('community')
    else:
        form = StoryForm()
    return render(request, 'add_story.html', {'form': form})


def save_recipe_view(request, recipe_id):
    if not request.user.is_authenticated:
        return redirect('login')
    recipe = Recipe.objects.get(pk=recipe_id)
    saved, created = SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        saved.delete()
    return redirect('community')