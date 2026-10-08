# ────────────────────────────────────────────────────────────────────────────
# core/apps.py — конфигурация приложения core.
# Django создаёт этот класс автоматически. Он подключается в settings.py
# строкой 'core.apps.CoreConfig' в списке INSTALLED_APPS.
# ────────────────────────────────────────────────────────────────────────────

from django.apps import AppConfig            # базовый класс конфигурации любого Django-приложения


class CoreConfig(AppConfig):                  # класс настроек приложения core
    default_auto_field = 'django.db.models.BigAutoField'   # тип поля id по умолчанию для моделей (64-битный счётчик)
    name = 'core'                             # техническое имя приложения (совпадает с именем папки)
    verbose_name = 'Ядро (главная страница)'  # человекочитаемое имя, отображается в админке

    def ready(self):
        """
        ready() вызывается один раз при старте Django, когда все приложения
        загружены. Удобное место для подписки на сигналы.

        Здесь мы чиним известную особенность SQLite: её встроенная функция
        LOWER() приводит к нижнему регистру только латиницу, поэтому поиск
        по кириллице (icontains) работает некорректно — «алматы» не находит
        «Алматы». Мы подменяем LOWER() на Python-версию str.lower(), которая
        понимает Unicode. Это делает регистронезависимый поиск корректным
        для русского и казахского текста во всём проекте.
        """
        from django.db.backends.signals import connection_created
        connection_created.connect(_register_unicode_lower)


def _register_unicode_lower(sender, connection, **kwargs):
    """
    Регистрирует Unicode-совместимую функцию LOWER для нового соединения
    SQLite. Для других СУБД (PostgreSQL и т.п.) ничего не делает — там
    LOWER() и так корректно работает с Unicode.
    """
    if connection.vendor == 'sqlite':
        # create_function(имя, число_аргументов, python_функция)
        connection.connection.create_function('LOWER', 1, _py_lower)


def _py_lower(value):
    """Python-реализация LOWER: понимает кириллицу. None остаётся None."""
    return value.lower() if isinstance(value, str) else value
