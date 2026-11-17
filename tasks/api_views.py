from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import Task, TimeLog
from .serializers import TaskSerializer, TimeLogSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    filterset_fields = ['status', 'priority', 'assigned_to', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['end_date', 'priority', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.all()
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(Q(assigned_to=user) | Q(project__assigned_users=user))
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TimeLogViewSet(viewsets.ModelViewSet):
    serializer_class = TimeLogSerializer
    filterset_fields = ['task', 'user', 'date']

    def get_queryset(self):
        user = self.request.user
        qs = TimeLog.objects.all()
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
