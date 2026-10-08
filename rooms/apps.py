from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rooms'
    verbose_name = 'Номера'

    def ready(self):
        # Подключаем сигнал очистки файла фото (см. rooms/signals.py).
        from . import signals  # noqa: F401
