from django.shortcuts import render
from .models import Hotel


def hotel_list(request):
    city = request.GET.get('city', '')
    hotels = Hotel.objects.all()  # SELECT * FROM hotels

    # Фильтрация по городу: Астана, астана, АСТАНА — без учёта регистра
    if city:
        hotels = hotels.filter(city__icontains=city)

    return render(request, 'hotels/list.html', {
        'hotels': hotels,
        'city': city,
    })
