from django.db import models


class Actor(models.Model):
    # create models here
    name = models.CharField(max_length=128)
    nationality = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    short_description = models.TextField(max_length=500)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    allergens = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='item_images/')

    def __str__(self):
        return self.name