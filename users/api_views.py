from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, UserCreateSerializer


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.is_superuser or request.user.role == 'ADMIN'))


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'name', 'phone']
    ordering_fields = ['date_joined', 'name', 'email']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRole()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
