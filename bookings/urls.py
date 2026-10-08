from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.booking_list, name='list'),
    path('create/<int:room_id>/', views.booking_create, name='create'),
    path('cancel/<int:pk>/', views.booking_cancel, name='cancel'),
]
