from django.db import models
from django.core.validators import FileExtensionValidator

from core.validators import ALLOWED_IMAGE_EXTENSIONS, validate_image_size
from hotels.models import Hotel


def room_image_path(instance, filename):
    """Путь для фото номера: media/rooms/images/<id_номера>/<имя_файла>."""
    return f'rooms/images/{instance.pk or "new"}/{filename}'


class RoomQuerySet(models.QuerySet):
    """
    Собственный QuerySet модели Room (Занятие 1 «Данные и выборки»,
    раздел «Умная форма поиска»; дополнен при аудите — см. on_sale()
    и with_today_status() ниже, дефект №4).

    Вынесен как метод QuerySet, а не код прямо во view, чтобы одна и та же
    логика «какие номера свободны на даты» была доступна и из view, и из
    сидеров, и из тестов — без копипасты.
    """

    def on_sale(self):
        """
        Номера, которые отель вообще выставил на продажу (is_available=True).

        Это НЕ означает «свободен прямо сейчас»: поле is_available — ручной
        переключатель персонала (например, «номер временно снят с продажи
        на ремонт»), а не признак занятости на конкретные даты. Раньше это
        поле использовалось в шаблонах как единственный источник бейджа
        «Свободен/Занят» (аудит, дефект №4) — из-за чего номер с бронью на
        завтра всё равно показывался «Свободен» для любых других дат.
        Теперь это разделено: on_sale() отвечает только за «виден ли номер
        на сайте вообще», а фактическая занятость на даты считается
        отдельно — free_between() (для поиска по интервалу) и
        with_today_status() (для бейджа на сегодня).
        """
        return self.filter(is_available=True)

    def free_between(self, check_in, check_out):
        """
        Оставить только номера, СВОБОДНЫЕ на интервал [check_in, check_out).

        Важно: в документе занятия 1 пример считал номер занятым при ЛЮБОЙ
        пересекающейся брони — включая уже ОТМЕНЁННУЮ (status='cancelled').
        Это ошибка: отменённая бронь не должна блокировать номер, иначе
        клиент, отменивший бронь, никогда не увидит этот номер свободным
        на те же даты. Используем тот же список активных статусов, что и
        сервисный слой bookings (bookings/services.py::ACTIVE_STATUSES) —
        единственный источник правды о том, что считается «занято».

        Booking импортируется внутри метода, а не в начале файла: rooms
        физически не должен зависеть от bookings на уровне модуля (иначе
        при загрузке приложений возник бы циклический импорт, так как
        bookings/models.py и bookings/services.py импортируют Room из
        rooms.models). Отложенный импорт — стандартный приём Django для
        таких ситуаций.

        Реализовано через ~Exists(OuterRef(...)) — коррелированный
        подзапрос «есть ли у ЭТОГО номера пересекающаяся активная бронь» —
        вместо .exclude(pk__in=values_list(...)) из предыдущей версии.
        Результат тот же, но Exists не тянет в память список id броней
        отдельным запросом: вся проверка остаётся одним SQL-запросом к
        Room с подзапросом внутри (аудит, дефект №4 — рекомендованный
        приём подтверждён в задании).
        """
        from bookings.services import ACTIVE_STATUSES
        from bookings.models import Booking

        overlapping = Booking.objects.filter(
            room=models.OuterRef('pk'),
            status__in=ACTIVE_STATUSES,
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
        return self.filter(~models.Exists(overlapping))

    def with_today_status(self, as_of=None):
        """
        Добавляет каждому номеру в выборке аннотацию occupied_today —
        есть ли у него активная бронь, покрывающая указанный день
        (по умолчанию — сегодня, по локальной таймзоне проекта).

        Используется в шаблонах карточек и странице номера вместо
        статичного is_available для бейджа «Свободен сейчас / Занят
        сейчас» (аудит, дефект №4). is_available и occupied_today — два
        независимых признака: номер может быть «в продаже», но занятым
        сегодня, или наоборот — снятым с продажи, но без текущей брони.

        Аннотация вместо отдельного запроса в цикле шаблона — чтобы не
        получить N+1 (один подзапрос Exists на всю страницу карточек,
        а не по одному дополнительному запросу на каждую карточку).
        """
        from django.utils import timezone
        from bookings.services import ACTIVE_STATUSES
        from bookings.models import Booking

        today = as_of or timezone.localdate()
        occupied = Booking.objects.filter(
            room=models.OuterRef('pk'),
            status__in=ACTIVE_STATUSES,
            check_in__lte=today,
            check_out__gt=today,
        )
        return self.annotate(occupied_today=models.Exists(occupied))


class Room(models.Model):
    ROOM_TYPES = [
        ('single', 'Одноместный'),
        ('double', 'Двухместный'),
        ('suite', 'Люкс'),
        ('family', 'Семейный'),
    ]

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='rooms'
    )

    number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='single')

    description = models.TextField(blank=True, null=True)
    # цена за одну ночь проживания
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    capacity = models.PositiveIntegerField(default=1)
    # Ручной переключатель «выставлен ли номер на продажу вообще» (например,
    # можно снять номер с продажи на ремонт) — НЕ признак занятости на
    # конкретные даты. Фактическую занятость считают RoomQuerySet.free_between()
    # (поиск по интервалу) и RoomQuerySet.with_today_status() (бейдж на
    # сегодня) — см. комментарии к ним выше (аудит, дефект №4). Имя поля
    # оставлено прежним, чтобы не плодить миграцию ради переименования;
    # смысл закреплён здесь и в on_sale().
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ---- Занятие 2: фото номера --------------------------------------------
    image = models.ImageField(
        'Фото номера',
        upload_to=room_image_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
        ],
        help_text='JPG/PNG/WEBP, не более 5 МБ.',
    )

    # Подключаем RoomQuerySet как менеджер: Room.objects.free_between(...)
    # работает напрямую, без промежуточного .all().
    objects = RoomQuerySet.as_manager()

    class Meta:
        verbose_name = 'Номер'
        verbose_name_plural = 'Номера'
        ordering = ['-created_at']
        constraints = [
            # В одном отеле не может быть двух номеров с одинаковым названием.
            models.UniqueConstraint(
                fields=['hotel', 'number'],
                name='room_unique_number_per_hotel',
            ),
        ]
        indexes = [
            # Ускоряет выборку свободных номеров с фильтром по типу.
            models.Index(fields=['is_available', 'room_type'], name='room_avail_type_idx'),
        ]

    def __str__(self):
        return f'{self.hotel.name} — номер {self.number}'
