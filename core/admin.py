from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from users.models import User
from .models import ActivityLog, AuditLog, Holiday


class ActivityLogResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = ActivityLog
        fields = (
            'id', 'timestamp', 'user', 'action', 'description',
            'content_type', 'object_id',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


class AuditLogResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = AuditLog
        fields = (
            'id', 'timestamp', 'user', 'action', 'model_name',
            'object_id', 'ip_address', 'user_agent', 'changes',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


@admin.register(ActivityLog)
class ActivityLogAdmin(ImportExportModelAdmin):
    resource_classes = [ActivityLogResource]
    list_display = ('timestamp', 'user', 'action', 'description', 'content_type')
    list_filter = ('action', 'content_type', 'timestamp')
    search_fields = ('description', 'user__email', 'user__name')
    readonly_fields = ('timestamp',)


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'region')
    list_filter = ('region', 'date')
    search_fields = ('name',)
    date_hierarchy = 'date'


@admin.register(AuditLog)
class AuditLogAdmin(ImportExportModelAdmin):
    resource_classes = [AuditLogResource]
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('action', 'model_name', 'user__email')
    readonly_fields = ('timestamp',)
