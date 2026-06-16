from django.db import models


class Hotel(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)
    # цена за одну ночь проживания, например 999.99
    price = models.DecimalField(max_digits=10, decimal_places=2)

    rating = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отель'
        verbose_name_plural = 'Отели'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
