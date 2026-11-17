from rest_framework.routers import DefaultRouter
from .api_views import NotificationViewSet, NotificationEventViewSet

router = DefaultRouter()
router.register(r'events', NotificationEventViewSet, basename='event')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = router.urls
