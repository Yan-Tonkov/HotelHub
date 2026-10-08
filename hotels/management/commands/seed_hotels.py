# ────────────────────────────────────────────────────────────────────────────
# hotels/management/commands/seed_hotels.py
# Наполняет базу демонстрационными ОТЕЛЯМИ.
#
# Запуск:  python manage.py seed_hotels
# Идемпотентна: get_or_create по названию отеля не плодит дубли.
# ────────────────────────────────────────────────────────────────────────────

from django.core.management.base import BaseCommand
from hotels.models import Hotel

# Заготовки отелей: (название, город, адрес, цена за ночь, рейтинг, описание).
HOTELS = [
    ('Grand Astana', 'Астана', 'пр. Кабанбай батыра, 12', 45000, 4.7,
     'Пятизвёздочный отель в центре столицы с панорамным видом на Байтерек.'),
    ('Almaty Plaza', 'Алматы', 'ул. Достык, 85', 38000, 4.5,
     'Современный отель у подножия гор, в шаговой доступности от парков.'),
    ('Caspian Resort', 'Актау', 'мкр. 15, дом 4', 52000, 4.8,
     'Курортный комплекс на берегу Каспийского моря с собственным пляжем.'),
    ('Shymkent City', 'Шымкент', 'пр. Тауке хана, 21', 27000, 4.2,
     'Уютный городской отель для деловых поездок и туризма.'),
    ('Turkistan Palace', 'Туркестан', 'ул. Айтеке би, 7', 33000, 4.6,
     'Отель рядом с мавзолеем Ходжи Ахмеда Ясави, восточный колорит.'),
    ('Karaganda Central', 'Караганда', 'пр. Бухар жырау, 40', 24000, 4.0,
     'Классический городской отель в деловом центре Караганды.'),
]

# ────────────────────────────────────────────────────────────────────────────
# ЗАГОТОВКА ДЛЯ ЗАНЯТИЯ 2 («Файлы и мультимедиа»).
#
# Для первых двух отелей сидер заранее прописывает путь к файлу обложки —
# даже если самого файла ещё нет на диске. Как только вы положите файл
# с ТОЧНО таким именем в указанную папку (внутри media/), обложка сразу
# появится на сайте — без похода в админку.
#
#   media/hotels/covers/demo/grand-astana.jpg   ← обложка для Grand Astana
#   media/hotels/covers/demo/almaty-plaza.jpg   ← обложка для Almaty Plaza
#
# Папку hotels/covers/demo/ нужно создать самостоятельно (mkdir -p) —
# Git и .gitignore не хранят пустые папки и содержимое media/.
# Имя файла и расширение можно взять любое (jpg/jpeg/png/webp) — просто
# поправьте путь ниже на своё.
#
# Если хотите загрузить обложку и для остальных отелей — не обязательно
# трогать сидер: откройте /admin/, раздел «Отели» → нужный отель → поле
# «Обложка» → обычная загрузка файла через форму.
DEMO_COVERS = {
    'Grand Astana': 'hotels/covers/demo/grand-astana.jpg',
    'Almaty Plaza': 'hotels/covers/demo/almaty-plaza.jpg',
}


class Command(BaseCommand):
    help = 'Создаёт демонстрационные отели.'

    def handle(self, *args, **options):
        # verbosity=0 (например, из тестов) — работаем молча.
        verbose = options.get('verbosity', 1) >= 1
        def say(msg):
            if verbose:
                self.stdout.write(msg)
        say('Создаю отели...')
        created_count = 0

        for name, city, address, price, rating, desc in HOTELS:
            hotel, created = Hotel.objects.get_or_create(
                name=name,  # ключ поиска — чтобы не дублировать при повторе
                defaults={
                    'city': city, 'address': address, 'price': price,
                    'rating': rating, 'description': desc, 'is_active': True,
                },
            )
            if created:
                created_count += 1
                say(f'  + {name} ({city})')

            # Заготовка пути к обложке (см. DEMO_COVERS выше) — прописываем,
            # даже если файла ещё нет на диске: как только он появится
            # по нужному пути, картинка отобразится сама, без пересидирования.
            demo_path = DEMO_COVERS.get(name)
            if demo_path and not hotel.cover:
                hotel.cover.name = demo_path
                hotel.save(update_fields=['cover'])

        say(self.style.SUCCESS(
            f'Готово. Создано новых: {created_count}. '
            f'Всего отелей: {Hotel.objects.count()}'
        ))
