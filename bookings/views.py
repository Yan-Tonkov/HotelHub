from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from rooms.models import Room
from .models import Booking
from .forms import BookingForm
from . import services


@login_required
def booking_list(request):
    """
    Список бронирований текущего пользователя.

    Декоратор @login_required пускает только авторизованных: бронь всегда
    привязана к конкретному пользователю. Фильтруем по request.user, чтобы
    человек видел только свои брони.
    """
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('room', 'room__hotel')  # чтобы не делать лишние запросы
    )
    return render(request, 'bookings/list.html', {'bookings': bookings})


@login_required
def booking_create(request, room_id):
    """
    Создание брони на конкретный номер.

    room_id приходит из URL. GET показывает форму с предустановленным номером,
    POST — проверяет данные формой, затем передаёт их в СЕРВИСНЫЙ СЛОЙ
    (services.create_booking), где живут бизнес-правила: проверка дат,
    вместимости и занятости номера. View остаётся «тонким».
    """
    room = get_object_or_404(Room, pk=room_id)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                # Вся бизнес-логика — в сервисе. View только связывает
                # проверенные данные формы с текущим пользователем.
                services.create_booking(
                    user=request.user,
                    room=room,
                    check_in=form.cleaned_data['check_in'],
                    check_out=form.cleaned_data['check_out'],
                    guests=form.cleaned_data['guests'],
                )
            except ValidationError as exc:
                # Ошибку бизнес-правила показываем прямо в форме.
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, 'Номер забронирован! Проверьте бронь в кабинете.')
                return redirect('bookings:list')
    else:
        # Предзаполняем скрытое поле room выбранным номером.
        form = BookingForm(initial={'room': room})

    return render(request, 'bookings/create.html', {'form': form, 'room': room})


@login_required
@require_POST
def booking_cancel(request, pk):
    """
    Отмена брони. Логика смены статуса — в сервисе cancel_booking.
    Отменять можно только собственную бронь (фильтр user=request.user).

    Только POST (аудит, дефект №1): отмена меняет состояние брони, поэтому
    её нельзя вызвать обычной GET-ссылкой или картинкой со стороннего
    сайта — раньше GET /bookings/cancel/<id>/ отменял бронь напрямую.
    """
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        services.cancel_booking(booking)
        messages.info(request, f'Бронь №{booking.pk} отменена.')
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect('bookings:list')
