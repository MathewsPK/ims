from django.urls import path
from . import views

app_name = 'amc'

urlpatterns = [
    path('', views.AMCListView.as_view(), name='amc_list'),
    path('new/', views.AMCCreateView.as_view(), name='amc_create'),
    path('import-csv/', views.import_csv_view, name='import_csv'),
    path('<int:pk>/', views.AMCDetailView.as_view(), name='amc_detail'),
    path('<int:pk>/edit/', views.AMCUpdateView.as_view(), name='amc_update'),
    path('<int:pk>/delete/', views.AMCDeleteView.as_view(), name='amc_delete'),
    path('equipment/new/', views.EquipmentCreateView.as_view(), name='equipment_create'),
    path('equipment/<int:pk>/', views.EquipmentDetailView.as_view(), name='equipment_detail'),
    path('equipment/<int:pk>/edit/', views.EquipmentUpdateView.as_view(), name='equipment_update'),
    path('equipment/<int:pk>/delete/', views.EquipmentDeleteView.as_view(), name='equipment_delete'),
]
