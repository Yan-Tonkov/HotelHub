from django.conf import settings
from django.db import models
from rooms.models import Room


class Booking(models.Model):
    """
    Бронирование номера пользователем.

    Модель связывает три вещи: КТО бронирует (user), ЧТО бронирует (room)
    и НА КАКОЙ срок (check_in / check_out). Именно ради этой связи приложение
    users проектировалось заранее — система должна знать, какой пользователь
    совершает бронирование.
    """

    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
    ]

    # Кто забронировал. settings.AUTH_USER_MODEL = 'users.User'.
    # related_name='bookings' даёт удобный доступ: user.bookings.all().
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Гость',
    )

    # Какой номер забронирован. related_name='bookings' -> room.bookings.all().
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Номер',
    )

    check_in = models.DateField('Дата заезда')
    check_out = models.DateField('Дата выезда')

    guests = models.PositiveIntegerField('Количество гостей', default=1)

    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']
        # Ограничения и индексы уровня БАЗЫ ДАННЫХ — надёжнее проверок в Python,
        # потому что действуют всегда, даже при записи в обход форм и сервисов.
        constraints = [
            # Выезд обязан быть строго позже заезда — гарантия на уровне СУБД.
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F('check_in')),
                name='booking_checkout_after_checkin',
            ),
            # Число гостей не может быть нулевым.
            models.CheckConstraint(
                condition=models.Q(guests__gte=1),
                name='booking_guests_positive',
            ),
        ]
        indexes = [
            # Ускоряет самый частый запрос — «брони этого пользователя».
            models.Index(fields=['user', '-created_at'], name='booking_user_created_idx'),
            # Ускоряет проверку занятости номера на даты (см. services).
            models.Index(fields=['room', 'status'], name='booking_room_status_idx'),
        ]

    def __str__(self):
        return f'Бронь №{self.pk} — {self.room} ({self.user})'

    @property
    def nights(self):
        """Сколько ночей длится бронь — разница между выездом и заездом."""
        return (self.check_out - self.check_in).days

    @property
    def total_price(self):
        """
        Итоговая стоимость = цена номера за ночь × число ночей.
        Считается на лету, в базе не хранится, чтобы всегда быть актуальной.
        """
        nights = self.nights
        if nights < 0:
            nights = 0
        return self.room.price_per_night * nights
