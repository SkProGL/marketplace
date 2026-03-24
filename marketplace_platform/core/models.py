from django.db import models
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

# Define Custom UserManager to set emial as username
class UserManager(BaseUserManager):
    # Override to remove emial requirement
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email=self.normalize_email(email)
        user=self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return User

class User(AbstractUser):
    class Category(models.TextChoices):
        CUSTOMER = "Customer"
        PRODUCER = "Producer"
        COMMUNITY = "Community","Community Group"
        RESTAURANT = "Restaurant"
        ADMIN = "Admin"

    # Aplly custom UserManager for email-based superuser creation
    objects = UserManager()
    # Disable default AbstractUser fields
    username = None
    first_name = None
    last_name = None
    #  Set email as default for authentication
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    email = models.EmailField(unique=True)

    # Primary key as UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    full_name = models.CharField(max_length=128, blank=True, default="")
    # User category
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.CUSTOMER)
    # Phone number
    phone = models.CharField(max_length=20, blank=True)
    # Address fields
    address = models.CharField(max_length=256, blank=True)
    postcode = models.CharField(max_length=20, blank=True)

    # Organisation name for producers, restaurants and community groups
    organisation_name = models.CharField(
        max_length=128, blank=True, default="")
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


    def __str__(self):
        return self.email


class Product(models.Model):
    # List of food categories
    class Category(models.TextChoices):
        VEGETABLE = "Vegetable"
        FRUIT = "Fruit"
        DAIRY = "Dairy"
        BAKERY = "Bakery"
        PRESERVE = "Preserve"

    # Seasonal availability options
    class SeasonalAvailability(models.TextChoices):
        AV = "Available"
        UN = "Unavailable"
        AAY = "Available All Year"

    # Months of the year for seasonal availability
    class Months(models.TextChoices):
        JAN = "January"
        FEB = "February"
        MAR = "March"
        APR = "April"
        MAY = "May"
        JUN = "June"
        JUL = "July"
        AUG = "August"
        SEP = "September"
        OCT = "October"
        NOV = "November"
        DEC = "December"

    # Units of measurement for products
    class Units(models.TextChoices):
        KG = "kg"
        G = "g"
        L = "l"
        ML = "ml"
        PCS = "pcs"
        BUNCH = "bunch"
        HEADS = "heads"
        DOZEN = "dozen"

    # Primary key as UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Foreign key - producer of the product, linked to User model
    producer = models.ForeignKey('core.User', on_delete=models.CASCADE)

    # Product name
    name = models.CharField(max_length=128)
    # Product category
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.VEGETABLE)
    # Detailed description of the product
    description = models.TextField()
    # Price of the product - max 10 digits, with 2 decimal places
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Unit of measurement
    unit = models.CharField(
        max_length=20, choices=Units.choices, default=Units.KG
    )
    # Seasonal availability
    availability = models.CharField(
        max_length=20, choices=SeasonalAvailability.choices, default=SeasonalAvailability.AV)
    # Season start and end
    seasonStart = models.CharField(
        max_length=20, choices=Months.choices, default=Months.JAN
    )
    seasonEnd = models.CharField(
        max_length=20, choices=Months.choices, default=Months.DEC
    )
    # Best before date
    best_before = models.DateField(default="2026-04-04")
    # Food miles - distance food travels from producer to customer
    food_miles = models.IntegerField(default=0)
    # Stock quantity
    stock = models.IntegerField(default=50)
    # Percentage to indicate how much stock is left before an alert is sent
    # stock_alert_threshold = models.DecimalField(
        # max_digits=5, decimal_places=2, default=0)
    # Replace with absolute number as perecentage needs max stock
    stock_alert_threshold = models.IntegerField()
    # List of food allergens
    allergens = ArrayField(models.CharField(
        max_length=128, blank=True), default=list)
    # Whether the product is organic-certified
    organic = models.BooleanField(default=False)
    # Whether the product is surplus and thus eligible for discounts
    surplus = models.BooleanField(default=False)
    # Discount percentage, stored as a decimal
    # For example, a 20% discount is stored as 20.00
    # Discounts would be calculated as price * (discount_percentage / 100)
    discount_percentage = models.DecimalField(
        max_digits=4, decimal_places=2, default=0)
    # Discount expiry date
    discount_expiry = models.DateTimeField(blank=True, null=True)
    # Note attached to discounts
    discount_note = models.TextField(blank=True)
    # Associated image
    image = models.ImageField(upload_to='item_images/', blank=True)

    def __str__(self):
        return f"{self.name} ({self.producer}) £{self.price}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        READY = "READY"
        DELIVERED = "DELIVERED"

    class Recurrence(models.TextChoices):
        NONE = "None"
        WEEKLY = "Weekly"
        FORTNIGHTLY = "Fortnightly"

    class Weekday(models.IntegerChoices):
        MON, TUE, WED, THUR, FRI, SAT, SUN = range(1, 8)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    products = models.ManyToManyField(
        Product,
        through="OrderProduct"
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField()
    order_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)
    special_instructions = models.TextField(blank=True)
    recurring = models.BooleanField(default=False)
    recurrence_type = models.CharField(
        max_length=20, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_day = models.IntegerField(
        choices=Weekday.choices, null=True, blank=True)
    # last_generated=models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return f"{self.customer} ({str(self.id)[:8]}) - {self.order_status} ({self.order_date.strftime('%d-%m-%Y %H:%M:%S')})"


class OrderProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    numPurchased = models.IntegerField()
    product_price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        unique_together = ("order", "product")
        
    @property
    def get_total_item_price(self):
        """Calculates the total cost for this specific item line"""
        return self.numPurchased * self.product.price
    
    def __str__(self):
        return f"{str(self.id)[:8]} - {self.order_status}"


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
    ingredients = models.ManyToManyField(
        "Product", through="RecipeIngredients")


class RecipeIngredients(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.CharField(max_length=30)

    class Meta:
        unique_together = ("recipe", "product")


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=128)
    content = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    date_posted = models.DateTimeField(auto_now_add=True)
    anonymous = models.BooleanField(default=False)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSED = "PROCESSED"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    orders = models.ManyToManyField("Order", blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

class OrderPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    class Meta:
        unique_together = ("order", "payment")
    date_posted=models.DateTimeField(auto_now_add=True)