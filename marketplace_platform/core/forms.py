from django import forms

from .models import Product, User


class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
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
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        category = cleaned_data.get("category")

        if email and category and User.objects.filter(email__iexact=email, category=category).exists():
            self.add_error(
                "email",
                "An account with this email already exists for this category."
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if User.objects.filter(username__iexact=user.username).exists():
            base_username = user.email.split("@")[0]
            username = base_username
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f"{base_username}{suffix}"
                suffix += 1
            user.username = username
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


