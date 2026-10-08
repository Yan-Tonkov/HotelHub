from django.apps import AppConfig


class HotelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hotels'
    verbose_name = 'Отели'

    def ready(self):
        # Подключаем сигнал очистки файлов обложки (см. hotels/signals.py).
        from . import signals  # noqa: F401
