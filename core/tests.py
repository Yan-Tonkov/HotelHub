# ────────────────────────────────────────────────────────────────────────────
# core/tests.py — тесты «объединяющего» приложения core.
#
# core не хранит своих данных, а собирает главную страницу из hotels и rooms.
# Поэтому тесты проверяют: страница открывается, показывает топ-отели и
# свободные номера, а блок статистики считает корректно.
#
# Отдельный блок — тест общего сидера seed (management-команды).
#
# Запуск:  python manage.py test core
# ────────────────────────────────────────────────────────────────────────────

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from hotels.models import Hotel
from rooms.models import Room
from bookings.models import Booking

User = get_user_model()


class HomePageTests(TestCase):
    """Тесты главной страницы (витрины)."""

    def setUp(self):
        # Два отеля с разным рейтингом и по номеру в каждом.
        self.h1 = Hotel.objects.create(name='Grand Astana', city='Астана',
                                       address='а', price=45000, rating=4.9)
        self.h2 = Hotel.objects.create(name='Almaty Plaza', city='Алматы',
                                       address='б', price=38000, rating=4.5)
        Room.objects.create(hotel=self.h1, number='101',
                           room_type='double', price_per_night=15000, is_available=True)
        Room.objects.create(hotel=self.h2, number='201',
                           room_type='single', price_per_night=12000, is_available=True)

    def test_home_page_ok(self):
        """Главная открывается со статусом 200 и нужным шаблоном."""
        resp = self.client.get(reverse('core:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'core/home.html')

    def test_home_shows_hotels(self):
        """На витрине видны названия отелей."""
        resp = self.client.get(reverse('core:home'))
        self.assertContains(resp, 'Grand Astana')

    def test_stats_counts(self):
        """Блок статистики считает отели, номера и уникальные города."""
        resp = self.client.get(reverse('core:home'))
        stats = resp.context['stats']
        self.assertEqual(stats['hotels'], 2)   # два активных отеля
        self.assertEqual(stats['rooms'], 2)    # два свободных номера
        self.assertEqual(stats['cities'], 2)   # два разных города


class SeedCommandTests(TestCase):
    """Тесты общего сидера seed (оркестратора per-app команд)."""

    def test_seed_populates_all_entities(self):
        """Команда seed наполняет все сущности связанными данными."""
        out = StringIO()
        # call_command запускает management-команду внутри теста.
        call_command('seed', stdout=out, verbosity=0)

        # После сидирования в базе есть пользователи, отели, номера и брони.
        self.assertTrue(User.objects.filter(username='guest').exists())
        self.assertTrue(User.objects.filter(username='admin').exists())
        self.assertGreater(Hotel.objects.count(), 0)
        self.assertGreater(Room.objects.count(), 0)
        self.assertGreater(Booking.objects.count(), 0)

    def test_seed_is_idempotent(self):
        """Повторный запуск seed не создаёт дубликатов."""
        call_command('seed', stdout=StringIO(), verbosity=0)
        hotels_after_first = Hotel.objects.count()
        rooms_after_first = Room.objects.count()

        call_command('seed', stdout=StringIO(), verbosity=0)  # второй запуск
        # Количество не изменилось — get_or_create защитил от дублей.
        self.assertEqual(Hotel.objects.count(), hotels_after_first)
        self.assertEqual(Room.objects.count(), rooms_after_first)

    def test_seed_flush_recreates(self):
        """seed --flush очищает демо-данные и создаёт их заново."""
        call_command('seed', stdout=StringIO(), verbosity=0)
        call_command('seed', '--flush', stdout=StringIO(), verbosity=0)
        # После flush + пересоздания данные снова на месте.
        self.assertGreater(Hotel.objects.count(), 0)
        self.assertTrue(User.objects.filter(username='admin').exists())
