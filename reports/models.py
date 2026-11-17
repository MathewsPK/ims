from django.conf import settings
from django.db import models
from django.urls import reverse
from core.models import TimeStampedModel


class AMCReport(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        REVIEWED = 'REVIEWED', 'Reviewed'
        APPROVED = 'APPROVED', 'Approved'

    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='amc_reports',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='amc_reports',
    )
    amc_project = models.ForeignKey(
        'amc.AMCProject',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reports',
    )
    date = models.DateField()
    work_done = models.TextField()
    issues_found = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_reports',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    client_signature = models.ImageField(
        upload_to='report_signatures/', null=True, blank=True,
    )

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"AMC Report — {self.project.name} by {self.engineer} on {self.date}"

    def get_absolute_url(self):
        return reverse('reports:report_detail', kwargs={'pk': self.pk})

    @property
    def status_color(self):
        return {
            'SUBMITTED': 'warning',
            'REVIEWED': 'info',
            'APPROVED': 'success',
        }.get(self.status, 'secondary')


class ReportImage(models.Model):
    report = models.ForeignKey(
        AMCReport, on_delete=models.CASCADE, related_name='images',
    )
    image = models.ImageField(upload_to='report_images/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.report}"


class InstallationReport(TimeStampedModel):
    """A simple log entry for equipment/installation work done on a project.
    No approval workflow — just a record with the challan/document attached."""

    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='installation_reports',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='installation_reports',
    )
    installation_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-installation_date', '-created_at']

    def __str__(self):
        return f"Installation — {self.project.name} on {self.installation_date}"

    def get_absolute_url(self):
        return reverse('reports:installation_detail', kwargs={'pk': self.pk})


class InstallationDocument(models.Model):
    """Challan / delivery document / photo attached to an InstallationReport.
    Supports multiple files per installation (challans are often multi-page)."""

    installation = models.ForeignKey(
        InstallationReport, on_delete=models.CASCADE, related_name='documents',
    )
    file = models.FileField(upload_to='installation_docs/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.installation}"

    @property
    def is_image(self):
        name = self.file.name.lower()
        return name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
