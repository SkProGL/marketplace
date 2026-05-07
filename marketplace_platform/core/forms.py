from datetime import timedelta, date
from django.utils import timezone

from django import forms
from .models import Product, ProductBatch, User, Review

PASSWORD_STRENGTH_ERROR = "Password must be at least 8 characters and include 1 lowercase and 1 uppercase letter."

class SignupForm(forms.ModelForm):
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'})
    )
    organization_name = forms.CharField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    remember_me = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    accept_policy = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must accept the policy.'},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "phone",
            "address",
            "postcode",
            "category",
        ]

    @staticmethod
    def validate_password(password):
        if password and not (len(password) >= 8 and any(c.islower() for c in password) and any(c.isupper() for c in password)):
            return False
        else:
            return True

    def clean(self):
        signup_data = super().clean()
        email = signup_data.get("email")
        category = signup_data.get("category")
        password = signup_data.get("password", "")

        if email and category and User.objects.filter(email__iexact=email, category=category).exists():
            self.add_error(
                "email",
                # do not tell that category exists (prevents users from scraping accounts)
                # "An account with this email already exists for this category."
                "An account with this email already exists."
            )

        
        if not self.validate_password(password):
            self.add_error(
                "password",
                PASSWORD_STRENGTH_ERROR
            )

        return signup_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data.get("full_name", "").strip()
        user.email = self.cleaned_data.get("email", "").strip().lower()
        organization_name = self.cleaned_data.get("organization_name", "").strip()
        user.organisation_name = organization_name
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    remember_me = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
class CheckoutForm(forms.Form):

    delivery_address = forms.CharField(
        max_length=256,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'})
    )
    delivery_postcode = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SW1A 1AA'})
    )
    delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if delivery_date and delivery_date < date.today() + timedelta(days=2):
            raise forms.ValidationError("Delivery must be at least 48 hours from now.")
        return delivery_date
    
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price',
            'unit', 'all_year', 'seasonStart', 'seasonEnd',
            'stock_alert_threshold',
            'allergens', 'organic', 'surplus', 'discount_percentage',
            'discount_expiry', 'discount_note', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "content", "anonymous"]
        widgets = {
            "rating": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Review title"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Share your experience with this product..."}),
            "anonymous": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {"anonymous": "Post anonymously"}


class ProductBatchForm(forms.ModelForm):
    class Meta:
        model = ProductBatch
        fields = [
            'quality_class', 'stock', 'stock_alert_threshold', 'image',
            'best_before', 'surplus', 'discount_percentage',
            'discount_expiry', 'discount_note',
            'seasonStart', 'seasonEnd',
        ]
