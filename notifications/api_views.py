from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, NotificationEvent
from .serializers import NotificationSerializer, NotificationEventSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.mark_read()
        return Response({'status': 'ok'})


class NotificationEventViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        user = self.request.user
        qs = NotificationEvent.objects.all()
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(Q(all_users=True) | Q(assigned_to=user))
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
