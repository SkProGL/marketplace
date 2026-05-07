from django.urls import path
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    # General/Account URLs
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('terms/', views.terms_view, name='terms'),
    path('review/<uuid:product_id>/', views.add_review, name='add_review'),
    path('community/', views.community, name='community'),
    path('inventory_upload/', views.upload_item, name='inventory_upload'),
    # Order URLs
    path('orders/', views.orders, name='orders'),
    path('orders/<uuid:order_id>/reorder/', views.reorder, name='reorder'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('add_batch/', views.add_batch, name='add_batch'),
    path('invoice/<str:order_code>/', views.invoice_view, name='invoice'),
    # Recurring order URLs
    path('orders/recurring/', views.recurring_orders, name='recurring_orders'),
    path('orders/recurring/<uuid:order_id>/modify/', views.modify_recurring_order, name='modify_recurring_order'),
    path('orders/recurring/<uuid:order_id>/pause/', views.pause_recurring_order, name='pause_recurring_order'),
    path('orders/recurring/<uuid:order_id>/delete/', views.delete_recurring_order, name='delete_recurring_order'),
    # Checkout URLs
    path('add-to-cart/<uuid:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/contents/', views.cart_contents, name='cart_contents'),
    path('cart/update/<uuid:product_id>/', views.update_cart_ajax, name='update_cart_ajax'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='password_reset_email.txt',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html',
    ), name='password_reset_complete'),
    # Management URLs
    path('management/', views.management_view, name="management"),
    path('management/order/<uuid:order_id>/order_summary/', views.get_order_summary_json, name='order_summary'),
    path('management/search/', views.management_search, name='management_search'),
    path('management/order/<uuid:order_id>/advance/', views.advance_order_status, name='advance_order_status'),
] 
