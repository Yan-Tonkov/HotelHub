"""
Корневая маршрутизация проекта HotelHub.

config/urls.py — «диспетчер»: он принимает запрос и по началу адреса
передаёт его в нужное приложение (include). Каждое приложение хранит свои
маршруты в собственном urls.py.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),               # /admin/  — панель администратора

    path('', include('core.urls')),                # /        — главная страница
    path('users/', include('users.urls')),         # /users/  — регистрация, вход, профиль
    path('hotels/', include('hotels.urls')),       # /hotels/ — отели
    path('rooms/', include('rooms.urls')),         # /rooms/  — номера
    path('bookings/', include('bookings.urls')),   # /bookings/ — бронирования
]

# В режиме разработки (DEBUG=True) отдаём загруженные медиафайлы (аватары,
# обложки отелей, фото номеров) напрямую через Django. В продакшене этим
# занимается веб-сервер.
#
# Раздачу STATIC_URL здесь намеренно не дублируем: пока
# 'django.contrib.staticfiles' в INSTALLED_APPS и DEBUG=True, статику и так
# отдаёт django.contrib.staticfiles.views.serve — вторая строка static()
# была лишней (см. аудит, дефект №15).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
