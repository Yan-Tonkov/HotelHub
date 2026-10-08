# ────────────────────────────────────────────────────────────────────────────
# bookings/management/commands/seed_bookings.py
# Наполняет базу демонстрационными БРОНИРОВАНИЯМИ.
#
# Запуск:  python manage.py seed_bookings
# Зависит от пользователей и номеров: сначала seed_users и seed_rooms
# (или общий seed).
#
# Важное: этот сидер использует СЕРВИСНЫЙ СЛОЙ (bookings.services), а не
# создаёт брони напрямую. Так демо-данные проходят те же бизнес-проверки
# (даты, вместимость, занятость), что и реальные брони из интерфейса.
# ────────────────────────────────────────────────────────────────────────────

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from rooms.models import Room
from bookings.models import Booking
from bookings import services

User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт демонстрационные бронирования для демо-пользователей.'

    def handle(self, *args, **options):
        # verbosity=0 (например, из тестов) — работаем молча.
        verbose = options.get('verbosity', 1) >= 1
        def say(msg):
            if verbose:
                self.stdout.write(msg)
        # Берём демо-гостя (создаётся в seed_users).
        guest = User.objects.filter(username='guest').first()
        rooms = list(Room.objects.all()[:4])

        if guest is None or len(rooms) < 2:
            say(self.style.WARNING(
                'Нужны пользователь guest и хотя бы 2 номера. '
                'Сначала выполните seed_users и seed_rooms.'
            ))
            return

        if Booking.objects.filter(user=guest).exists():
            say('  · У пользователя guest уже есть брони — пропускаю.')
            say(self.style.SUCCESS(
                f'Всего бронирований: {Booking.objects.count()}'
            ))
            return

        say('Создаю бронирования...')
        today = date.today()

        # Заготовки броней: (номер, смещение заезда, число ночей, гостей).
        plan = [
            (rooms[0], 3, 3, 2),    # заезд через 3 дня, на 3 ночи, 2 гостя
            (rooms[1], 14, 2, 1),   # заезд через 2 недели, на 2 ночи, 1 гость
        ]

        for room, start_offset, nights, guests in plan:
            check_in = today + timedelta(days=start_offset)
            check_out = check_in + timedelta(days=nights)
            try:
                # Через сервис — с полной проверкой бизнес-правил.
                # guests ограничиваем вместимостью номера на всякий случай.
                booking = services.create_booking(
                    user=guest, room=room,
                    check_in=check_in, check_out=check_out,
                    guests=min(guests, room.capacity),
                )
                say(
                    f'  + Бронь №{booking.pk}: {room} '
                    f'({check_in}–{check_out}, {booking.nights} ноч.)'
                )
            except ValidationError as exc:
                # Если правило не пройдено — сообщаем, но не падаем.
                say(self.style.WARNING(f'  ! Пропущено: {exc.messages[0]}'))

        say(self.style.SUCCESS(
            f'Готово. Всего бронирований: {Booking.objects.count()}'
        ))
