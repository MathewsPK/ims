from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.TaskListView.as_view(), name='task_list'),
    path('new/', views.TaskCreateView.as_view(), name='task_create'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('calendar/ical/', views.ical_feed, name='ical_feed'),
    path('workload/', views.workload_view, name='workload'),
    path('out-of-office/', views.out_of_office_list, name='out_of_office_list'),
    path('out-of-office/new/', views.out_of_office_create, name='out_of_office_create'),
    path('out-of-office/<int:pk>/delete/', views.out_of_office_delete, name='out_of_office_delete'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_update'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('<int:pk>/log-time/', views.log_time, name='log_time'),
]
