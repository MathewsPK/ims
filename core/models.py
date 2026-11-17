"""
Shared core models:
- ActivityLog: project/task/AMC timeline entries (visible to users)
- AuditLog:    admin-facing change tracking
- TimeStampedModel: abstract base for created/updated timestamps
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityLog(models.Model):
    """Generic timeline entry tied to any object (Project, Task, AMC, etc.)."""

    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        UPDATED = 'UPDATED', 'Updated'
        DELETED = 'DELETED', 'Deleted'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        COMMENTED = 'COMMENTED', 'Commented'
        UPLOADED = 'UPLOADED', 'Uploaded'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities',
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    description = models.TextField(blank=True)

    # GenericForeignKey to any object
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        who = self.user.name if self.user and self.user.name else (self.user.email if self.user else 'System')
        return f"{who} {self.get_action_display()} — {self.description[:60]}"


class AuditLog(models.Model):
    """Admin-facing audit trail for sensitive changes."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_entries',
    )
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} @ {self.timestamp}"


class Holiday(models.Model):
    """Public holiday shown on the IMS calendar with special marking."""

    class Region(models.TextChoices):
        NATIONAL = 'NATIONAL', 'India (National)'
        ODISHA = 'ODISHA', 'Odisha'
        VADODARA = 'VADODARA', 'Vadodara / Gujarat'

    name = models.CharField(max_length=150)
    date = models.DateField(db_index=True)
    region = models.CharField(
        max_length=20, choices=Region.choices, default=Region.NATIONAL,
    )

    # Marker colours used by the calendar
    REGION_COLORS = {
        'NATIONAL': '#15803d',   # green
        'ODISHA': '#c2410c',     # deep orange
        'VADODARA': '#6d28d9',   # violet
    }

    class Meta:
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(fields=['date', 'region', 'name'], name='uniq_holiday'),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_region_display()}) — {self.date}"

    @property
    def color(self):
        return self.REGION_COLORS.get(self.region, '#15803d')


def log_activity(user, action, description, obj=None):
    """Helper to create an ActivityLog entry."""
    entry = ActivityLog(
        user=user,
        action=action,
        description=description,
    )
    if obj is not None:
        entry.content_type = ContentType.objects.get_for_model(obj.__class__)
        entry.object_id = obj.pk
    entry.save()
    return entry
