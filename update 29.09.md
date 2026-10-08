# HotelHub — исправления и Занятие 2 («Файлы и мультимедиа»)

Этот файл описывает, что было изменено в проекте относительно присланного
архива: исправленные ошибки из аудита, новые механизмы занятия 2 и —
самое важное для запуска — **куда положить картинки**, чтобы они сразу
появились на сайте.

Все изменения проверены: `python manage.py check` — чисто,
`python manage.py test` — **65 тестов, все зелёные** (было 51; добавлено 14
новых тестов на исправленные баги и на новые механизмы).

---

## 1. Что было исправлено (по нумерации из документа-аудита)

| № | Проблема | Файл | Как исправлено |
|---|---|---|---|
| 1 | Отмена брони работала через GET | `bookings/views.py` | `@require_POST` на `booking_cancel` |
| 2 | Открытый редирект через `?next=` | `users/views.py` | Проверка `url_has_allowed_host_and_scheme` |
| 3 | Гонка при параллельном бронировании | `bookings/services.py` | `transaction.atomic()` + `select_for_update()` |
| 5 | Выход выполнялся по GET-ссылке | `users/views.py`, `templates/includes/navbar.html`, `users/templates/users/profile.html` | `@require_POST`, ссылки заменены на POST-формы |
| 6 | Повторный `authenticate()` после валидной формы | `users/views.py` | Используется `form.get_user()` |
| 7 | `Hotel.rating` принимал любое число | `hotels/models.py` | `MinValueValidator`/`MaxValueValidator` + `CheckConstraint` в БД |
| 9 | Поле `avatar` было, а формы загрузки — нет | `users/forms.py`, `users/views.py`, новый шаблон `profile_edit.html` | Добавлена форма и страница редактирования профиля |
| 11 | Локальная БД отставала от миграций (3 непримененные) | — | `python manage.py migrate` — применены |
| 13 | `SECRET_KEY`/`DEBUG` захардкожены | `config/settings.py` | Берутся из переменных окружения, с учебным дефолтом |
| 15 | Дублирующая раздача `static()` | `config/urls.py` | Лишняя строка убрана |

**Не трогали намеренно** (не входит в Занятие 2, требует отдельных
занятий 1/3 по вашему же плану): №4 (`is_available` не привязан к датам),
№8 (нет пагинации), №10 (страницы 403/404/500), №12 (venv из архива —
просто пересоздайте на Python 3.12+, в архив он не включён), №14
(`Hotel.price` дублирует цены номеров).

---

## 2. Занятие 2 — что добавлено

### 2.1. Изображения отелей и номеров

- `Hotel.cover` (`hotels/models.py`) и `Room.image` (`rooms/models.py`) —
  обычные `ImageField` с валидацией расширения (`jpg/jpeg/png/webp`) и
  размера (не больше 5 МБ). Валидаторы — в `core/validators.py`, общие для
  всего проекта (аватар пользователя тоже мог бы их использовать).
- Миграции `hotels/migrations/0004_...` и `rooms/migrations/0003_room_image.py`
  уже применены к `db.sqlite3`.
- Шаблоны карточек (`hotels/_card.html`, `rooms/_card.html`) и страниц
  отеля/номера показывают картинку, если она есть, и заглушку
  `static/img/no-photo.svg`, если нет.
- В админке (`/admin/`) в списке отелей и номеров теперь видна миниатюра.
- Сигналы (`hotels/signals.py`, `rooms/signals.py`) удаляют файл с диска
  при удалении отеля/номера — без этого файлы оставались бы «сиротами».

### 2.2. КУДА ПОЛОЖИТЬ КАРТИНКИ (самое важное)

В сидерах уже прописаны пути для двух обложек отелей и одного фото номера —
достаточно **просто положить файл с точным именем в нужную папку**, без
захода в админку:

```
media/hotels/covers/demo/grand-astana.jpg   ← обложка отеля «Grand Astana»
media/hotels/covers/demo/almaty-plaza.jpg   ← обложка отеля «Almaty Plaza»
media/rooms/images/demo/single-room.jpg     ← фото одноместного номера в Grand Astana
```

Папки `media/...` нужно создать самостоятельно (`mkdir -p`) — Git не хранит
пустые папки, а сама папка `media/` в `.gitignore`. Имя и расширение файла
можно взять любое — тогда поправьте путь в:

- `hotels/management/commands/seed_hotels.py` → словарь `DEMO_COVERS`
- `rooms/management/commands/seed_rooms.py` → строка с `rooms/images/demo/...`

и перезапустите `python manage.py seed_hotels` / `seed_rooms` (сидеры
идемпотентны — повторный запуск не создаст дублей, только обновит путь).

**Для остальных отелей/номеров** — проще через админку: `/admin/` → «Отели»
или «Номера» → нужная запись → поле «Обложка»/«Фото номера» → обычная
загрузка файла через форму. Это и есть тот самый механизм `ImageField` +
`<input type="file">`, который показывает занятие 2.

### 2.3. Аватар пользователя

Поле `User.avatar` уже существовало, не хватало формы. Теперь:
`/users/profile/edit/` → загрузка аватара, email, телефона. Кнопка
«Редактировать профиль» — на странице `/users/profile/`.

### 2.4. Импорт/экспорт CSV (приложение `hotels`)

Простейший, но рабочий пример обоих направлений в одном приложении:

- **Экспорт** — кнопка «⬇ Экспорт CSV» на `/hotels/`, доступна всем.
  Код: `hotels/exports.py`.
- **Импорт** — кнопка «⬆ Импорт CSV» видна и доступна только персоналу
  (`is_staff` + право `hotels.add_hotel`); обычный посетитель получит 403.
  Код: `hotels/views.py::import_hotels_csv`, форма — `hotels/forms.py`.
  Формат файла: `name,city,address,price,rating` (первая строка — заголовок).
  Импорт атомарный: если хотя бы одна строка невалидна — не создаётся
  ни один отель (транзакция откатывается целиком).

Проверить импорт можно тестовым файлом:

```csv
name,city,address,price,rating
Kokshetau Hotel,Кокшетау,ул. Абая 5,21000,4.1
```

Зайдите под `admin` (создаётся сидером `seed_users`) → `/hotels/import/`.

---

## 3. Как запустить и проверить

```bash
python -m venv venv && source venv/bin/activate   # Python 3.12+
pip install -r requirements.txt
python manage.py migrate
python manage.py seed                              # демо-данные + пути к картинкам
mkdir -p media/hotels/covers/demo media/rooms/images/demo
# сюда положить свои jpg/png с указанными выше именами
python manage.py test                              # 65 тестов, все зелёные
python manage.py runserver
```

Админка: `/admin/` — логин `admin`, пароль `admin12345` (создаётся автоматически
сидером `seed_users`, см. `users/management/commands/seed_users.py`).

---

## 4. Занятие 1 «Данные и выборки» — проверка и реализация

По вашей просьбе проверил документ «Данные и выборки» на ошибки и реализовал
описанные в нём механизмы (их не было в присланном коде — были только в PDF
как образец).

### Найденные в документе ошибки

| Ошибка в документе | Почему это ошибка | Как исправлено |
|---|---|---|
| `RoomSearchForm.clean()`: `return cleaned_data` был вложен внутрь `if` | При КОРРЕКТНЫХ датах метод возвращал бы `None` вместо словаря — форма ломается именно в «счастливом» случае | `return` вынесен на уровень метода, тест `test_valid_dates_pass_validation` проверяет это явно |
| `Room.objects.filter(is_active=True)` | На реальной модели `Room` поля `is_active` нет — есть `is_available`. Код упал бы с `FieldError` | Использовано `is_available=True` |
| `order_by(sort_by)` со значениями `'price'/'-price'` | На модели цена называется `price_per_night`, а не `price` — тоже `FieldError` | Добавлен словарь `SORT_FIELDS`, сопоставляющий значения формы с реальными именами полей |
| Проверка занятости по датам без фильтра по статусу брони | Отменённая бронь (`status='cancelled'`) блокировала бы номер наравне с активной — клиент, отменивший бронь, никогда не увидел бы номер свободным на те же даты | `Room.objects.free_between()` фильтрует только по `ACTIVE_STATUSES` (`pending`, `confirmed`) — тот же список, что уже используется в `bookings/services.py` |
| Пагинация вручную: `?{{ request.GET.urlencode }}&page=N` | При уже существующем в адресе `?page=` получается два параметра `page` одновременно | Заменено на встроенный тег `{% querystring page=... %}` (Django 5.1+) |
| Шаблон использовал `room.image.url` без проверки `{% if %}` | Для номеров без фото — `ValueError` при рендере страницы | Используется уже существующий паттерн `{% if room.image %}...{% else %}заглушка{% endif %}` |

### Что добавлено в код

- `rooms/forms.py` — `RoomSearchForm` (даты + сортировка), с исправлениями выше.
- `rooms/models.py` — `RoomQuerySet.free_between()`, подключён как `Room.objects`.
- `rooms/views.py` — `room_list` заменён на `RoomListView` (CBV): старый поиск
  `?q=` сохранён (чтобы не сломать существующие тесты/страницы), плюс новые
  `check_in`/`check_out`/`sort_by`, плюс `paginate_by = 6`.
- `rooms/urls.py` — маршрут `''` теперь ведёт на `RoomListView.as_view()`
  (имя `room_list` не менялось — все `{% url 'rooms:room_list' %}` в шаблонах
  работают без изменений).
- `rooms/templates/rooms/list.html` — добавлены поля дат/сортировки и блок
  пагинации.
- `static/css/base.css` — стили `.input-group`, `.pagination`, `.flex-center`,
  `.current-page`.
- 21 новый тест в `rooms/tests.py`: форма (валидные/невалидные даты),
  `free_between` (в т.ч. про отменённую бронь), сортировка, интеграция
  поиска по датам во view, пагинация.

### Проверка config и urls — всё подключено

- `INSTALLED_APPS`: `core`, `users`, `hotels`, `rooms`, `bookings` — все на месте.
- `config/urls.py`: все 5 приложений подключены через `include()`, медиа
  раздаются в DEBUG-режиме.
- `hotels/urls.py`, `rooms/urls.py`: маршруты `export/`, `import/`,
  `RoomListView` корректно зарегистрированы и не конфликтуют с `<int:pk>/`.

**Итог: 77 тестов (было 51 в присланном архиве), все зелёные.**
