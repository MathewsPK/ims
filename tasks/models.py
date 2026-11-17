from django.conf import settings
from django.db import models
from django.urls import reverse
from core.models import TimeStampedModel


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        BLOCKED = 'BLOCKED', 'Blocked'
        COMPLETED = 'COMPLETED', 'Completed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tasks',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True, blank=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    completed_date = models.DateField(
        null=True, blank=True,
        help_text="Auto-filled with today's date when marked Completed, if left blank.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    depends_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dependent_tasks',
        help_text="Optional: this task can't realistically start until the selected task is done.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
    )

    class Meta:
        ordering = ['-priority', 'end_date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED:
            if not self.completed_date:
                from django.utils import timezone
                self.completed_date = timezone.now().date()
        else:
            self.completed_date = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tasks:task_detail', kwargs={'pk': self.pk})

    @property
    def is_blocked_by_dependency(self):
        return bool(self.depends_on and self.depends_on.status != self.Status.COMPLETED)

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status != self.Status.COMPLETED and self.end_date < timezone.now().date()

    @property
    def status_color(self):
        return {
            'PENDING': 'secondary',
            'IN_PROGRESS': 'primary',
            'BLOCKED': 'warning',
            'COMPLETED': 'success',
        }.get(self.status, 'secondary')

    @property
    def priority_color(self):
        return {
            'LOW': 'success',
            'MEDIUM': 'info',
            'HIGH': 'warning',
            'URGENT': 'danger',
        }.get(self.priority, 'secondary')


class OutOfOffice(models.Model):
    """A block of days someone is unavailable — shown on the calendar so
    others can see it before assigning tasks to that person."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='out_of_office',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_out_of_office',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Out of Office'
        verbose_name_plural = 'Out of Office'

    def __str__(self):
        return f"{self.user} out of office {self.start_date} → {self.end_date}"


class TimeLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_logs',
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_logs')
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user} logged {self.hours}h on {self.task} ({self.date})"
