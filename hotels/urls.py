from django.urls import path
from . import views
from .exports import export_hotels_csv, export_hotels_xlsx, export_hotels_pdf, export_hotels_docx

app_name = 'hotels'

urlpatterns = [
    path('', views.HotelListView.as_view(), name='hotel_list'),

    # Экспорт каталога в четырёх форматах — см. hotels/exports.py.
    path('export/csv/', export_hotels_csv, name='export_csv'),
    path('export/xlsx/', export_hotels_xlsx, name='export_xlsx'),
    path('export/pdf/', export_hotels_pdf, name='export_pdf'),
    path('export/docx/', export_hotels_docx, name='export_docx'),

    path('import/', views.import_hotels, name='import_hotels'),
    path('<int:pk>/', views.hotel_detail, name='hotel_detail'),
]
