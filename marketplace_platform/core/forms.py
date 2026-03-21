from django import forms
from .models import Product, Recipe, StoryPost

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}))

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "description", "price", "unit", "food_miles", "stock", "allergens", "organic", "surplus", "image"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["title", "description", "instructions", "season", "ingredients", "image"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "instructions": forms.Textarea(attrs={"rows": 5}), "ingredients": forms.CheckboxSelectMultiple()}
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            producer_products = Product.objects.filter(producer=user)
            self.fields["ingredients"].queryset = producer_products if producer_products.exists() else Product.objects.all()
        else:
            self.fields["ingredients"].queryset = Product.objects.all()

class StoryForm(forms.ModelForm):
    class Meta:
        model = StoryPost
        fields = ["content", "image"]
        widgets = {"content": forms.Textarea(attrs={"rows": 5})}
