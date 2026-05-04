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
    # Unit of measurement
    unit = models.CharField(
        max_length=20, choices=Units.choices, default=Units.KG
    )
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

    def __str__(self):
        return f"{self.name} ({self.producer})"


class ProductBatch(models.Model):
    class QualityClass(models.TextChoices):
        A = "A", "A — Premium"
        B = "B", "B — Standard"
        C = "C", "C — Economy"
        D = "D", "D — Basic"
        Discounted = "Discounted", "Surplus / Discount"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=32, unique=True, blank=True)
    quality_class = models.CharField(
        max_length=10, choices=QualityClass.choices, default=QualityClass.A)

    # Price of the product - max 10 digits, with 2 decimal places
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Stock quantity
    stock = models.IntegerField()
    # Absolute number of units before a low-stock alert is sent
    stock_alert_threshold = models.IntegerField(default=0)
    # Associated image
    image = models.ImageField(upload_to='item_images/', blank=True)
    # Best before date
    best_before = models.DateField(default="2026-04-04")
    # Whether the product is surplus and thus eligible for discounts
    surplus = models.BooleanField(default=False)
    # Discount percentage (e.g. 20.00 = 20%)
    discount_percentage = models.DecimalField(
        max_digits=4, decimal_places=2, default=0)
    # Discount expiry date
    discount_expiry = models.DateTimeField(blank=True, null=True)
    # Note attached to discounts
    discount_note = models.TextField(blank=True)
    # Seasonal availability
    availability = models.CharField(
        max_length=20,
        choices=Product.SeasonalAvailability.choices,
        default=Product.SeasonalAvailability.AV)
    # Season start and end
    seasonStart = models.CharField(
        max_length=20, choices=Product.Months.choices, default=Product.Months.JAN)
    seasonEnd = models.CharField(
        max_length=20, choices=Product.Months.choices, default=Product.Months.DEC)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Convenience properties so templates can use batch.name, batch.producer etc. ---
    @property
    def name(self):
        return self.product.name

    @property
    def producer(self):
        return self.product.producer

    @property
    def category(self):
        return self.product.category

    @property
    def description(self):
        return self.product.description

    @property
    def allergens(self):
        return self.product.allergens

    def _generate_batch_number(self):
        from django.utils import timezone
        today = timezone.now().date()
        cat_code = self.product.category[:3].upper()
        org_name = self.product.producer.organisation_name or self.product.producer.email
        org_code = ''.join(w[0].upper() for w in org_name.split() if w)[:3]
        date_str = today.strftime('%Y%m%d')
        seq = self.__class__.objects.filter(
            product__producer=self.product.producer,
            created_at__date=today
        ).count() + 1
        return f"{cat_code}-{org_code}-{date_str}-{seq:03d}"

    def _compute_availability(self):
        from django.utils import timezone
        month_order = {v: i for i, v in enumerate(Product.Months.values, 1)}
        start = month_order.get(self.seasonStart, 1)
        end = month_order.get(self.seasonEnd, 12)
        if start == 1 and end == 12:
            return Product.SeasonalAvailability.AAY
        current = timezone.now().month
        in_season = (start <= current <= end) if start <= end else (current >= start or current <= end)
        return Product.SeasonalAvailability.AV if in_season else Product.SeasonalAvailability.UN

    def save(self, *args, **kwargs):
        if not self.batch_number:
            self.batch_number = self._generate_batch_number()
        self.availability = self._compute_availability()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch_number} — {self.product.name} £{self.price}"


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
        MON = 1, 'Monday'
        TUE = 2, 'Tuesday'
        WED = 3, 'Wednesday'
        THUR = 4, 'Thursday'
        FRI = 5, 'Friday'
        SAT = 6, 'Saturday'
        SUN = 7, 'Sunday'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    products = models.ManyToManyField(
        ProductBatch,
        through="OrderProduct"
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField()
    order_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)
    special_instructions = models.TextField(blank=True)
    recurring = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)  
    recurrence_type = models.CharField(
        max_length=20, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_day = models.IntegerField(
        choices=Weekday.choices, null=True, blank=True)

    @property
    def calculated_total(self):
        return sum(op.get_total_item_price for op in self.orderproduct_set.all())

    @property
    def calculated_total(self):
        return sum(op.get_total_item_price for op in self.orderproduct_set.all())

    def __str__(self):
        return f"{self.customer} ({str(self.id)[:8]}) - {self.order_status} ({self.order_date.strftime('%d-%m-%Y %H:%M:%S')})"


class OrderProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    batch = models.ForeignKey(ProductBatch, on_delete=models.CASCADE)
    numPurchased = models.IntegerField()
    product_price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)  
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("order", "batch")

    @property
    def product(self):
        return self.batch.product

    @property
    def get_total_item_price(self):
        return self.numPurchased * self.price_at_purchase

    def __str__(self):
        return f"{self.batch.batch_number} x{self.numPurchased}"


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