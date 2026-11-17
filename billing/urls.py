from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('new/', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    path('<int:pk>/', views.SubscriptionDetailView.as_view(), name='subscription_detail'),
    path('<int:pk>/edit/', views.SubscriptionUpdateView.as_view(), name='subscription_update'),
    path('<int:pk>/delete/', views.SubscriptionDeleteView.as_view(), name='subscription_delete'),
    path('<int:pk>/mark-paid/', views.mark_subscription_paid, name='subscription_mark_paid'),
    path('cron/check-renewals/', views.cron_check_renewals, name='cron_check_renewals'),
]
