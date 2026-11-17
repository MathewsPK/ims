from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from users.models import User
from .models import Project, ProjectMedia


class ProjectResource(resources.ModelResource):
    created_by = fields.Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, field='email'),
    )
    assigned_users = fields.Field(
        column_name='assigned_users',
        attribute='assigned_users',
        widget=ManyToManyWidget(User, field='email', separator='; '),
    )

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'client', 'location', 'status',
            'start_date', 'end_date', 'description',
            'created_by', 'assigned_users',
            'created_at', 'updated_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


class ProjectMediaInline(admin.TabularInline):
    model = ProjectMedia
    extra = 0


@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    resource_classes = [ProjectResource]
    list_display = ('name', 'client', 'location', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'client', 'location')
    filter_horizontal = ('assigned_users',)
    inlines = [ProjectMediaInline]


@admin.register(ProjectMedia)
class ProjectMediaAdmin(ImportExportModelAdmin):
    list_display = ('project', 'caption', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
