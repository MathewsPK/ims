from rest_framework import serializers
from .models import Task, TimeLog


class TimeLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = TimeLog
        fields = ('id', 'task', 'user', 'user_name', 'hours', 'date', 'notes', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    time_logs = TimeLogSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'assigned_to', 'assigned_to_name',
                  'project', 'project_name', 'start_date', 'end_date',
                  'status', 'status_display', 'priority', 'priority_display',
                  'is_overdue', 'time_logs', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
