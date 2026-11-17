from rest_framework import viewsets, permissions
from .models import Project, ProjectMedia
from .serializers import ProjectSerializer, ProjectMediaSerializer


class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return (
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.role in ('ADMIN', 'MANAGER'))
        )


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsManagerOrAdmin]
    filterset_fields = ['status', 'client']
    search_fields = ['name', 'client', 'location', 'description']
    ordering_fields = ['start_date', 'end_date', 'name', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.all()
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(assigned_users=user)
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
