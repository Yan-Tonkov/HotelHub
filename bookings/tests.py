# ────────────────────────────────────────────────────────────────────────────
# bookings/tests.py — тесты приложения бронирований.
#
# Три группы тестов:
#   1. BookingModelTests    — свойства модели (nights, total_price).
#   2. BookingServiceTests  — СЕРВИСНЫЙ СЛОЙ (bookings/services.py): расчёт
#      цены, проверка дат, занятость номера, создание и отмена брони.
#      Это ядро бизнес-логики — тестируем её напрямую, без HTTP.
#   3. BookingViewTests     — тонкие view поверх сервиса (права доступа,
#      сценарий бронирования через веб-клиент).
#
# Запуск только этого приложения:  python manage.py test bookings
# Запуск только сервисных тестов:   python manage.py test bookings.tests.BookingServiceTests
# ────────────────────────────────────────────────────────────────────────────

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from hotels.models import Hotel
from rooms.models import Room
from bookings.models import Booking
from bookings import services

User = get_user_model()


class BookingModelTests(TestCase):
    """Проверяем вычисляемые свойства модели Booking."""

    def setUp(self):
        # setUp выполняется перед КАЖДЫМ тестом — свежие данные каждый раз.
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.hotel = Hotel.objects.create(
            name='Test Hotel', city='Астана', address='ул. Тест, 1', price=30000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='double',
            price_per_night=15000, capacity=2,
        )

    def test_nights_and_total_price(self):
        """nights = разница дат; total_price = цена за ночь × число ночей."""
        booking = Booking.objects.create(
            user=self.user, room=self.room,
            check_in=date(2026, 8, 1), check_out=date(2026, 8, 5), guests=2,
        )
        self.assertEqual(booking.nights, 4)                      # 4 ночи
        self.assertEqual(booking.total_price, Decimal('15000') * 4)  # 60 000

    def test_total_price_never_negative(self):
        """Если выезд раньше заезда — цена не уходит в минус, а равна 0."""
        booking = Booking(
            user=self.user, room=self.room,
            check_in=date(2026, 8, 10), check_out=date(2026, 8, 8), guests=1,
        )
        # nights отрицательный, но total_price подстрахован нулём.
        self.assertEqual(booking.total_price, 0)


class BookingServiceTests(TestCase):
    """
    Тесты СЕРВИСНОГО СЛОЯ — самое важное. Здесь проверяется бизнес-логика
    в отрыве от веба: функции вызываются напрямую с обычными объектами.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.hotel = Hotel.objects.create(
            name='Test Hotel', city='Астана', address='ул. Тест, 1', price=30000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='double',
            price_per_night=Decimal('15000'), capacity=2,
        )
        self.today = date.today()

    # ---- расчёт ночей и цены -------------------------------------------------
    def test_calculate_nights(self):
        """Число ночей между двумя датами."""
        nights = services.calculate_nights(
            self.today, self.today + timedelta(days=3)
        )
        self.assertEqual(nights, 3)

    def test_calculate_nights_zero_for_reversed_dates(self):
        """Перевёрнутые даты дают 0 ночей, а не отрицательное число."""
        nights = services.calculate_nights(
            self.today + timedelta(days=3), self.today
        )
        self.assertEqual(nights, 0)

    def test_calculate_total_price(self):
        """Стоимость = цена за ночь × ночи."""
        total = services.calculate_total_price(
            self.room, self.today, self.today + timedelta(days=2)
        )
        self.assertEqual(total, Decimal('15000') * 2)

    # ---- валидация дат -------------------------------------------------------
    def test_validate_dates_rejects_past_checkin(self):
        """Заезд в прошлом запрещён."""
        with self.assertRaises(ValidationError):
            services.validate_booking_dates(
                self.today - timedelta(days=1), self.today + timedelta(days=1)
            )

    def test_validate_dates_rejects_checkout_before_checkin(self):
        """Выезд не позже заезда — ошибка."""
        with self.assertRaises(ValidationError):
            services.validate_booking_dates(
                self.today + timedelta(days=5), self.today + timedelta(days=2)
            )

    def test_validate_dates_accepts_valid_range(self):
        """Корректный интервал не вызывает исключения."""
        # Если бы было исключение — тест упал бы. Явного assert не требуется.
        services.validate_booking_dates(
            self.today + timedelta(days=1), self.today + timedelta(days=3)
        )

    # ---- проверка занятости номера ------------------------------------------
    def test_room_available_when_no_bookings(self):
        """Свободный номер доступен на любые корректные даты."""
        self.assertTrue(services.is_room_available(
            self.room, self.today + timedelta(days=1), self.today + timedelta(days=3)
        ))

    def test_room_unavailable_on_overlapping_dates(self):
        """Пересекающиеся по датам брони делают номер занятым."""
        services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=2), self.today + timedelta(days=6), guests=1,
        )
        # Новый интервал (3–5) целиком внутри уже занятого (2–6) — пересечение.
        self.assertFalse(services.is_room_available(
            self.room, self.today + timedelta(days=3), self.today + timedelta(days=5)
        ))

    def test_cancelled_booking_frees_the_room(self):
        """Отменённая бронь не блокирует номер на те же даты."""
        booking = services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=2), self.today + timedelta(days=6), guests=1,
        )
        services.cancel_booking(booking)
        # После отмены те же даты снова свободны.
        self.assertTrue(services.is_room_available(
            self.room, self.today + timedelta(days=2), self.today + timedelta(days=6)
        ))

    # ---- создание брони ------------------------------------------------------
    def test_create_booking_success(self):
        """Успешное бронирование создаёт запись со статусом pending."""
        booking = services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=1), self.today + timedelta(days=4), guests=2,
        )
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.nights, 3)

    def test_create_booking_rejects_too_many_guests(self):
        """Гостей больше вместимости номера — бронь не создаётся."""
        with self.assertRaises(ValidationError):
            services.create_booking(
                self.user, self.room,
                self.today + timedelta(days=1), self.today + timedelta(days=2),
                guests=5,  # вместимость номера всего 2
            )
        self.assertEqual(Booking.objects.count(), 0)

    def test_create_booking_rejects_double_booking(self):
        """Нельзя забронировать уже занятый на эти даты номер."""
        services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=2), self.today + timedelta(days=5), guests=1,
        )
        with self.assertRaises(ValidationError):
            # Другой пользователь пытается занять пересекающийся интервал.
            services.create_booking(
                self.other, self.room,
                self.today + timedelta(days=3), self.today + timedelta(days=4), guests=1,
            )
        self.assertEqual(Booking.objects.count(), 1)

    # ---- отмена брони --------------------------------------------------------
    def test_cancel_booking_sets_status(self):
        """Отмена меняет статус на cancelled, запись остаётся в базе."""
        booking = services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=1), self.today + timedelta(days=2), guests=1,
        )
        services.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(Booking.objects.count(), 1)  # не удалена, история сохранена

    def test_cancel_already_cancelled_raises(self):
        """Повторная отмена уже отменённой брони — ошибка."""
        booking = services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=1), self.today + timedelta(days=2), guests=1,
        )
        services.cancel_booking(booking)
        with self.assertRaises(ValidationError):
            services.cancel_booking(booking)


class BookingViewTests(TestCase):
    """Тонкие view: проверяем права доступа и веб-сценарий бронирования."""

    def setUp(self):
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.hotel = Hotel.objects.create(
            name='Test Hotel', city='Астана', address='ул. Тест, 1', price=30000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='double',
            price_per_night=15000, capacity=2,
        )
        self.today = date.today()

    def test_booking_requires_login(self):
        """Гость не может открыть форму брони — редирект (302) на вход."""
        resp = self.client.get(reverse('bookings:create', args=[self.room.id]))
        self.assertEqual(resp.status_code, 302)

    def test_successful_booking_via_view(self):
        """Авторизованный пользователь бронирует номер через POST-запрос."""
        self.client.login(username='guest', password='pass12345')
        resp = self.client.post(reverse('bookings:create', args=[self.room.id]), {
            'room': self.room.id,
            'check_in': (self.today + timedelta(days=2)).isoformat(),
            'check_out': (self.today + timedelta(days=5)).isoformat(),
            'guests': 2,
        })
        # После успеха — редирект в список броней.
        self.assertRedirects(resp, reverse('bookings:list'))
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)

    def test_invalid_dates_rejected_by_form(self):
        """Выезд раньше заезда — форма показывает ошибку, брони нет."""
        self.client.login(username='guest', password='pass12345')
        resp = self.client.post(reverse('bookings:create', args=[self.room.id]), {
            'room': self.room.id,
            'check_in': (self.today + timedelta(days=10)).isoformat(),
            'check_out': (self.today + timedelta(days=5)).isoformat(),
            'guests': 1,
        })
        self.assertContains(resp, 'должна быть позже')
        self.assertEqual(Booking.objects.count(), 0)

    def test_user_can_cancel_only_own_booking(self):
        """Отменить чужую бронь нельзя — get_object_or_404 вернёт 404."""
        other = User.objects.create_user(username='other', password='pass12345')
        booking = services.create_booking(
            other, self.room,
            self.today + timedelta(days=1), self.today + timedelta(days=2), guests=1,
        )
        self.client.login(username='guest', password='pass12345')
        # Отмена — действие, изменяющее состояние, поэтому только POST
        # (аудит, дефект №1; см. также test_cancel_via_get_is_not_allowed).
        resp = self.client.post(reverse('bookings:cancel', args=[booking.pk]))
        self.assertEqual(resp.status_code, 404)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'pending')  # статус не изменился

    def test_cancel_via_get_is_not_allowed(self):
        """
        Регрессионный тест на дефект №1 из аудита: раньше GET-запрос
        (например, обычная ссылка или <img src=...> на стороннем сайте)
        отменял бронь. Теперь GET должен вернуть 405, а бронь остаться
        нетронутой.
        """
        self.client.login(username='guest', password='pass12345')
        booking = services.create_booking(
            self.user, self.room,
            self.today + timedelta(days=1), self.today + timedelta(days=2), guests=1,
        )
        resp = self.client.get(reverse('bookings:cancel', args=[booking.pk]))
        self.assertEqual(resp.status_code, 405)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'pending')


class SeedBookingsCommandTests(TestCase):
    """Тесты сидера seed_bookings (Занятие 3: скрипты-наполнители)."""

    def test_seed_bookings_skips_gracefully_without_dependencies(self):
        """Без пользователей/номеров сидер не падает, а вежливо выходит."""
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('seed_bookings', stdout=out, verbosity=1)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertIn('Сначала выполните', out.getvalue())

    def test_seed_bookings_creates_bookings_via_service(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_users', stdout=StringIO(), verbosity=0)
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        call_command('seed_bookings', stdout=StringIO(), verbosity=0)
        self.assertGreater(Booking.objects.count(), 0)
        # Брони созданы сервисным слоем — статус выставлен по бизнес-правилам.
        self.assertTrue(Booking.objects.filter(status='pending').exists())

    def test_seed_bookings_is_idempotent(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_users', stdout=StringIO(), verbosity=0)
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        call_command('seed_bookings', stdout=StringIO(), verbosity=0)
        count_first = Booking.objects.count()
        call_command('seed_bookings', stdout=StringIO(), verbosity=0)
        self.assertEqual(Booking.objects.count(), count_first)
