from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Кастомная модель пользователя HotelHub.

    Мы наследуемся от AbstractUser, а не пишем пользователя с нуля.
    Благодаря этому сохраняются все системные механизмы Django:
    хэширование паролей, проверка прав, поля username / email / password,
    is_staff, is_active и т.д. Мы лишь ДОБАВЛЯЕМ два своих поля.

    Модель подключается в settings.py через AUTH_USER_MODEL = 'users.User'.
    Важно: кастомную модель заводят на старте проекта, чтобы потом не
    переделывать уже созданную базу.
    """

    # Телефон необязателен: blank=True — можно не заполнять в форме,
    # null=True — в базе допускается значение NULL (пустой телефон).
    phone = models.CharField(
        'Телефон',
        max_length=20,
        blank=True,
        null=True,
    )

    # Аватар — загружаемая картинка. Файлы попадут в MEDIA_ROOT/users/avatars/.
    # ImageField требует установленной библиотеки Pillow (см. requirements.txt).
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        # То, что показывается в админке и в шаблонах при {{ user }}.
        return self.username
