from rest_framework.routers import DefaultRouter
from .api_views import TaskViewSet, TimeLogViewSet

router = DefaultRouter()
router.register(r'time-logs', TimeLogViewSet, basename='timelog')
router.register(r'', TaskViewSet, basename='task')

urlpatterns = router.urls
