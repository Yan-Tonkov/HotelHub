from django.contrib import admin
from django.utils.html import format_html
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'image_preview',
        'number',
        'hotel',
        'room_type',
        'price_per_night',
        'capacity',
        'is_available',
    )

    list_filter = (
        'room_type',
        'is_available',
        'hotel',
    )

    search_fields = (
        'number',
        'hotel__name',
    )

    def image_preview(self, obj):
        """Миниатюра фото номера в списке админки."""
        if obj.image:
            return format_html(
                '<img src="{}" style="width:48px;height:32px;object-fit:cover;'
                'border-radius:4px;">', obj.image.url,
            )
        return '—'
    image_preview.short_description = 'Фото'
