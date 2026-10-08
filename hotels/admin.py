from django.contrib import admin
from django.utils.html import format_html
from .models import Hotel


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        'cover_preview',
        'name',
        'city',
        'price',
        'rating',
        'is_active',
    )

    list_filter = (
        'city',
        'is_active',
    )

    search_fields = (
        'name',
        'city',
    )

    def cover_preview(self, obj):
        """Маленькая миниатюра обложки прямо в списке — видно сразу,
        у какого отеля уже есть фото, без открытия карточки."""
        if obj.cover:
            return format_html(
                '<img src="{}" style="width:48px;height:32px;object-fit:cover;'
                'border-radius:4px;">', obj.cover.url,
            )
        return '—'
    cover_preview.short_description = 'Обложка'
