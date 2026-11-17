from django.db import models
from django.urls import reverse
from django.utils import timezone
from core.models import TimeStampedModel


class AMCProject(TimeStampedModel):
    """AMC (Annual Maintenance Contract) for a project."""
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, related_name='amc_contracts',
    )
    contract_number = models.CharField(max_length=50, blank=True)
    amc_start_date = models.DateField()
    amc_end_date = models.DateField()
    contract_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-amc_end_date']

    def __str__(self):
        return f"AMC: {self.project.name} ({self.amc_start_date} → {self.amc_end_date})"

    def get_absolute_url(self):
        return reverse('amc:amc_detail', kwargs={'pk': self.pk})

    @property
    def is_active(self):
        today = timezone.now().date()
        return self.amc_start_date <= today <= self.amc_end_date

    @property
    def days_to_expiry(self):
        today = timezone.now().date()
        return (self.amc_end_date - today).days

    @property
    def is_expiring_soon(self):
        """Within 30 days of expiry."""
        return 0 <= self.days_to_expiry <= 30

    @property
    def is_expired(self):
        return self.days_to_expiry < 0


class Equipment(TimeStampedModel):
    amc_project = models.ForeignKey(
        AMCProject, on_delete=models.CASCADE, related_name='equipment',
    )
    name = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    location = models.CharField(
        max_length=200, blank=True,
        help_text="Physical location of equipment (e.g. Gallery 1, Reception)",
    )
    installation_date = models.DateField(
        null=True, blank=True,
        help_text="Date equipment was installed on site",
    )
    warranty_expiry = models.DateField(null=True, blank=True, verbose_name="Warranty Ends")
    amc_date = models.DateField(
        null=True, blank=True,
        help_text="Date equipment entered AMC",
    )
    amc_end_date = models.DateField(
        null=True, blank=True,
        help_text="Equipment-specific AMC end date",
    )
    invoice_date = models.DateField(null=True, blank=True)
    invoice_no = models.CharField(max_length=100, blank=True, verbose_name="Invoice No.")
    win_license = models.CharField(
        max_length=200, blank=True,
        verbose_name="Windows License Key",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def get_absolute_url(self):
        return reverse('amc:equipment_detail', kwargs={'pk': self.pk})

    @property
    def warranty_days_left(self):
        if not self.warranty_expiry:
            return None
        return (self.warranty_expiry - timezone.now().date()).days
