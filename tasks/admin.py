from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from users.models import User
from projects.models import Project
from .models import Task, TimeLog, OutOfOffice


class TaskResource(resources.ModelResource):
    assigned_to = fields.Field(
        column_name='assigned_to',
        attribute='assigned_to',
        widget=ForeignKeyWidget(User, field='email'),
    )
    project = fields.Field(
        column_name='project',
        attribute='project',
        widget=ForeignKeyWidget(Project, field='name'),
    )
    created_by = fields.Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'assigned_to',
            'status', 'priority', 'start_date', 'end_date',
            'created_by', 'created_at', 'updated_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


class TimeLogResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='email'),
    )
    task = fields.Field(
        column_name='task',
        attribute='task',
        widget=ForeignKeyWidget(Task, field='title'),
    )

    class Meta:
        model = TimeLog
        fields = ('id', 'task', 'user', 'hours', 'date', 'notes', 'created_at')
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


@admin.register(Task)
class TaskAdmin(ImportExportModelAdmin):
    resource_classes = [TaskResource]
    list_display = ('title', 'assigned_to', 'project', 'status', 'priority', 'start_date', 'end_date')
    list_filter = ('status', 'priority', 'start_date')
    search_fields = ('title', 'description')


@admin.register(TimeLog)
class TimeLogAdmin(ImportExportModelAdmin):
    resource_classes = [TimeLogResource]
    list_display = ('task', 'user', 'hours', 'date')
    list_filter = ('date', 'user')


@admin.register(OutOfOffice)
class OutOfOfficeAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'reason', 'created_by')
    list_filter = ('start_date',)
    search_fields = ('user__name', 'user__email', 'reason')
