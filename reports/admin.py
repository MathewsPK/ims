from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from users.models import User
from projects.models import Project
from .models import AMCReport, ReportImage, InstallationReport, InstallationDocument


class AMCReportResource(resources.ModelResource):
    engineer = fields.Field(
        column_name='engineer',
        attribute='engineer',
        widget=ForeignKeyWidget(User, field='email'),
    )
    project = fields.Field(
        column_name='project',
        attribute='project',
        widget=ForeignKeyWidget(Project, field='name'),
    )
    reviewed_by = fields.Field(
        column_name='reviewed_by',
        attribute='reviewed_by',
        widget=ForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = AMCReport
        fields = (
            'id', 'project', 'engineer', 'date', 'status',
            'work_done', 'issues_found', 'recommendations',
            'reviewed_by', 'reviewed_at', 'review_note',
            'created_at', 'updated_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 0


@admin.register(AMCReport)
class AMCReportAdmin(ImportExportModelAdmin):
    resource_classes = [AMCReportResource]
    list_display = ('project', 'engineer', 'date', 'status')
    list_filter = ('status', 'date')
    inlines = [ReportImageInline]


class InstallationDocumentInline(admin.TabularInline):
    model = InstallationDocument
    extra = 0


@admin.register(InstallationReport)
class InstallationReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'installed_by', 'installation_date')
    list_filter = ('installation_date',)
    search_fields = ('project__name', 'notes')
    inlines = [InstallationDocumentInline]
