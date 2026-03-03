from django import forms
from .models import Product


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 
            'category', 
            'description', 
            'price', 
            'unit', 
            'season', 
            'food_miles', 
            'stock', 
            'allergens', 
            'organic', 
            'surplus', 
            'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }