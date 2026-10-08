"""
Django settings for config project (HotelHub).

Django 6.0.5. Учебный проект: сервис поиска и бронирования отелей.
Здесь описана глобальная конфигурация — какие приложения подключены,
где лежат шаблоны, статика и медиа, а также кастомная модель пользователя.
"""

import os
from pathlib import Path

# Базовый путь проекта. Всё строится относительно него: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: секретный ключ держите в тайне в продакшене!
# Значение берётся из переменной окружения DJANGO_SECRET_KEY; если её нет
# (обычная ситуация на локальной машине студента), используется учебный
# ключ-заглушка — с ним удобно запускать проект «из коробки», но именно
# поэтому реальный продакшен-ключ никогда не хранят в коде (аудит, дефект №13).
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-rod5(vtz@7)vm^yhsfqegx(f^cqady3qi(j*89ma2diqp(ucdt',
)

# SECURITY WARNING: не включайте DEBUG в продакшене!
# '1'/'true' → True, всё остальное → False. По умолчанию — True (учебный режим).
DEBUG = os.environ.get('DJANGO_DEBUG', '1').lower() in ('1', 'true', 'yes')

# Хосты, которым разрешено обслуживать проект. Для учебной разработки
# перечисляем локальные адреса и 'testserver' (его использует тест-клиент
# Django). В продакшене список хостов передают через переменную окружения.
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'localhost,127.0.0.1,[::1],testserver',
).split(',')


# ---------------------------------------------------------------------------
# Приложения
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Приложения проекта HotelHub.
    # core объединяет проект и отдаёт главную страницу.
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'hotels.apps.HotelsConfig',
    'rooms.apps.RoomsConfig',
    'bookings.apps.BookingsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Глобальная папка шаблонов проекта (base.html, навигация, футер).
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ---------------------------------------------------------------------------
# Валидация паролей
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Статика и медиа
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
# Глобальная статика проекта (общие css/js/img).
STATICFILES_DIRS = [BASE_DIR / 'static']
# Куда collectstatic собирает файлы для продакшена.
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Медиа — загружаемые пользователями файлы (аватары профиля и т.п.).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Аутентификация
# ---------------------------------------------------------------------------
# Кастомная модель пользователя (users/models.py): наследник AbstractUser
# с дополнительными полями phone и avatar.
AUTH_USER_MODEL = 'users.User'

# Куда отправлять после входа / выхода и куда вести гостей с закрытых страниц.
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'users:profile'
LOGOUT_REDIRECT_URL = 'core:home'
