from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Регистрируем кастомного пользователя в админке.

    Наследуемся от стандартного UserAdmin, чтобы сохранить удобные экраны
    смены пароля и управления правами, и добавляем наши поля phone/avatar
    в список и в форму редактирования.
    """
    list_display = ('username', 'email', 'phone', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')

    # Добавляем блок с нашими полями к стандартным наборам полей формы.
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('phone', 'avatar')}),
    )
