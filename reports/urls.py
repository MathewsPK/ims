from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportListView.as_view(), name='report_list'),
    path('new/', views.ReportCreateView.as_view(), name='report_create'),
    path('<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('<int:pk>/edit/', views.ReportUpdateView.as_view(), name='report_update'),
    path('<int:pk>/review/', views.review_report, name='report_review'),

    # Installation Log
    path('installations/', views.InstallationListView.as_view(), name='installation_list'),
    path('installations/new/', views.InstallationCreateView.as_view(), name='installation_create'),
    path('installations/<int:pk>/', views.InstallationDetailView.as_view(), name='installation_detail'),
    path('installations/<int:pk>/edit/', views.InstallationUpdateView.as_view(), name='installation_update'),
    path('installations/<int:pk>/delete/', views.InstallationDeleteView.as_view(), name='installation_delete'),
]
