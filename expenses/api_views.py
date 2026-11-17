from rest_framework import serializers, viewsets, permissions
from rest_framework.routers import DefaultRouter
from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_approval_status_display', read_only=True)

    class Meta:
        model = Expense
        fields = ('id', 'user', 'user_name', 'project', 'date', 'amount',
                  'category', 'category_display', 'description', 'receipt',
                  'approval_status', 'status_display', 'reviewed_by',
                  'reviewed_at', 'review_note', 'created_at')
        read_only_fields = ('id', 'user', 'reviewed_by', 'reviewed_at', 'created_at')


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['category', 'approval_status', 'date', 'project']
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


router = DefaultRouter()
router.register(r'', ExpenseViewSet, basename='expense')
urlpatterns = router.urls
