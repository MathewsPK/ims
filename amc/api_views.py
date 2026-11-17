from rest_framework import serializers, viewsets, permissions
from rest_framework.routers import DefaultRouter
from .models import AMCProject, Equipment


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ('id', 'amc_project', 'name', 'serial_number', 'brand',
                  'model_number', 'installation_date', 'warranty_expiry',
                  'amc_date', 'notes', 'warranty_days_left', 'created_at')
        read_only_fields = ('id', 'warranty_days_left', 'created_at')


class AMCProjectSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_to_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = AMCProject
        fields = ('id', 'project', 'project_name', 'contract_number',
                  'amc_start_date', 'amc_end_date', 'contract_value', 'notes',
                  'equipment', 'is_active', 'days_to_expiry', 'is_expiring_soon',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class AMCProjectViewSet(viewsets.ModelViewSet):
    queryset = AMCProject.objects.all()
    serializer_class = AMCProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['project']
    search_fields = ['project__name', 'contract_number']
    ordering_fields = ['amc_end_date', 'created_at']


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['amc_project', 'brand']
    search_fields = ['name', 'serial_number', 'brand']


router = DefaultRouter()
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'', AMCProjectViewSet, basename='amcproject')
urlpatterns = router.urls

