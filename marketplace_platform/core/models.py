from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid


class Actor(models.Model):
    # create models here
    name = models.CharField(max_length=128)
    nationality = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Category(models.TextChoices):
        CUSTOMER = "Customer"
        PRODUCER = "Producer"
        ORGANISATION = "Organisation"
        ADMIN = "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=256, blank=True)
    postcode = models.CharField(max_length=20, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )


class Product(models.Model):
    class Category(models.TextChoices):
        VEGETABLE = "Vegetable"
        FRUIT = "Fruit"
        DAIRY = "Dairy"
        BAKERY = "Bakery"
        PRESERVE = "Preserve"

    class Season(models.TextChoices):
        SPRING = "Spring"
        SUMMER = "Summer"
        AUTUMN = "Autumn"
        WINTER = "Winter"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producer = models.ForeignKey('core.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.VEGETABLE)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    season = models.CharField(
        max_length=20, choices=Season.choices, default=Season.SPRING)
    food_miles = models.IntegerField()
    stock = models.IntegerField()
    allergens = ArrayField(models.CharField(
        max_length=128, blank=True), default=list)
    organic = models.BooleanField(default=False)
    surplus = models.BooleanField(default=False)
    image = models.ImageField(upload_to='item_images/', blank=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        READY = "READY"
        DELIVERED = "DELIVERED"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, null=True, blank=True,
        on_delete=models.CASCADE
    )
    num_purchased = models.IntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField()
    order_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)
    special_instructions = models.TextField(blank=True)


class StoryPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    image = models.ImageField(upload_to='item_images/', blank=True)
    date_posted = models.DateTimeField(auto_now_add=True)


class Recipe(models.Model):
    class Season(models.TextChoices):
        SPRING = "Spring"
        SUMMER = "Summer"
        AUTUMN = "Autumn"
        WINTER = "Winter"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=128)
    description = models.TextField()
    image = models.ImageField(upload_to='item_images/', blank=True)
    instructions = models.TextField()
    season = models.CharField(
        max_length=20, choices=Season.choices, default=Season.SPRING)
    ingredients = models.ManyToManyField(Product)


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        Order, null=True, blank=True,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=128)
    content = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    date_posted = models.DateTimeField(auto_now_add=True)

class SavedRecipe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')