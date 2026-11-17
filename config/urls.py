"""
IMS URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
)

urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('admin/', admin.site.urls),

    # Web (template) URLs
    path('users/', include('users.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('projects/', include('projects.urls')),
    path('tasks/', include('tasks.urls')),
    path('amc/', include('amc.urls')),
    path('expenses/', include('expenses.urls')),
    path('billing/', include('billing.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),

    # REST API URLs
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', include('users.api_urls')),
    path('api/projects/', include('projects.api_urls')),
    path('api/tasks/', include('tasks.api_urls')),
    path('api/amc/', include('amc.api_urls')),
    path('api/expenses/', include('expenses.api_urls')),
    path('api/reports/', include('reports.api_urls')),
    path('api/notifications/', include('notifications.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
