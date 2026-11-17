from django.conf import settings
from django.db import models
from django.urls import reverse
from core.models import TimeStampedModel


class Project(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNING = 'PLANNING', 'Planning'
        ONGOING = 'ONGOING', 'Ongoing'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    name = models.CharField(max_length=200)
    client = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)

    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='projects',
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.client})"

    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.pk})

    @property
    def is_ongoing(self):
        return self.status == self.Status.ONGOING

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def progress_percent(self):
        """Rough progress: completed tasks / total tasks."""
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter(status='COMPLETED').count()
        return int((done / total) * 100)


class ProjectMedia(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='media',
    )
    image = models.ImageField(upload_to='project_media/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Media for {self.project.name}"
