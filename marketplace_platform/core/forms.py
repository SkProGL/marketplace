from django import forms

from .models import Product, User


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

        if password and not (len(password) >= 8 and any(c.islower() for c in password) and any(c.isupper() for c in password)):
            self.add_error(
                "password",
                "Password must be at least 8 characters and include 1 lowercase and 1 uppercase letter."
            )

        return signup_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data.get("full_name", "").strip()
        user.username = user.full_name or user.email
        if User.objects.filter(username__iexact=user.username).exists():
            base_name = user.full_name or user.email.split("@")[0]
            username = base_name
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f"{base_name}{suffix}"
                suffix += 1
            user.username = username
        organization_name = self.cleaned_data.get("organization_name", "").strip()
        user.organisation_name = organization_name
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price',
            'unit', 'availability', 'seasonStart', 'seasonEnd',
            'best_before', 'food_miles', 'stock', 'stock_alert_threshold',
            'allergens', 'organic', 'surplus', 'discount_percentage',
            'discount_expiry', 'discount_note', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


