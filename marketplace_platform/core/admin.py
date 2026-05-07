from django.apps import apps
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from .models import (
    User, Product, Order, OrderProduct, StoryPost, 
    Recipe, RecipeIngredients, Review, Payment,
    OrderStatusHistory
)
# Register all models
app_models = apps.get_app_config('core').get_models()

# for model in app_models:
#     try:
#         admin.site.register(model)
#     except Exception as e:
#         print("Error registering:", e)
#         pass

# @admin.register(User)
# class CustomUserAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, UserAdmin):
#     """
#     Combines default User management with Import/Export and History tracking.
#     """
#     list_display = ('email', 'full_name', 'category', 'is_staff', 'is_active')
#     list_filter = ('category', 'is_staff', 'is_superuser', 'is_active')
#     search_fields = ('email', 'full_name', 'organisation_name')
#     ordering = ('email',)


# @admin.register(Product)
# class ProductAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
#     list_display = ('name', 'producer', 'category', 'price', 'stock', 'all_year')
#     # history__history_date adds the built-in time slider to the filter sidebar!
#     list_filter = ('category', 'organic', 'surplus', 'all_year', 'history__history_date')
#     search_fields = ('name', 'producer__email', 'description')
#     readonly_fields = ('id',)


# # Inline to show items directly inside the Order admin page
# class OrderProductInline(admin.TabularInline):
#     model = OrderProduct
#     extra = 0
#     readonly_fields = ('product_at_purchase', 'id')

# @admin.register(Order)
# class OrderAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
#     list_display = ('id', 'customer', 'order_status', 'total_price', 'delivery_date')
#     list_filter = ('order_status', 'paused', 'recurrence_type', 'history__history_date')
#     search_fields = ('id', 'customer__email')
#     readonly_fields = ('id', 'order_date')
#     inlines = [OrderProductInline]


# @admin.register(OrderProduct)
# class OrderProductAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
#     list_display = ('id', 'order', 'product', 'numPurchased', 'product_at_purchase')
#     search_fields = ('order__id', 'product__name')


# @admin.register(Payment)
# class PaymentAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
#     list_display = ('id', 'producer', 'amount', 'status', 'created_at')
#     list_filter = ('status', 'created_at', 'history__history_date')
#     search_fields = ('producer__email', 'id')


# @admin.register(OrderPayment)
# class OrderPaymentAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
#     list_display = ('id', 'order', 'payment', 'date_posted')
#     search_fields = ('order__id', 'payment__id')


# # ==========================================
# # 2. STANDARD MODELS (Export Only, No History Bloat)
# # ==========================================

# @admin.register(StoryPost)
# class StoryPostAdmin(ImportExportModelAdmin):
#     list_display = ('user', 'date_posted')
#     search_fields = ('user__email', 'content')
#     list_filter = ('date_posted',)


# # Inline to show ingredients directly inside the Recipe admin page
# class RecipeIngredientsInline(admin.TabularInline):
#     model = RecipeIngredients
#     extra = 1

# @admin.register(Recipe)
# class RecipeAdmin(ImportExportModelAdmin):
#     list_display = ('title', 'user', 'season')
#     list_filter = ('season',)
#     search_fields = ('title', 'user__email')
#     inlines = [RecipeIngredientsInline]


# @admin.register(RecipeIngredients)
# class RecipeIngredientsAdmin(ImportExportModelAdmin):
#     list_display = ('recipe', 'product', 'quantity')
#     search_fields = ('recipe__title', 'product__name')


# @admin.register(Review)
# class ReviewAdmin(ImportExportModelAdmin):
#     list_display = ('title', 'user', 'product', 'rating', 'date_posted', 'anonymous')
#     list_filter = ('rating', 'anonymous', 'date_posted')
#     search_fields = ('title', 'user__email', 'product__name')


# @admin.register(OrderStatusHistory)
# class OrderStatusHistoryAdmin(ImportExportModelAdmin):
#     list_display = ('order', 'from_status', 'to_status', 'changed_by', 'changed_at')
#     list_filter = ('changed_at', 'from_status', 'to_status')
#     search_fields = ('order__id', 'changed_by__email')
#     readonly_fields = ('changed_at',)