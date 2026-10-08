from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import UserRegisterForm, ProfileUpdateForm


def register_view(request):
    """
    Регистрация пользователя. Контроллер обрабатывает два типа запросов:

    GET  — просто показать пустую форму регистрации.
    POST — принять заполненные данные, проверить их и, если всё верно,
           создать пользователя и сразу же залогинить его (чтобы человек
           не вводил логин/пароль второй раз).
    """
    if request.method == 'POST':
        # Наполняем форму данными из запроса.
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # form.save() создаёт пользователя и хэширует пароль.
            user = form.save()
            # Мгновенный вход: кладём пользователя в текущую сессию.
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно. Добро пожаловать!')
            return redirect('users:profile')
    else:
        # GET — отдаём пустую форму.
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    """
    Вход пользователя.

    Для входа нужны только логин и пароль, поэтому используем встроенную
    AuthenticationForm без переопределения. Форма сама вызывает
    authenticate() внутри is_valid() — второй, повторный вызов
    authenticate() был лишним дублированием (аудит, дефект №6): пару
    логин/пароль форма уже проверила, поэтому просто забираем
    готового пользователя через form.get_user().
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()  # форма уже выполнила authenticate()
            login(request, user)
            messages.success(request, f'Вы вошли как {user.username}.')

            # Если пользователя перекинуло на вход с закрытой страницы,
            # вернём его обратно через параметр ?next=... Но редиректить
            # можно только на свой же сайт: без проверки это открытый
            # редирект (аудит, дефект №2) — параметром next= можно было
            # увести вошедшего пользователя на сторонний фишинговый сайт.
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('users:profile')
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def logout_view(request):
    """
    Выход: очищаем сессию и возвращаем на главную (см. LOGOUT_REDIRECT_URL).

    Только POST (аудит, дефект №5): выход — действие, меняющее состояние
    (завершает сессию), поэтому его нельзя вызывать обычной GET-ссылкой —
    иначе достаточно <img src="/users/logout/"> на чужой странице, чтобы
    разлогинить вошедшего пользователя. Ссылки «Выйти» в шаблонах теперь
    оформлены как маленькие POST-формы.
    """
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта.')
    return redirect('core:home')


@login_required
def profile_edit_view(request):
    """
    Редактирование профиля: email, телефон и аватар.

    Поле User.avatar (ImageField) в модели уже было — не хватало формы
    загрузки (аудит, дефект №9). enctype='multipart/form-data' в шаблоне
    обязателен: без него браузер не передаст файл в request.FILES.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён.')
            return redirect('users:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def profile_view(request):
    """
    Личный кабинет. Декоратор @login_required пускает сюда только
    авторизованных пользователей — гостя перенаправит на страницу входа.

    Данные текущего пользователя всегда доступны через request.user,
    поэтому дополнительно ничего запрашивать из базы не нужно.
    """
    # Бронирования пользователя показываем прямо в кабинете (связь из bookings).
    bookings = request.user.bookings.select_related('room', 'room__hotel').all()
    return render(request, 'users/profile.html', {
        'profile_user': request.user,
        'bookings': bookings,
    })
