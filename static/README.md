# Глобальная статика проекта HotelHub

Эта папка `static/` лежит в КОРНЕ проекта (рядом с `manage.py` и папкой `config/`)
и содержит файлы, общие для всех приложений: общий CSS, базовый JS, логотип, шрифты.

Это НЕ то же самое, что `hotels/static/hotels/...` — там лежит статика конкретного
приложения. Здесь — глобальная статика всего проекта.

## Структура

    проект/
    ├── manage.py
    ├── config/
    ├── hotels/
    └── static/              <- эта папка
        ├── css/base.css     общие стили и переменные
        ├── js/main.js       общий скрипт
        ├── img/             логотип, favicon, баннеры
        └── fonts/           шрифты проекта


## ШАГ 1. Настройки в config/settings.py

Убедитесь, что вверху файла определён BASE_DIR (обычно он уже есть):

    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent.parent

В самом низу файла, рядом со STATIC_URL, добавьте STATICFILES_DIRS:

    STATIC_URL = 'static/'

    # Папки с глобальной статикой проекта (вне приложений)
    STATICFILES_DIRS = [
        BASE_DIR / 'static',
    ]

    # Куда collectstatic соберёт всю статику для боевого сервера
    STATIC_ROOT = BASE_DIR / 'staticfiles'

ВАЖНО: STATICFILES_DIRS и STATIC_ROOT должны указывать на РАЗНЫЕ папки.


## ШАГ 2. Подключение в шаблоне

В начале шаблона:

    {% load static %}

В <head>:

    <link rel="stylesheet" href="{% static 'css/base.css' %}">

Перед </body>:

    <script src="{% static 'js/main.js' %}"></script>

Логотип:

    <img src="{% static 'img/logo.png' %}" alt="HotelHub">


## ШАГ 3. Проверка

    python manage.py runserver

Откройте страницу — стили из base.css должны примениться.
Найти, откуда грузится файл, можно командой:

    python manage.py findstatic css/base.css


## Локальный запуск vs боевой сервер

- При DEBUG = True Django сам раздаёт статику из STATICFILES_DIRS — ничего
  дополнительно делать не нужно.
- Перед выкладкой на сервер (DEBUG = False) один раз выполните:

    python manage.py collectstatic

  Эта команда соберёт всё в папку STATIC_ROOT (staticfiles/).
