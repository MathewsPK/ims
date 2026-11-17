from rest_framework import serializers
from .models import Project, ProjectMedia


class ProjectMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMedia
        fields = ('id', 'image', 'caption', 'uploaded_at')


class ProjectSerializer(serializers.ModelSerializer):
    media = ProjectMediaSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'client', 'location', 'description',
                  'start_date', 'end_date', 'status', 'status_display',
                  'assigned_users', 'created_by', 'media', 'progress_percent',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
