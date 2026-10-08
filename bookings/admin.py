from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Управление бронированиями из админки."""
    list_display = ('id', 'user', 'room', 'check_in', 'check_out', 'status', 'created_at')
    list_filter = ('status', 'check_in', 'created_at')
    search_fields = ('user__username', 'room__number', 'room__hotel__name')
    date_hierarchy = 'check_in'
