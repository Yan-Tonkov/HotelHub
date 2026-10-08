ПОДКЛЮЧЕНИЕ ПРИЛОЖЕНИЯ rooms
=============================

Приложение создано по аналогии с hotels. Скопируйте папку rooms
в корень проекта (рядом с hotels и manage.py) и выполните 3 шага.


ШАГ 1. Зарегистрировать в config/settings.py
---------------------------------------------
В список INSTALLED_APPS добавьте строку:

    INSTALLED_APPS = [
        ...
        'hotels.apps.HotelsConfig',
        'rooms.apps.RoomsConfig',      # <- добавить
    ]


ШАГ 2. Подключить маршруты в config/urls.py
--------------------------------------------
    urlpatterns = [
        path('admin/', admin.site.urls),
        path('hotels/', include('hotels.urls')),
        path('rooms/', include('rooms.urls')),   # <- добавить
    ]


ШАГ 3. Создать таблицу в базе
------------------------------
    python manage.py makemigrations
    python manage.py migrate


ЗАПУСК И ПРОВЕРКА
-----------------
    python manage.py runserver

    Админка:  http://127.0.0.1:8000/admin/   (раздел "Номера")
    Страница: http://127.0.0.1:8000/rooms/


ДОБАВИТЬ ТЕСТОВЫЕ НОМЕРА (через консоль)
----------------------------------------
    python manage.py shell

    >>> from hotels.models import Hotel
    >>> from rooms.models import Room
    >>> h = Hotel.objects.first()      # берём любой существующий отель
    >>> Room.objects.create(hotel=h, number="101", room_type="single",
    ...     price_per_night=15000, capacity=1,
    ...     description="Уютный одноместный номер с видом во двор.")
    >>> Room.objects.create(hotel=h, number="205", room_type="double",
    ...     price_per_night=25000, capacity=2,
    ...     description="Двухместный номер с балконом.")
    >>> exit()


ВАЖНО
-----
- Модель Room связана с Hotel через ForeignKey, поэтому в базе уже
  должен быть хотя бы один отель (иначе номер не к чему привязать).
- Поиск в views.py использует .lower() с обеих сторон — это нужно,
  чтобы регистр работал корректно для кириллицы на SQLite.
- В шаблоне обязательно стоит {% load static %} в первой строке.
