from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Actor(models.Model):
    # create models here
    name = models.CharField(max_length=128)
    nationality = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(models.Model):
    class Category(models.TextChoices):
        CUSTOMER="Customer"
        PRODUCER="Producer"
        ORGANISATION="Organisation"
        ADMIN="Admin"

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name=models.CharField(max_length=128)
    email=models.EmailField(unique=True,max_length=254)
    category=models.CharField(max_length=20,choices=Category.choices,default=Category.CUSTOMER)
    phone=models.CharField(max_length=20)
    address=models.CharField(max_length=256)
    postcode=models.CharField(max_length=20)
    passwordHash=models.CharField(max_length=256)
    created=models.DateTimeField(auto_now_add=True)

class Product(models.Model):
    class Category(models.TextChoices):
        VEGETABLE="Vegetable","veg"
        FRUIT="Fruit"
        DAIRY="dairy"
        BAKERY="bakery"
        PRESERVE="preserve"
    class Season(models.TextChoices):
        SPRING="Spring"
        SUMMER="Summer"
        AUTUMN="Autumn"
        WINTER="Winter"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4, editable=False)
    producerID=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        editable=False
    )
    name=models.CharField(max_length=128)
    category=models.CharField(max_length=20,choices=Category.choices,default=Category.VEGETABLE)
    description=models.TextField()
    price=models.DecimalField(max_digits=10,decimal_places=2)
    unit=models.CharField(max_length=20)
    season=models.CharField(max_length=20,choices=Season.choices, default=Season.SPRING)
    food_miles=models.IntegerField()
    stock=models.IntegerField()
    allergens=ArrayField(models.CharField(max_length=128,blank=True))
    organic=models.BooleanField(default=False)
    surplus=models.BooleanField(default=False)
    imgsrc=models.CharField(max_length=128)

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING="PENDING"
        CONFIRMED="CONFIRMED"
        READY="READY"
        DELIVERED="DELIVERED"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    customerID=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        editable=False
    )
    productID=models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        editable=False
    )
    numPurchased=models.IntegerField()
    totalPrice=models.DecimalField(max_digits=10,decimal_places=2)
    orderDate=models.DateTimeField(auto_now_add=True)
    deliveryDate=models.DateTimeField()
    orderStatus=models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    specialInstructions=models.TextField(blank=True)

class StoryPost(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    userID=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        editable=False
    )
    content=models.TextField()
    imgsrc=models.CharField(max_length=128,blank=True)
    datePosted=models.DateTimeField(auto_now_add=True)

class Recipe(models.Model):
    class Season(models.TextChoices):
        SPRING="Spring"
        SUMMER="Summer"
        AUTUMN="Autumn"
        WINTER="Winter"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    userID=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        editable=False
    )
    title=models.CharField(max_length=128)
    description=models.TextField()
    imgsrc=models.CharField(max_length=128,blank=True)
    instructions=models.TextField()
    season=models.CharField(max_length=20,choices=Season.choices,default=Season.SPRING)
    ingredients=models.ManyToManyField(Product, through="RecipeIngredient")

class Review(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    userID=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        editable=False
    )
    orderID=models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        editable=False
    )
    title=models.CharField(max_length=128)
    content=models.TextField()
    rating=models.IntegerField(min_length=1,max_length=5)
    date_posted=models.DateTimeField(auto_now_add=True)