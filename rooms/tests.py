# ────────────────────────────────────────────────────────────────────────────
# rooms/tests.py — тесты приложения номеров.
#
# Проверяем: строковое представление, ограничение уникальности номера в
# пределах отеля, поиск по названию отеля и по типу номера, страницу номера.
#
# Запуск:  python manage.py test rooms
# ────────────────────────────────────────────────────────────────────────────

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from hotels.models import Hotel
from rooms.models import Room
from rooms.forms import RoomSearchForm

User = get_user_model()


class RoomModelTests(TestCase):
    """Тесты модели Room."""

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='ул. Тест, 1', price=45000,
        )

    def test_str_representation(self):
        """__str__ показывает отель и номер комнаты."""
        room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='single', price_per_night=12000,
        )
        self.assertEqual(str(room), 'Grand Astana — номер 101')

    def test_unique_number_per_hotel(self):
        """Нельзя создать два номера с одинаковым числом в одном отеле."""
        Room.objects.create(
            hotel=self.hotel, number='101', room_type='single', price_per_night=12000,
        )
        # Второй '101' в том же отеле нарушает UniqueConstraint.
        with self.assertRaises(IntegrityError):
            Room.objects.create(
                hotel=self.hotel, number='101', room_type='double', price_per_night=18000,
            )

    def test_same_number_different_hotels_allowed(self):
        """Одинаковый номер в РАЗНЫХ отелях разрешён."""
        other_hotel = Hotel.objects.create(
            name='Almaty Plaza', city='Алматы', address='ул. Достык, 85', price=38000,
        )
        Room.objects.create(hotel=self.hotel, number='101',
                           room_type='single', price_per_night=12000)
        # Тот же '101', но другой отель — конфликта нет.
        Room.objects.create(hotel=other_hotel, number='101',
                           room_type='single', price_per_night=12000)
        self.assertEqual(Room.objects.filter(number='101').count(), 2)


class RoomListViewTests(TestCase):
    """Тесты списка номеров и поиска."""

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='ул. Тест, 1', price=45000,
        )
        self.other = Hotel.objects.create(
            name='Almaty Plaza', city='Алматы', address='ул. Достык, 85', price=38000,
        )
        Room.objects.create(hotel=self.hotel, number='101',
                           room_type='suite', price_per_night=32000, capacity=2)
        Room.objects.create(hotel=self.other, number='201',
                           room_type='single', price_per_night=12000, capacity=1)

    def test_list_ok(self):
        """Список номеров открывается со статусом 200."""
        resp = self.client.get(reverse('rooms:room_list'))
        self.assertEqual(resp.status_code, 200)

    def test_search_by_hotel_name(self):
        """Поиск ?q=Almaty находит номера отеля Almaty Plaza."""
        resp = self.client.get(reverse('rooms:room_list'), {'q': 'Almaty'})
        self.assertContains(resp, '201')
        self.assertNotContains(resp, '№ 101')

    def test_search_by_room_type_label(self):
        """Поиск ?q=люкс находит номера типа suite (по человекочит. названию)."""
        resp = self.client.get(reverse('rooms:room_list'), {'q': 'люкс'})
        # Отель, где есть suite-номер, должен присутствовать.
        self.assertContains(resp, 'Grand Astana')

    def test_unavailable_room_hidden(self):
        """Занятые номера (is_available=False) не показываются в списке."""
        Room.objects.create(hotel=self.hotel, number='999',
                           room_type='single', price_per_night=12000,
                           is_available=False)
        resp = self.client.get(reverse('rooms:room_list'))
        self.assertNotContains(resp, '999')


class RoomDetailViewTests(TestCase):
    """Тесты страницы одного номера."""

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='ул. Тест, 1', price=45000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='double', price_per_night=15000,
        )

    def test_detail_ok(self):
        """Страница номера открывается и содержит его данные."""
        resp = self.client.get(reverse('rooms:room_detail', args=[self.room.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '101')

    def test_missing_room_404(self):
        """Несуществующий номер — 404."""
        resp = self.client.get(reverse('rooms:room_detail', args=[9999]))
        self.assertEqual(resp.status_code, 404)


class RoomSearchFormTests(TestCase):
    """
    Занятие 1 «Данные и выборки»: форма поиска по датам.

    Регрессионный тест на ошибку отступа в исходном примере — там
    `return cleaned_data` был вложен внутрь `if`, и при КОРРЕКТНЫХ датах
    clean() возвращал бы None вместо словаря, что ломает любую форму.
    """

    def test_valid_dates_pass_validation(self):
        form = RoomSearchForm(data={
            'check_in': '2026-10-10', 'check_out': '2026-10-15', 'sort_by': 'price',
        })
        self.assertTrue(form.is_valid())
        # Если бы clean() возвращал None, cleaned_data было бы пустым/отсутствовало.
        self.assertEqual(form.cleaned_data.get('check_in'), date(2026, 10, 10))

    def test_checkout_before_checkin_is_rejected(self):
        form = RoomSearchForm(data={'check_in': '2026-10-15', 'check_out': '2026-10-10'})
        self.assertFalse(form.is_valid())
        self.assertIn('позже даты заезда', form.errors['__all__'][0])

    def test_empty_dates_are_allowed(self):
        """Форма валидна и без дат — обычный список без фильтра по датам."""
        form = RoomSearchForm(data={})
        self.assertTrue(form.is_valid())


class RoomAvailabilitySearchTests(TestCase):
    """
    Занятие 1: Room.objects.free_between() — номер с пересекающейся
    АКТИВНОЙ бронью скрыт, а с ОТМЕНЁННОЙ — по-прежнему виден.
    """

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='а', price=45000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='single', price_per_night=10000,
        )
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.today = date.today()

    def test_room_hidden_when_booked_for_requested_dates(self):
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='confirmed',
            check_in=self.today + timedelta(days=5),
            check_out=self.today + timedelta(days=8),
        )
        free = Room.objects.filter(is_available=True).free_between(
            self.today + timedelta(days=6), self.today + timedelta(days=7),
        )
        self.assertNotIn(self.room, free)

    def test_cancelled_booking_does_not_block_room(self):
        """
        Ключевой фикс относительно исходного примера занятия: отменённая
        бронь не должна считаться «занятостью» номера.
        """
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='cancelled',
            check_in=self.today + timedelta(days=5),
            check_out=self.today + timedelta(days=8),
        )
        free = Room.objects.filter(is_available=True).free_between(
            self.today + timedelta(days=6), self.today + timedelta(days=7),
        )
        self.assertIn(self.room, free)

    def test_room_visible_when_dates_do_not_overlap(self):
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='confirmed',
            check_in=self.today + timedelta(days=5),
            check_out=self.today + timedelta(days=8),
        )
        free = Room.objects.filter(is_available=True).free_between(
            self.today + timedelta(days=20), self.today + timedelta(days=22),
        )
        self.assertIn(self.room, free)


class RoomTodayStatusTests(TestCase):
    """
    Аудит, дефект №4: бейдж «Свободен/Занят» должен отражать реальные
    брони на сегодня, а не статичный флаг is_available.
    RoomQuerySet.with_today_status() аннотирует occupied_today.
    """

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='а', price=45000,
        )
        self.room = Room.objects.create(
            hotel=self.hotel, number='101', room_type='single', price_per_night=10000,
        )
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.today = date.today()

    def test_room_not_occupied_without_bookings(self):
        rooms = Room.objects.with_today_status()
        self.assertFalse(rooms.get(pk=self.room.pk).occupied_today)

    def test_room_occupied_when_active_booking_covers_today(self):
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='confirmed',
            check_in=self.today - timedelta(days=1),
            check_out=self.today + timedelta(days=2),
        )
        rooms = Room.objects.with_today_status()
        self.assertTrue(rooms.get(pk=self.room.pk).occupied_today)

    def test_room_not_occupied_when_booking_is_in_the_future(self):
        """
        Ключевой случай из дефекта №4: бронь на ЗАВТРА не должна делать
        номер «занятым сегодня» — но и не должна больше бессрочно
        показывать его «Свободен» для всех дат (это чинит free_between()).
        """
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='confirmed',
            check_in=self.today + timedelta(days=1),
            check_out=self.today + timedelta(days=3),
        )
        rooms = Room.objects.with_today_status()
        self.assertFalse(rooms.get(pk=self.room.pk).occupied_today)

    def test_cancelled_booking_does_not_count_as_occupied(self):
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.room, status='cancelled',
            check_in=self.today, check_out=self.today + timedelta(days=2),
        )
        rooms = Room.objects.with_today_status()
        self.assertFalse(rooms.get(pk=self.room.pk).occupied_today)

    def test_room_list_badge_shows_occupied_today(self):
        """Карточка в /rooms/ показывает «Занят сегодня» для забронированного
        на сегодня номера, и «Свободен» для второго, свободного."""
        from bookings.models import Booking
        free_room = Room.objects.create(
            hotel=self.hotel, number='102', room_type='single', price_per_night=12000,
        )
        Booking.objects.create(
            user=self.user, room=self.room, status='confirmed',
            check_in=self.today, check_out=self.today + timedelta(days=1),
        )
        resp = self.client.get(reverse('rooms:room_list'))
        self.assertContains(resp, 'Занят сегодня')
        self.assertContains(resp, 'Свободен')

    def test_room_detail_page_has_annotation(self):
        resp = self.client.get(reverse('rooms:room_detail', args=[self.room.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['room'].occupied_today)


class RoomListDatesAndSortTests(TestCase):
    """Занятие 1: интеграция формы поиска по датам и сортировки в RoomListView."""

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='а', price=45000,
        )
        self.cheap = Room.objects.create(
            hotel=self.hotel, number='101', room_type='single', price_per_night=10000,
        )
        self.expensive = Room.objects.create(
            hotel=self.hotel, number='201', room_type='suite', price_per_night=50000,
        )
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.today = date.today()

    def test_default_sort_is_cheapest_first(self):
        resp = self.client.get(reverse('rooms:room_list'))
        rooms = list(resp.context['rooms'])
        self.assertEqual(rooms[0], self.cheap)

    def test_sort_by_price_descending(self):
        resp = self.client.get(reverse('rooms:room_list'), {'sort_by': '-price'})
        rooms = list(resp.context['rooms'])
        self.assertEqual(rooms[0], self.expensive)

    def test_booked_room_excluded_from_date_search(self):
        from bookings.models import Booking
        Booking.objects.create(
            user=self.user, room=self.cheap, status='confirmed',
            check_in=self.today + timedelta(days=5),
            check_out=self.today + timedelta(days=8),
        )
        resp = self.client.get(reverse('rooms:room_list'), {
            'check_in': (self.today + timedelta(days=6)).isoformat(),
            'check_out': (self.today + timedelta(days=7)).isoformat(),
        })
        rooms = list(resp.context['rooms'])
        self.assertNotIn(self.cheap, rooms)
        self.assertIn(self.expensive, rooms)

    def test_invalid_date_range_falls_back_to_unfiltered_list(self):
        """
        Некорректные даты (выезд раньше заезда) не должны положить страницу
        500-й ошибкой — просто игнорируются формой, список остаётся полным.
        """
        resp = self.client.get(reverse('rooms:room_list'), {
            'check_in': (self.today + timedelta(days=10)).isoformat(),
            'check_out': (self.today + timedelta(days=5)).isoformat(),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'позже даты заезда')


class RoomListPaginationTests(TestCase):
    """Занятие 1: пагинация по 6 номеров на страницу."""

    def setUp(self):
        hotel = Hotel.objects.create(name='Grand Astana', city='Астана', address='а', price=45000)
        for i in range(8):
            Room.objects.create(
                hotel=hotel, number=str(100 + i), room_type='single', price_per_night=10000 + i,
            )

    def test_first_page_has_six_rooms(self):
        resp = self.client.get(reverse('rooms:room_list'))
        self.assertEqual(len(resp.context['rooms']), 6)
        self.assertTrue(resp.context['is_paginated'])

    def test_second_page_has_remaining_rooms(self):
        resp = self.client.get(reverse('rooms:room_list'), {'page': 2})
        self.assertEqual(len(resp.context['rooms']), 2)


class SeedRoomsCommandTests(TestCase):
    """Тесты сидера seed_rooms (Занятие 3: скрипты-наполнители)."""

    def setUp(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)  # rooms зависят от hotels

    def test_seed_rooms_creates_demo_rooms(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        self.assertGreater(Room.objects.count(), 0)

    def test_seed_rooms_is_idempotent(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        count_first = Room.objects.count()
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        self.assertEqual(Room.objects.count(), count_first)

    def test_seed_rooms_sets_demo_image_path(self):
        """Одноместный номер в Grand Astana получает заготовленный путь к фото."""
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_rooms', stdout=StringIO(), verbosity=0)
        room = Room.objects.filter(hotel__name='Grand Astana', room_type='single').first()
        self.assertIsNotNone(room)
        self.assertEqual(room.image.name, 'rooms/images/demo/single-room.jpg')
