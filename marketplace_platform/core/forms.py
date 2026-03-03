from django import forms
<<<<<<< HEAD
from .models import Product


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
=======
from .models import Item


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class ProductForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'short_description', 'price', 'allergens', 'image']
>>>>>>> f64f6c7 (add inventory mvp)
