# ────────────────────────────────────────────────────────────────────────────
# bookings/services.py — СЕРВИСНЫЙ СЛОЙ приложения bookings.
#
# Зачем нужен сервисный слой. В «толстых» view бизнес-логика (расчёт цены,
# проверка занятости номера, смена статуса) перемешана с обработкой HTTP.
# Из-за этого её тяжело переиспользовать и тестировать: чтобы проверить
# расчёт, приходится поднимать весь веб-запрос.
#
# Здесь мы выносим правила предметной области в отдельные функции, которые:
#   • ничего не знают про request/response — принимают обычные объекты;
#   • легко вызываются и из view, и из management-команд, и из тестов;
#   • покрываются юнит-тестами напрямую (см. bookings/tests.py, класс сервисов).
#
# View становится «тонким»: принял запрос -> вызвал сервис -> вернул ответ.
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from rooms.models import Room
from .models import Booking


# Статусы брони, при которых номер считается занятым в эти даты.
# Отменённые (cancelled) брони не блокируют номер.
ACTIVE_STATUSES = ('pending', 'confirmed')


def calculate_nights(check_in: date, check_out: date) -> int:
    """
    Посчитать число ночей между заездом и выездом.

    Возвращает целое число ночей. Если выезд не позже заезда — 0
    (защита от отрицательных значений при расчёте цены).
    """
    nights = (check_out - check_in).days
    return nights if nights > 0 else 0


def calculate_total_price(room: Room, check_in: date, check_out: date) -> Decimal:
    """
    Итоговая стоимость проживания = цена номера за ночь × число ночей.

    Вынесено в сервис, чтобы одну и ту же формулу использовали и модель
    (свойство Booking.total_price), и предпросмотр цены во view, и тесты.
    """
    nights = calculate_nights(check_in, check_out)
    return room.price_per_night * nights


def validate_booking_dates(check_in: date, check_out: date) -> None:
    """
    Проверить корректность дат брони. Ничего не возвращает — при ошибке
    выбрасывает ValidationError с понятным сообщением.

    Правила:
      • обе даты обязательны;
      • заезд не может быть в прошлом;
      • выезд должен быть строго позже заезда.
    """
    if check_in is None or check_out is None:
        raise ValidationError('Укажите даты заезда и выезда.')
    if check_in < date.today():
        raise ValidationError('Дата заезда не может быть в прошлом.')
    if check_out <= check_in:
        raise ValidationError('Дата выезда должна быть позже даты заезда.')


def is_room_available(room: Room, check_in: date, check_out: date,
                      exclude_booking_id: int | None = None) -> bool:
    """
    Свободен ли номер на выбранный интервал дат.

    Две брони пересекаются, если начало одной раньше конца другой И
    конец одной позже начала другой (классическая проверка пересечения
    интервалов: existing.check_in < new.check_out и
    existing.check_out > new.check_in).

    exclude_booking_id позволяет исключить саму себя при редактировании
    существующей брони, чтобы она не «конфликтовала» сама с собой.
    """
    overlapping = Booking.objects.filter(
        room=room,
        status__in=ACTIVE_STATUSES,
    ).filter(
        Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
    )
    if exclude_booking_id is not None:
        overlapping = overlapping.exclude(pk=exclude_booking_id)
    return not overlapping.exists()


@transaction.atomic
def create_booking(user, room: Room, check_in: date, check_out: date,
                   guests: int = 1) -> Booking:
    """
    Создать бронь с полной проверкой бизнес-правил.

    Последовательно проверяет: корректность дат, вместимость номера,
    занятость на эти даты. Только если все проверки пройдены — создаёт
    и возвращает объект Booking. Иначе выбрасывает ValidationError.

    Гонка при параллельных запросах (аудит, дефект №3). Раньше проверка
    занятости (is_room_available) и запись Booking.objects.create()
    выполнялись отдельными операциями: если два запроса на одни и те же
    даты приходили одновременно, оба успевали пройти проверку до того,
    как первый успевал сохранить бронь, — в базе оказывались два
    пересекающихся бронирования одного номера.

    Исправление — transaction.atomic() оборачивает всю функцию в одну
    транзакцию, а select_for_update() блокирует строку номера на время
    транзакции: второй параллельный запрос будет ждать, пока первый
    не завершится, и увидит уже актуальную занятость. На SQLite
    select_for_update() не блокирует построчно, но сама SQLite
    сериализует конкурентные записи, поэтому код корректен и здесь;
    на PostgreSQL блокировка строки работает в полной мере.
    """
    # Блокируем строку номера до конца транзакции — см. пояснение выше.
    room = Room.objects.select_for_update().get(pk=room.pk)

    validate_booking_dates(check_in, check_out)

    if guests < 1:
        raise ValidationError('Число гостей должно быть не меньше одного.')
    if guests > room.capacity:
        raise ValidationError(
            f'Номер вмещает не более {room.capacity} гост(я/ей).'
        )
    if not is_room_available(room, check_in, check_out):
        raise ValidationError('Номер уже забронирован на выбранные даты.')

    return Booking.objects.create(
        user=user,
        room=room,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        status='pending',
    )


def cancel_booking(booking: Booking) -> Booking:
    """
    Отменить бронь: перевести статус в 'cancelled', не удаляя запись
    (сохраняем историю). Повторная отмена уже отменённой брони —
    ошибка бизнес-правила.
    """
    if booking.status == 'cancelled':
        raise ValidationError('Эта бронь уже отменена.')
    booking.status = 'cancelled'
    booking.save(update_fields=['status'])
    return booking
