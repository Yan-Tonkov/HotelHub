# ────────────────────────────────────────────────────────────────────────────
# rooms/forms.py — форма поиска номеров (Занятие 1 «Данные и выборки»).
#
# Принимает даты заезда/выезда и вариант сортировки из GET-параметров,
# очищает их и защищает от логической ошибки (выезд раньше заезда) —
# ещё до того, как эти значения попадут в запрос к базе данных.
# ────────────────────────────────────────────────────────────────────────────
from django import forms


class RoomSearchForm(forms.Form):
    check_in = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Заезд',
    )
    check_out = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Выезд',
    )
    sort_by = forms.ChoiceField(
        choices=[('price', 'Сначала дешевле'), ('-price', 'Сначала дороже')],
        required=False,
        label='Сортировка',
    )

    def clean(self):
        """
        Межполевая проверка: обе даты вместе должны образовывать корректный
        интервал. Одна дата без другой — это неполный поиск, а не ошибка:
        оставляем такую комбинацию на усмотрение view (см. RoomListView —
        фильтр по датам применяется только если заполнены ОБЕ даты).

        В исходном примере занятия эта проверка была написана с неверным
        отступом: `return cleaned_data` стоял глубже, чем сам `if`, — при
        заполненных корректных датах метод возвращал бы None вместо
        словаря очищенных данных, и Django-форма падала бы с ошибкой
        "cleaned_data becomes None". Здесь `return` вынесен на уровень
        метода и выполняется всегда, а не только внутри чужого блока.
        """
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')

        if check_in and check_out and check_in >= check_out:
            raise forms.ValidationError('Дата выезда должна быть позже даты заезда.')

        return cleaned_data
