from django.shortcuts import render

# Create your views here.
#
# from django.http import HttpResponse
#
# def hotel_list(request):
#     return HttpResponse('Список отелей работает')

from django.shortcuts import render
from .models import Hotel

def hotel_list(request):
    city = request.GET.get('city')
    hotels = Hotel.objects.all() #SELECT * FROM hotels

    # Фильтрация по городу
    if city:
        hotels = hotels.filter(city__icontains=city)
        #Астана, астана, АСТАНА

    return render(request, 'hotels/list.html', {
        'hotels':hotels
    })