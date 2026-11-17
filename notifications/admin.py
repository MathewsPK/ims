from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from users.models import User
from .models import (
    GoogleCalendarEvent,
    GoogleCalendarFeed,
    Notification,
    NotificationEvent,
)


class NotificationResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='email'),
    )

    class Meta:
        model = Notification
        fields = (
            'id', 'user', 'title', 'message', 'category',
            'link', 'is_read', 'created_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


class NotificationEventResource(resources.ModelResource):
    created_by = fields.Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, field='email'),
    )
    assigned_to = fields.Field(
        column_name='assigned_to',
        attribute='assigned_to',
        widget=ManyToManyWidget(User, field='email', separator='; '),
    )

    class Meta:
        model = NotificationEvent
        fields = (
            'id', 'title', 'description', 'event_type', 'event_datetime',
            'location', 'all_users', 'created_by', 'assigned_to', 'created_at',
        )
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True


@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin):
    resource_classes = [NotificationResource]
    list_display = ('user', 'title', 'category', 'is_read', 'created_at')
    list_filter = ('category', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')


@admin.register(NotificationEvent)
class NotificationEventAdmin(ImportExportModelAdmin):
    resource_classes = [NotificationEventResource]
    list_display = ('title', 'event_type', 'event_datetime', 'all_users', 'created_by')
    list_filter = ('event_type', 'all_users', 'event_datetime')
    filter_horizontal = ('assigned_to',)


@admin.register(GoogleCalendarFeed)
class GoogleCalendarFeedAdmin(admin.ModelAdmin):
    """Admin manages COMPANY-WIDE feeds only.

    Private per-user feeds (owner set) are hidden here — users manage
    their own via the 'My Google Calendars' page in the app.
    """

    list_display = ('name', 'color', 'enabled', 'import_as_events', 'last_synced', 'short_error')
    list_filter = ('enabled',)
    exclude = ('owner',)
    actions = ['sync_now']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(owner__isnull=True)

    @admin.display(description='Last error')
    def short_error(self, obj):
        return (obj.last_error[:60] + '…') if len(obj.last_error) > 60 else obj.last_error

    @admin.action(description='Sync selected feeds now')
    def sync_now(self, request, queryset):
        from django.utils import timezone
        from . import gcal
        for feed in queryset:
            try:
                n = gcal.sync_feed(feed)
                feed.last_error = ''
                self.message_user(request, f"{feed.name}: {n} events synced.")
            except Exception as exc:  # noqa: BLE001
                feed.last_error = str(exc)[:2000]
                self.message_user(request, f"{feed.name}: FAILED — {exc}", level=30)
            feed.last_synced = timezone.now()
            feed.save(update_fields=['last_synced', 'last_error'])


@admin.register(GoogleCalendarEvent)
class GoogleCalendarEventAdmin(admin.ModelAdmin):
    """Only events from company-wide feeds — private feeds stay private."""

    list_display = ('title', 'feed', 'start', 'end', 'all_day')
    list_filter = ('all_day',)
    search_fields = ('title', 'location')
    date_hierarchy = 'start'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(feed__owner__isnull=True)
