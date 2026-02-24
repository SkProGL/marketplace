from django.db import models


class Actor(models.Model):
    # create models here
    name = models.CharField(max_length=128)
    nationality = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
