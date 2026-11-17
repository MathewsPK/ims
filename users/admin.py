from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export import resources
from import_export.admin import ImportExportMixin

from .models import User


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'role', 'phone',
            'is_active', 'is_staff', 'date_joined', 'created_at',
        )
        export_order = fields
        import_id_fields = ('email',)
        skip_unchanged = True
        report_skipped = True
        exclude = ('password', 'profile_photo', 'user_permissions', 'groups')


@admin.register(User)
class UserAdmin(ImportExportMixin, BaseUserAdmin):
    resource_classes = [UserResource]
    list_display = ('email', 'name', 'role', 'phone', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'name', 'phone')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('name', 'phone', 'profile_photo')}),
        ('Role & Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'password1', 'password2'),
        }),
    )
