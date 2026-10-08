# ────────────────────────────────────────────────────────────────────────────
# users/tests.py — тесты приложения пользователей.
#
# Проверяем: кастомную модель User (поля phone/avatar), сценарий регистрации
# с авто-входом, вход/выход, защиту профиля, а также сидер seed_users.
#
# Запуск:  python manage.py test users
# ────────────────────────────────────────────────────────────────────────────

from io import BytesIO, StringIO
import tempfile

from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    """Тесты кастомной модели пользователя."""

    def test_create_user_with_extra_fields(self):
        """Кастомные поля phone/avatar доступны при создании пользователя."""
        u = User.objects.create_user(
            username='ivan', password='pass12345', phone='+77001112233',
        )
        self.assertEqual(u.phone, '+77001112233')
        # Пароль хранится в ХЭШИРОВАННОМ виде, но проверяется через check_password.
        self.assertTrue(u.check_password('pass12345'))
        self.assertEqual(str(u), 'ivan')

    def test_phone_is_optional(self):
        """Телефон необязателен — пользователь создаётся и без него."""
        u = User.objects.create_user(username='nophone', password='pass12345')
        self.assertIn(u.phone, (None, ''))


class AuthFlowTests(TestCase):
    """Тесты регистрации, входа, выхода и защиты профиля."""

    def test_register_logs_user_in(self):
        """После регистрации пользователь сразу авторизован (редирект в профиль)."""
        resp = self.client.post(reverse('users:register'), {
            'username': 'newbie', 'email': 'n@e.com', 'phone': '+7700',
            'password1': 'ComplexPass2026', 'password2': 'ComplexPass2026',
        })
        self.assertRedirects(resp, reverse('users:profile'))
        self.assertTrue(User.objects.filter(username='newbie').exists())

    def test_profile_requires_login(self):
        """Гость не может открыть профиль — редирект на страницу входа."""
        resp = self.client.get(reverse('users:profile'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('users:login'), resp.url)

    def test_login_and_logout(self):
        """Пользователь входит, попадает в профиль, затем выходит."""
        User.objects.create_user(username='guest', password='pass12345')

        # Вход с корректными данными -> редирект в профиль.
        resp = self.client.post(reverse('users:login'), {
            'username': 'guest', 'password': 'pass12345',
        })
        self.assertRedirects(resp, reverse('users:profile'))

        # Профиль теперь доступен (200), гостя не редиректит.
        resp = self.client.get(reverse('users:profile'))
        self.assertEqual(resp.status_code, 200)

        # Выход -> редирект на главную. Только POST (аудит, дефект №5;
        # см. также test_logout_via_get_is_not_allowed).
        resp = self.client.post(reverse('users:logout'))
        self.assertRedirects(resp, reverse('core:home'))

    def test_login_wrong_password_fails(self):
        """Неверный пароль не пускает — остаёмся на странице входа (200)."""
        User.objects.create_user(username='guest', password='pass12345')
        resp = self.client.post(reverse('users:login'), {
            'username': 'guest', 'password': 'wrong',
        })
        self.assertEqual(resp.status_code, 200)  # без редиректа = вход не выполнен

    def test_logout_via_get_is_not_allowed(self):
        """
        Регрессионный тест на дефект №5: выход должен требовать POST.
        Обычная GET-ссылка (в т.ч. подставленная на стороннем сайте) не
        должна разлогинивать пользователя.
        """
        User.objects.create_user(username='guest', password='pass12345')
        self.client.login(username='guest', password='pass12345')
        resp = self.client.get(reverse('users:logout'))
        self.assertEqual(resp.status_code, 405)
        # Пользователь остался в сессии — профиль всё ещё доступен.
        resp = self.client.get(reverse('users:profile'))
        self.assertEqual(resp.status_code, 200)

    def test_login_blocks_open_redirect(self):
        """
        Регрессионный тест на дефект №2: ?next= на чужой домен не должен
        сработать — после входа пользователя должно вернуть в профиль,
        а не на сторонний сайт.
        """
        User.objects.create_user(username='guest', password='pass12345')
        resp = self.client.post(
            reverse('users:login') + '?next=https://evil.example.com/',
            {'username': 'guest', 'password': 'pass12345', 'next': 'https://evil.example.com/'},
        )
        self.assertRedirects(resp, reverse('users:profile'))

    def test_login_allows_safe_next(self):
        """Свой собственный внутренний адрес в ?next= по-прежнему работает."""
        User.objects.create_user(username='guest', password='pass12345')
        resp = self.client.post(reverse('users:login'), {
            'username': 'guest', 'password': 'pass12345',
            'next': reverse('hotels:hotel_list'),
        })
        self.assertRedirects(resp, reverse('hotels:hotel_list'))


class SeedUsersCommandTests(TestCase):
    """Тесты сидера seed_users."""

    def test_seed_users_creates_demo_accounts(self):
        """Команда создаёт демо-гостя guest и суперпользователя admin."""
        call_command('seed_users', stdout=StringIO(), verbosity=0)
        self.assertTrue(User.objects.filter(username='guest').exists())
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)  # admin действительно суперпользователь

    def test_seed_users_idempotent(self):
        """Повторный запуск не плодит дубли пользователей."""
        call_command('seed_users', stdout=StringIO(), verbosity=0)
        count_first = User.objects.count()
        call_command('seed_users', stdout=StringIO(), verbosity=0)
        self.assertEqual(User.objects.count(), count_first)


class ProfileEditTests(TestCase):
    """
    Занятие 2: форма редактирования профиля и загрузка аватара
    (аудит, дефект №9 — поле avatar существовало, но формы для него не было).
    """

    def setUp(self):
        self.user = User.objects.create_user(username='guest', password='pass12345')
        self.client.login(username='guest', password='pass12345')

    def test_edit_page_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('users:profile_edit'))
        self.assertEqual(resp.status_code, 302)  # редирект на страницу входа

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_avatar_upload_updates_profile(self):
        buffer = BytesIO()
        Image.new('RGB', (10, 10), color='blue').save(buffer, format='JPEG')
        buffer.seek(0)
        avatar = SimpleUploadedFile('avatar.jpg', buffer.read(), content_type='image/jpeg')

        resp = self.client.post(reverse('users:profile_edit'), {
            'email': 'guest@example.com',
            'phone': '+7 700 000 00 00',
            'avatar': avatar,
        })
        self.assertRedirects(resp, reverse('users:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name.endswith('avatar.jpg'))
        self.assertEqual(self.user.email, 'guest@example.com')
