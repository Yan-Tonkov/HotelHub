from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Min

from core.validators import ALLOWED_IMAGE_EXTENSIONS, validate_image_size


class HotelQuerySet(models.QuerySet):
    """
    Собственный QuerySet модели Hotel (добавлен при аудите — приводит
    hotels в соответствие с тем, что уже сделано в rooms на Занятии 1:
    собственный менеджер, агрегаты, сортировка списком, а не вручную
    в каждом view).
    """

    def active(self):
        """Только активные отели — то же самое, что раньше писали как
        filter(is_active=True) прямо во view каждый раз."""
        return self.filter(is_active=True)

    def with_stats(self):
        """
        Добавляет каждому отелю в выборке две аннотации:
          • min_price — минимальная цена среди его номеров (или None,
            если номеров ещё нет);
          • rooms_count — число номеров отеля.

        Зачем. У Hotel есть собственное поле price, но оно не обязано
        совпадать с ценами конкретных номеров отеля (аудит, дефект №14) —
        это два разных числа, которые легко разойдутся при редактировании.
        min_price, посчитанный агрегатом по реальным номерам, — честная
        цена «от», которую видит пользователь в каталоге и на странице
        отеля; Hotel.price остаётся как служебное поле (например, для
        сортировки каталога до того, как у отеля появятся номера).
        """
        return self.annotate(
            min_price=Min('rooms__price_per_night'),
            rooms_count=Count('rooms', distinct=True),
        )


def hotel_cover_path(instance, filename):
    """
    Путь для обложки отеля: media/hotels/covers/<id_отеля>/<имя_файла>.

    upload_to может быть функцией: Django вызывает её при каждом сохранении
    файла и подставляет результат как относительный путь внутри MEDIA_ROOT.
    Группировка по instance.pk удобна для навигации на диске и исключает
    конфликт имён файлов у разных отелей.
    """
    return f'hotels/covers/{instance.pk or "new"}/{filename}'


class Hotel(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)
    # цена за одну ночь проживания, например 999.99
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Рейтинг по 5-балльной шкале. Раньше поле принимало любое число
    # (например, 17.5 в админке, см. аудит, дефект №7) — валидаторы
    # проверяют значение в формах и в админке, а CheckConstraint в Meta
    # страхует и прямую запись в БД в обход форм.
    rating = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ---- Занятие 2: обложка отеля -----------------------------------------
    # blank=True/null=True — поле необязательно: старые отели без фото не
    # ломают сайт, в шаблоне для них показывается заглушка-плейсхолдер.
    cover = models.ImageField(
        'Обложка',
        upload_to=hotel_cover_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
        ],
        help_text='JPG/PNG/WEBP, не более 5 МБ.',
    )

    # Подключаем HotelQuerySet как менеджер: Hotel.objects.active().with_stats()
    # работает напрямую, без промежуточного .all() (как и в rooms/models.py).
    objects = HotelQuerySet.as_manager()

    class Meta:
        verbose_name = 'Отель'
        verbose_name_plural = 'Отели'
        ordering = ['-created_at']
        indexes = [
            # Поиск отелей по городу — самый частый фильтр на витрине.
            models.Index(fields=['city'], name='hotel_city_idx'),
            # Сортировка/фильтрация активных отелей по рейтингу.
            models.Index(fields=['is_active', '-rating'], name='hotel_active_rating_idx'),
        ]
        constraints = [
            # Страхует рейтинг на уровне БД, даже если запись обошла форму
            # и валидаторы модели (например, прямой INSERT или старый код).
            models.CheckConstraint(
                condition=models.Q(rating__gte=0) & models.Q(rating__lte=5),
                name='hotel_rating_between_0_and_5',
            ),
        ]

    def __str__(self):
        return self.name
