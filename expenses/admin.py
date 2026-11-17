from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from users.models import User
from projects.models import Project
from .models import Expense


class ExpenseResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
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
        model = Expense
        fields = (
            'id', 'user', 'project', 'date', 'amount', 'category',
            'description', 'approval_status', 'reviewed_by',
            'reviewed_at', 'review_note', 'created_at', 'updated_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


@admin.register(Expense)
class ExpenseAdmin(ImportExportModelAdmin):
    resource_classes = [ExpenseResource]
    list_display = ('user', 'date', 'amount', 'category', 'approval_status', 'project')
    list_filter = ('category', 'approval_status', 'date')
    search_fields = ('user__name', 'user__email', 'description')
    readonly_fields = ('reviewed_by', 'reviewed_at')
