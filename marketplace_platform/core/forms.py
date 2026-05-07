from datetime import timedelta, date
from django.utils import timezone
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import Complaint, Product, ProductBatch, User, Review, Recipe, StoryPost

PASSWORD_STRENGTH_ERROR = "Password must be at least 8 characters and include 1 lowercase and 1 uppercase letter."

class SignupForm(forms.ModelForm):
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'})
    )
    organization_name = forms.CharField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
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
class ProfileEditForm(forms.ModelForm):
    # Fields shown per category — all are optional, purely display/contact info
    CATEGORY_FIELDS = {
        'Customer':        ['full_name', 'phone', 'address', 'postcode', 'profile_image'],
        'Producer':        ['full_name', 'phone', 'address', 'postcode', 'organisation_name', 'organic_description', 'profile_image'],
        'Restaurant':      ['full_name', 'phone', 'address', 'postcode', 'organisation_name', 'profile_image'],
        'Community group': ['full_name', 'phone', 'address', 'postcode', 'organisation_name', 'charity_status', 'profile_image'],
    }

    class Meta:
        model = User
        fields = [
            "full_name", "phone", "address", "postcode",
            "organisation_name", "organic_description", "charity_status", "profile_image",
        ]
        widgets = {
            "full_name":           forms.TextInput(attrs={"class": "form-control"}),
            "phone":               forms.TextInput(attrs={"class": "form-control"}),
            "address":             forms.TextInput(attrs={"class": "form-control"}),
            "postcode":            forms.TextInput(attrs={"class": "form-control"}),
            "organisation_name":   forms.TextInput(attrs={"class": "form-control"}),
            "organic_description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "charity_status":      forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Registered charity, Educational institution…"}),
            "profile_image":       forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        category = kwargs.pop('category', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        allowed = self.CATEGORY_FIELDS.get(category)
        if allowed:
            for field in list(self.fields):
                if field not in allowed:
                    del self.fields[field]
        org_labels = {
            'Producer':        'Farm / Producer name',
            'Restaurant':      'Restaurant name',
            'Community group': 'Organisation name',
        }
        if 'organisation_name' in self.fields and category in org_labels:
            self.fields['organisation_name'].label = org_labels[category]

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


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'instructions', 'season', 'image', 'storage_guidance']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipe title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Step-by-step cooking instructions'}),
            'season': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'storage_guidance': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g. Store carrots in a cool dark place for up to 2 weeks…'}),
        }


class StoryPostForm(forms.ModelForm):
    class Meta:
        model = StoryPost
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Share your farm story, harvest update, or news…'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['name', 'email', 'category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Please describe your complaint in detail…'}),
        }
