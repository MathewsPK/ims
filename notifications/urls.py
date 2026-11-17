from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('<int:pk>/read/', views.mark_notification_read, name='mark_read'),
    path('api/json/', views.notifications_json, name='notifications_json'),

    # Events
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/new/', views.EventCreateView.as_view(), name='event_create'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('events/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),

    # My Google Calendars (private, per-user)
    path('my-calendars/', views.my_calendars, name='my_calendars'),
    path('my-calendars/<int:pk>/delete/', views.my_calendar_delete, name='my_calendar_delete'),
    path('my-calendars/<int:pk>/sync/', views.my_calendar_sync, name='my_calendar_sync'),
]
