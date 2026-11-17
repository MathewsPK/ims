from django.urls import path

from . import views

app_name = 'tenders'

urlpatterns = [
    path('', views.home, name='home'),
    path('run/', views.start, name='start'),
    path('runs/<int:pk>/', views.run_detail, name='run_detail'),
    path('runs/<int:pk>/status/', views.run_status, name='run_status'),
]
