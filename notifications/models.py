from django.conf import settings
from django.db import models
from django.urls import reverse


class Notification(models.Model):
    """In-app notification per user."""

    class Category(models.TextChoices):
        TASK = 'TASK', 'Task'
        AMC = 'AMC', 'AMC'
        MEETING = 'MEETING', 'Meeting'
        INTERVIEW = 'INTERVIEW', 'Interview'
        REMINDER = 'REMINDER', 'Reminder'
        EXPENSE = 'EXPENSE', 'Expense'
        REPORT = 'REPORT', 'Report'
        BILLING = 'BILLING', 'Billing'
        SYSTEM = 'SYSTEM', 'System'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.SYSTEM,
    )
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read', '-created_at'])]

    def __str__(self):
        return f"[{self.category}] {self.title} → {self.user}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    @property
    def icon(self):
        return {
            'TASK': 'bi-check2-square',
            'AMC': 'bi-tools',
            'MEETING': 'bi-calendar-event',
            'INTERVIEW': 'bi-person-badge',
            'REMINDER': 'bi-bell',
            'EXPENSE': 'bi-currency-rupee',
            'REPORT': 'bi-file-earmark-text',
            'BILLING': 'bi-credit-card',
            'SYSTEM': 'bi-info-circle',
        }.get(self.category, 'bi-bell')

    @property
    def color(self):
        return {
            'TASK': 'primary',
            'AMC': 'warning',
            'MEETING': 'info',
            'INTERVIEW': 'success',
            'REMINDER': 'secondary',
            'EXPENSE': 'danger',
            'REPORT': 'dark',
            'BILLING': 'warning',
            'SYSTEM': 'light',
        }.get(self.category, 'secondary')


class NotificationEvent(models.Model):
    """Scheduled meeting / interview / reminder visible to assigned users."""

    class EventType(models.TextChoices):
        MEETING = 'MEETING', 'Meeting'
        INTERVIEW = 'INTERVIEW', 'Interview'
        REMINDER = 'REMINDER', 'Reminder'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.MEETING,
    )
    event_datetime = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(
        max_length=500, blank=True,
        help_text="Google Meet, Teams, Zoom or any video call link",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
    )
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='events',
        blank=True,
        help_text="Leave empty to broadcast to all users",
    )
    all_users = models.BooleanField(
        default=False,
        help_text="Notify all active users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    gcal_uid = models.CharField(
        max_length=300, blank=True, default='', db_index=True,
        help_text="Set automatically for events imported from Google Calendar",
    )

    class Meta:
        ordering = ['event_datetime']

    def __str__(self):
        return f"[{self.event_type}] {self.title} @ {self.event_datetime}"

    def get_absolute_url(self):
        return reverse('notifications:event_detail', kwargs={'pk': self.pk})


class GoogleCalendarFeed(models.Model):
    """A Google Calendar synced into the IMS via its secret iCal address.

    Google Calendar (web) → Settings → select the calendar →
    'Integrate calendar' → copy 'Secret address in iCal format'
    and paste that URL here.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='gcal_feeds',
        help_text="Private feed — its events are visible ONLY to this user. "
                  "Leave empty for a company-wide feed visible to everyone.",
    )
    name = models.CharField(max_length=100, help_text="Label shown in the calendar legend")
    ical_url = models.URLField(
        max_length=600,
        help_text="Secret address in iCal format (ends in /basic.ics)",
    )
    color = models.CharField(max_length=7, default='#0b8043', help_text="Hex colour, e.g. #0b8043")
    enabled = models.BooleanField(default=True)
    import_as_events = models.BooleanField(
        default=True,
        help_text="Company-wide feeds only: also import upcoming entries "
                  "into the Meetings/Events list",
    )
    last_synced = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name


class GoogleCalendarEvent(models.Model):
    """A single (possibly recurring-expanded) event pulled from a feed."""

    feed = models.ForeignKey(GoogleCalendarFeed, on_delete=models.CASCADE, related_name='events')
    uid = models.CharField(max_length=300)
    title = models.CharField(max_length=300, blank=True, default='(no title)')
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=300, blank=True, default='')
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start']
        constraints = [
            models.UniqueConstraint(fields=['feed', 'uid', 'start'], name='uniq_feed_uid_start'),
        ]

    def __str__(self):
        return f"{self.title} @ {self.start:%Y-%m-%d %H:%M}"
