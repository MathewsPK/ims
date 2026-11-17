from rest_framework import serializers
from .models import Notification, NotificationEvent


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'message', 'category', 'link', 'is_read', 'created_at')
        read_only_fields = ('id', 'created_at')


class NotificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = ('id', 'title', 'description', 'event_type', 'event_datetime',
                  'location', 'assigned_to', 'all_users', 'created_by', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_at')
