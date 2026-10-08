# ────────────────────────────────────────────────────────────────────────────
# hotels/signals.py — очистка файлов обложки при удалении отеля.
#
# Занятие 2: если просто удалить объект Hotel, сама картинка останется
# лежать в media/hotels/covers/... («файл-сирота») — Django никогда не
# удаляет файлы автоматически, только запись в БД. Подписываемся на
# post_delete и вручную удаляем файл с диска.
# ────────────────────────────────────────────────────────────────────────────
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Hotel


@receiver(post_delete, sender=Hotel)
def delete_cover_file_on_hotel_delete(sender, instance, **kwargs):
    """При удалении отеля удаляем его файл обложки, если он был."""
    if instance.cover:
        instance.cover.delete(save=False)
