# ────────────────────────────────────────────────────────────────────────────
# hotels/tests.py — тесты приложения отелей.
#
# Проверяем: строковое представление модели, фильтрацию списка по городу,
# страницу отеля и поведение при неактивном/несуществующем отеле.
#
# Запуск:  python manage.py test hotels
# ────────────────────────────────────────────────────────────────────────────

import io
import tempfile

from PIL import Image

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from hotels.models import Hotel

User = get_user_model()


class HotelModelTests(TestCase):
    """Тесты модели Hotel."""

    def test_str_returns_name(self):
        """__str__ возвращает название отеля (видно в админке и шаблонах)."""
        hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='ул. Тест, 1', price=45000,
        )
        self.assertEqual(str(hotel), 'Grand Astana')

    def test_defaults(self):
        """Значения по умолчанию: is_active=True, rating=0."""
        hotel = Hotel.objects.create(
            name='Almaty Plaza', city='Алматы', address='ул. Достык, 85', price=38000,
        )
        self.assertTrue(hotel.is_active)
        self.assertEqual(hotel.rating, 0)


class HotelListViewTests(TestCase):
    """Тесты списка отелей и поиска по городу."""

    def setUp(self):
        # Три отеля в разных городах + один неактивный.
        Hotel.objects.create(name='Grand Astana', city='Астана',
                             address='а', price=45000, is_active=True)
        Hotel.objects.create(name='Almaty Plaza', city='Алматы',
                             address='б', price=38000, is_active=True)
        Hotel.objects.create(name='Old Hotel', city='Астана',
                             address='в', price=10000, is_active=False)

    def test_list_shows_only_active(self):
        """В списке отображаются только активные отели."""
        resp = self.client.get(reverse('hotels:hotel_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Grand Astana')
        self.assertContains(resp, 'Almaty Plaza')
        self.assertNotContains(resp, 'Old Hotel')  # неактивный скрыт

    def test_search_by_city(self):
        """Поиск ?city=Алматы возвращает только отели этого города."""
        resp = self.client.get(reverse('hotels:hotel_list'), {'city': 'Алматы'})
        self.assertContains(resp, 'Almaty Plaza')
        self.assertNotContains(resp, 'Grand Astana')

    def test_search_case_insensitive(self):
        """Поиск не чувствителен к регистру (icontains)."""
        resp = self.client.get(reverse('hotels:hotel_list'), {'city': 'алматы'})
        self.assertContains(resp, 'Almaty Plaza')


class HotelDetailViewTests(TestCase):
    """Тесты страницы одного отеля."""

    def setUp(self):
        self.hotel = Hotel.objects.create(
            name='Grand Astana', city='Астана', address='ул. Тест, 1', price=45000,
        )

    def test_detail_page_ok(self):
        """Страница активного отеля открывается и содержит его название."""
        resp = self.client.get(reverse('hotels:hotel_detail', args=[self.hotel.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Grand Astana')

    def test_missing_hotel_returns_404(self):
        """Несуществующий отель отдаёт страницу 404."""
        resp = self.client.get(reverse('hotels:hotel_detail', args=[9999]))
        self.assertEqual(resp.status_code, 404)

    def test_inactive_hotel_returns_404(self):
        """Неактивный отель недоступен по прямой ссылке (404)."""
        self.hotel.is_active = False
        self.hotel.save()
        resp = self.client.get(reverse('hotels:hotel_detail', args=[self.hotel.pk]))
        self.assertEqual(resp.status_code, 404)


class HotelListPaginationAndStatsTests(TestCase):
    """
    Аудит, дефекты №8/№14: у списка отелей не было ни пагинации, ни
    сортировки, а цена бралась из отдельного Hotel.price, который мог
    разойтись с ценами номеров. HotelListView + HotelQuerySet.with_stats()
    приводят hotels к тому же виду, что и rooms на Занятии 1.
    """

    def setUp(self):
        for i in range(8):
            Hotel.objects.create(
                name=f'Hotel {i}', city='Астана', address='а',
                price=10000, rating=3.0 + (i % 5) * 0.4,
            )

    def test_first_page_has_six_hotels(self):
        resp = self.client.get(reverse('hotels:hotel_list'))
        self.assertEqual(len(resp.context['hotels']), 6)
        self.assertTrue(resp.context['is_paginated'])

    def test_second_page_has_remaining_hotels(self):
        resp = self.client.get(reverse('hotels:hotel_list'), {'page': 2})
        self.assertEqual(len(resp.context['hotels']), 2)

    def test_min_price_reflects_cheapest_room_not_hotel_price(self):
        """
        min_price должен считаться по ценам НОМЕРОВ, а не повторять
        Hotel.price — именно это расхождение и есть дефект №14.
        """
        from rooms.models import Room
        hotel = Hotel.objects.create(
            name='Grand Astana', city='Алматы', address='б', price=99999, rating=4.0,
        )
        Room.objects.create(hotel=hotel, number='101', room_type='single', price_per_night=15000)
        Room.objects.create(hotel=hotel, number='102', room_type='double', price_per_night=20000)

        stats = Hotel.objects.with_stats().get(pk=hotel.pk)
        self.assertEqual(stats.min_price, 15000)
        self.assertEqual(stats.rooms_count, 2)
        self.assertNotEqual(stats.min_price, hotel.price)

    def test_hotel_without_rooms_has_no_min_price(self):
        hotel = Hotel.objects.create(name='Empty Hotel', city='Астана', address='в', price=5000)
        stats = Hotel.objects.with_stats().get(pk=hotel.pk)
        self.assertIsNone(stats.min_price)

    def test_sort_by_price_ascending(self):
        """
        Проверяем саму сортировку через HotelListView.SORTS напрямую на
        отфильтрованном по городу запросе — страница 1 списка иначе может
        оказаться занята восемью отелями без номеров из setUp (у них
        min_price = None, а NULL в SQLite сортируется первым по
        возрастанию, что не относится к проверяемому поведению).
        """
        from rooms.models import Room
        cheap = Hotel.objects.create(name='Cheap', city='Павлодар', address='г', price=1, rating=1)
        pricey = Hotel.objects.create(name='Pricey', city='Павлодар', address='д', price=1, rating=1)
        Room.objects.create(hotel=cheap, number='1', room_type='single', price_per_night=5000)
        Room.objects.create(hotel=pricey, number='1', room_type='single', price_per_night=90000)

        resp = self.client.get(reverse('hotels:hotel_list'), {'sort': 'price', 'city': 'Павлодар'})
        names = [h.name for h in resp.context['hotels']]
        self.assertEqual(names, ['Cheap', 'Pricey'])


class HotelRatingValidationTests(TestCase):
    """
    Регрессионный тест на дефект №7 из аудита: раньше Hotel.rating
    принимал любое число (например, 17.5 в админке).
    """

    def test_rating_above_five_is_rejected(self):
        hotel = Hotel(name='Bad Hotel', city='Тест', address='а', price=1000, rating=17.5)
        with self.assertRaises(ValidationError):
            hotel.full_clean()

    def test_rating_within_range_is_accepted(self):
        hotel = Hotel(name='Good Hotel', city='Тест', address='а', price=1000, rating=4.5)
        hotel.full_clean()  # не должно бросить исключение


class HotelCoverUploadTests(TestCase):
    """
    Занятие 2: загрузка обложки отеля — проверяем валидацию расширения
    и то, что корректный файл действительно сохраняется в поле cover.
    """

    def _make_image_file(self, name='cover.jpg', size=(10, 10), fmt='JPEG'):
        """Готовим маленькое настоящее изображение в памяти через Pillow —
        FileExtensionValidator и ImageField должны принять его как валидное."""
        buffer = io.BytesIO()
        Image.new('RGB', size, color='red').save(buffer, format=fmt)
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_valid_image_is_accepted(self):
        hotel = Hotel.objects.create(
            name='Photo Hotel', city='Тест', address='а', price=1000,
            cover=self._make_image_file(),
        )
        hotel.full_clean()
        self.assertTrue(hotel.cover.name.endswith('cover.jpg'))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_disallowed_extension_is_rejected(self):
        bad_file = SimpleUploadedFile('cover.txt', b'not an image', content_type='text/plain')
        hotel = Hotel(name='Bad Photo Hotel', city='Тест', address='а', price=1000, cover=bad_file)
        with self.assertRaises(ValidationError):
            hotel.full_clean()


class HotelExportImportTests(TestCase):
    """
    Занятие 2: экспорт каталога в CSV/Excel/PDF/Word и импорт отелей
    из CSV или Excel персоналом.
    """

    def setUp(self):
        Hotel.objects.create(name='Grand Astana', city='Астана', address='а', price=45000, rating=4.7)
        self.staff = User.objects.create_user(username='staff', password='pass12345', is_staff=True)
        self.staff.user_permissions.add(
            Permission.objects.get(codename='add_hotel', content_type__app_label='hotels')
        )
        self.regular = User.objects.create_user(username='guest', password='pass12345')

    # ---- экспорт: по одному тесту на формат ----------------------------------

    def test_export_csv_returns_hotel_data(self):
        resp = self.client.get(reverse('hotels:export_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Grand Astana', resp.content.decode('utf-8-sig'))

    def test_export_xlsx_returns_valid_workbook(self):
        from openpyxl import load_workbook
        resp = self.client.get(reverse('hotels:export_xlsx'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('spreadsheetml', resp['Content-Type'])
        wb = load_workbook(io.BytesIO(resp.content))
        values = [cell.value for row in wb.active.iter_rows() for cell in row]
        self.assertIn('Grand Astana', values)

    def test_export_pdf_returns_pdf_file(self):
        resp = self.client.get(reverse('hotels:export_pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))  # сигнатура PDF-файла

    def test_export_docx_returns_word_file(self):
        resp = self.client.get(reverse('hotels:export_docx'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('wordprocessingml', resp['Content-Type'])
        self.assertTrue(resp.content.startswith(b'PK'))  # .docx — это ZIP-контейнер

    # ---- импорт: доступ и CSV -------------------------------------------------

    def test_import_requires_staff_permission(self):
        """Обычный пользователь получает 403 — импорт не для всех (аудит)."""
        self.client.login(username='guest', password='pass12345')
        resp = self.client.get(reverse('hotels:import_hotels'))
        self.assertEqual(resp.status_code, 403)

    def test_import_creates_hotels_from_valid_csv(self):
        self.client.login(username='staff', password='pass12345')
        csv_content = (
            'name,city,address,price,rating\n'
            'Karaganda Central,Караганда,пр. Бухар жырау 40,24000,4.0\n'
            'Turkistan Palace,Туркестан,ул. Айтеке би 7,33000,4.6\n'
        )
        csv_file = SimpleUploadedFile('hotels.csv', csv_content.encode('utf-8'), content_type='text/csv')
        resp = self.client.post(reverse('hotels:import_hotels'), {'import_file': csv_file})
        self.assertRedirects(resp, reverse('hotels:hotel_list'))
        self.assertTrue(Hotel.objects.filter(name='Karaganda Central').exists())
        self.assertTrue(Hotel.objects.filter(name='Turkistan Palace').exists())

    def test_import_rolls_back_on_bad_row(self):
        """Одна невалидная строка (рейтинг 99) отменяет весь импорт — ни один отель не создаётся."""
        self.client.login(username='staff', password='pass12345')
        csv_content = (
            'name,city,address,price,rating\n'
            'Valid Hotel,Астана,ул. А 1,20000,4.0\n'
            'Broken Hotel,Астана,ул. Б 2,20000,99\n'
        )
        csv_file = SimpleUploadedFile('hotels.csv', csv_content.encode('utf-8'), content_type='text/csv')
        before = Hotel.objects.count()
        self.client.post(reverse('hotels:import_hotels'), {'import_file': csv_file})
        self.assertEqual(Hotel.objects.count(), before)  # ничего не создано
        self.assertFalse(Hotel.objects.filter(name='Valid Hotel').exists())

    # ---- импорт: Excel ---------------------------------------------------------

    def test_import_creates_hotels_from_valid_xlsx(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(['name', 'city', 'address', 'price', 'rating'])
        ws.append(['Kokshetau Hotel', 'Кокшетау', 'ул. Абая 5', 21000, 4.1])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        xlsx_file = SimpleUploadedFile(
            'hotels.xlsx', buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.client.login(username='staff', password='pass12345')
        resp = self.client.post(reverse('hotels:import_hotels'), {'import_file': xlsx_file})
        self.assertRedirects(resp, reverse('hotels:hotel_list'))
        self.assertTrue(Hotel.objects.filter(name='Kokshetau Hotel').exists())

    def test_import_rejects_unsupported_extension(self):
        """Файл .pdf на вход импорта не принимается — это формат только для чтения."""
        self.client.login(username='staff', password='pass12345')
        bad_file = SimpleUploadedFile('hotels.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post(reverse('hotels:import_hotels'), {'import_file': bad_file})
        self.assertEqual(resp.status_code, 200)  # форма не прошла валидацию, страница переспрашивает
        self.assertContains(resp, 'Поддерживаются только файлы .csv и .xlsx')


class SeedHotelsCommandTests(TestCase):
    """Тесты сидера seed_hotels (Занятие 3: скрипты-наполнители)."""

    def test_seed_hotels_creates_demo_hotels(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        self.assertTrue(Hotel.objects.filter(name='Grand Astana').exists())
        self.assertGreater(Hotel.objects.count(), 0)

    def test_seed_hotels_is_idempotent(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        count_first = Hotel.objects.count()
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        self.assertEqual(Hotel.objects.count(), count_first)

    def test_seed_hotels_sets_demo_cover_path(self):
        """
        Grand Astana и Almaty Plaza получают заготовленный путь к обложке
        (media/hotels/covers/demo/...), даже если файла ещё нет на диске —
        см. ИЗМЕНЕНИЯ_ЗАНЯТИЕ_2.md, раздел про размещение картинок.
        """
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_hotels', stdout=StringIO(), verbosity=0)
        hotel = Hotel.objects.get(name='Grand Astana')
        self.assertEqual(hotel.cover.name, 'hotels/covers/demo/grand-astana.jpg')
