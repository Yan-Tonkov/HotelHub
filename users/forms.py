from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegisterForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.

    Наследуется от встроенной UserCreationForm, которая уже умеет:
    - показывать два поля пароля (password1 и password2),
    - проверять, что пароли совпадают,
    - прогонять пароль через валидаторы из settings.py.

    Стандартная форма «не знает» про наши новые поля (email, phone),
    поэтому мы переопределяем вложенный класс Meta и явно перечисляем,
    какие поля показывать и сохранять.
    """

    class Meta:
        model = User
        # Порядок полей в форме = порядок в этом кортеже.
        fields = ('username', 'email', 'phone', 'password1', 'password2')


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма редактирования профиля: только те поля, которые можно менять
    самостоятельно (без пароля и без username). avatar — обычный
    ImageField модели, Django сам подставит виджет загрузки файла
    (<input type="file">) и провалидирует его перед сохранением.
    """

    class Meta:
        model = User
        fields = ('email', 'phone', 'avatar')
