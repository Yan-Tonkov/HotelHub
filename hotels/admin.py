from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Hotel

admin.site.register(Hotel)

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display  = ('name', 'city', 'price', 'rating', 'is_active')
    list_filter = ('city', 'is_active')
    search_fields = ('name', 'city')
