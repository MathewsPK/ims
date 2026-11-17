from django.conf import settings
from django.db import models


class TenderRun(models.Model):
    """One execution of the tender radar (search + email), started from IMS or the daily schedule."""

    class Kind(models.TextChoices):
        SEARCH = 'SEARCH', 'Search all portals & email'
        RESEND = 'RESEND', 'Re-send current open tenders'

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        RUNNING = 'RUNNING', 'Running'
        DONE = 'DONE', 'Done'
        FAILED = 'FAILED', 'Failed'

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SEARCH)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    scheduled = models.BooleanField(default=False, help_text='Started by the daily schedule, not a person')
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='tender_runs')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    tenders_emailed = models.PositiveIntegerField(default=0)
    updates_emailed = models.PositiveIntegerField(default=0)
    email_sent = models.BooleanField(default=False)
    summary = models.CharField(max_length=300, blank=True)
    log = models.TextField(blank=True)
    digest_html = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_kind_display()} · {self.created_at:%d %b %Y %H:%M} · {self.get_status_display()}"

    @property
    def is_active(self):
        return self.status in (self.Status.QUEUED, self.Status.RUNNING)

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            secs = int((self.finished_at - self.started_at).total_seconds())
            return f"{secs // 60} min {secs % 60} s" if secs >= 60 else f"{secs} s"
        return ''
