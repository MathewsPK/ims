from rest_framework import serializers, viewsets, permissions
from rest_framework.routers import DefaultRouter
from .models import AMCReport, ReportImage


class ReportImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportImage
        fields = ('id', 'image', 'caption', 'uploaded_at')


class AMCReportSerializer(serializers.ModelSerializer):
    images = ReportImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    engineer_name = serializers.CharField(source='engineer.name', read_only=True)

    class Meta:
        model = AMCReport
        fields = ('id', 'engineer', 'engineer_name', 'project', 'amc_project',
                  'date', 'work_done', 'issues_found', 'recommendations',
                  'status', 'status_display', 'images', 'reviewed_by',
                  'reviewed_at', 'review_note', 'created_at')
        read_only_fields = ('id', 'engineer', 'reviewed_by', 'reviewed_at', 'created_at')


class AMCReportViewSet(viewsets.ModelViewSet):
    serializer_class = AMCReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'project', 'engineer']
    search_fields = ['work_done', 'issues_found']
    ordering_fields = ['date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = AMCReport.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(engineer=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(engineer=self.request.user)


router = DefaultRouter()
router.register(r'', AMCReportViewSet, basename='amcreport')
urlpatterns = router.urls

