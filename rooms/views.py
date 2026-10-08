from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from .models import Room
from .forms import RoomSearchForm

# Ключи формы ('price'/'-price') → реальные имена полей модели.
# В документе занятия 1 форма сортировала по полю 'price', которого нет
# на модели Room (цена называется price_per_night) — при прямой передаче
# в order_by('price') Django упал бы с FieldError. Соответствие полей
# держим в одном месте, а не угадываем строку на лету.
SORT_FIELDS = {
    'price': 'price_per_night',
    '-price': '-price_per_night',
}


class RoomListView(ListView):
    """
    Список номеров: старый текстовый поиск (?q=) по названию отеля/типу
    номера — плюс новый структурированный поиск по датам и сортировка
    (Занятие 1 «Данные и выборки»), с постраничным выводом.
    """
    model = Room
    template_name = 'rooms/list.html'
    context_object_name = 'rooms'
    paginate_by = 6

    def get_queryset(self):
        # on_sale() = «выставлен на продажу» (бывший прямой filter(is_available=True)).
        # with_today_status() добавляет occupied_today для бейджа в карточке —
        # без него карточка не может отличить «свободен» от «занят сегодня»
        # (аудит, дефект №4). free_between() ниже — отдельная, более точная
        # проверка по выбранному интервалу дат, когда он задан.
        queryset = Room.objects.on_sale().with_today_status().select_related('hotel')

        # --- старый текстовый поиск по названию отеля / типу номера ---
        query = self.request.GET.get('q', '')
        if query:
            matching_types = [
                code for code, label in Room.ROOM_TYPES
                if query.lower() in label.lower()
            ]
            queryset = queryset.annotate(hotel_name_lower=Lower('hotel__name')).filter(
                Q(hotel_name_lower__contains=query.lower())
                | Q(room_type__in=matching_types)
            )

        # --- новый поиск по датам + сортировка ---
        form = RoomSearchForm(self.request.GET)
        sort_field = 'price_per_night'  # сортировка по умолчанию: сначала дешевле
        if form.is_valid():
            check_in = form.cleaned_data.get('check_in')
            check_out = form.cleaned_data.get('check_out')
            sort_by = form.cleaned_data.get('sort_by')

            # Фильтруем по занятости, только если обе даты заполнены —
            # частично заполненная форма не должна ломать обычный список.
            if check_in and check_out:
                queryset = queryset.free_between(check_in, check_out)

            if sort_by in SORT_FIELDS:
                sort_field = SORT_FIELDS[sort_by]

        return queryset.order_by(sort_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Форма возвращается в шаблон, чтобы даты и сортировка оставались
        # заполненными после отправки (иначе поля обнулялись бы на экране).
        context['form'] = RoomSearchForm(self.request.GET)
        context['query'] = self.request.GET.get('q', '')
        return context


def room_detail(request, pk):
    """Страница одного номера с кнопкой бронирования."""
    # with_today_status() — тот же бейдж «Свободен сейчас/Занят сейчас»,
    # что и в карточках списка (аудит, дефект №4); без аннотации тут
    # не было бы room.occupied_today для шаблона.
    room = get_object_or_404(Room.objects.with_today_status(), pk=pk)
    return render(request, 'rooms/detail.html', {'room': room})
