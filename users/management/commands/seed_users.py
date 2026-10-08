# ────────────────────────────────────────────────────────────────────────────
# users/management/commands/seed_users.py
# Наполняет базу демонстрационными ПОЛЬЗОВАТЕЛЯМИ.
#
# Запуск:  python manage.py seed_users
# Идемпотентна: повторный запуск не создаёт дублей (get_or_create по username).
#
# У каждого приложения теперь свой сидер — так данные каждой сущности можно
# заливать по отдельности. Общий сборный сидер (core/seed.py) вызывает их все.
# ────────────────────────────────────────────────────────────────────────────

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# Список демо-гостей: (логин, e-mail, телефон, пароль).
DEMO_USERS = [
    ('guest',  'guest@example.com',  '+7 700 000 00 00', 'guestpass123'),
    ('aizhan', 'aizhan@example.com', '+7 701 111 22 33', 'aizhan2026'),
    ('daniyar', 'daniyar@example.com', '+7 702 222 33 44', 'daniyar2026'),
    ('marat',  'marat@example.com',  '+7 705 333 44 55', 'marat2026'),
]


class Command(BaseCommand):
    help = 'Создаёт демо-пользователей и суперпользователя admin.'

    def handle(self, *args, **options):
        # verbosity=0 (например, из тестов) — работаем молча.
        verbose = options.get('verbosity', 1) >= 1
        def say(msg):
            if verbose:
                self.stdout.write(msg)
        say('Создаю пользователей...')

        # ---- Обычные гости ----
        for username, email, phone, password in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'phone': phone},
            )
            if created:
                # set_password хэширует пароль (в открытом виде не хранится).
                user.set_password(password)
                user.save()
                say(f'  + {username} / {password}')
            else:
                say(f'  · {username} уже существует')

        # ---- Суперпользователь для админки ----
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin12345')
            say('  + admin / admin12345 (суперпользователь)')
        else:
            say('  · admin уже существует')

        say(self.style.SUCCESS(
            f'Готово. Пользователей в базе: {User.objects.count()}'
        ))
