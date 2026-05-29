from django.db import models

# Create your models here.

from django.db import models

class Hotel(models.Model):

    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)
    # цена за одну ночь проживания
    price = models.DecimalField(max_digits=10, decimal_places=2) #999.99


    rating = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name