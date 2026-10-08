# ────────────────────────────────────────────────────────────────────────────
# rooms/signals.py — очистка файла фото при удалении номера (см. hotels/signals.py).
# ────────────────────────────────────────────────────────────────────────────
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Room


@receiver(post_delete, sender=Room)
def delete_image_file_on_room_delete(sender, instance, **kwargs):
    """При удалении номера удаляем его файл фото, если он был."""
    if instance.image:
        instance.image.delete(save=False)
