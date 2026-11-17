from django.conf import settings
from django.db import models
from django.urls import reverse
from core.models import TimeStampedModel


class Expense(TimeStampedModel):
    class Category(models.TextChoices):
        TRAVEL = 'TRAVEL', 'Travel'
        STAY = 'STAY', 'Stay'
        FOOD = 'FOOD', 'Food'
        ELECTRICAL = 'ELECTRICAL', 'Electrical'
        TOOLS = 'TOOLS', 'Tools & Equipment'
        COMMUNICATION = 'COMMUNICATION', 'Communication'
        MISC = 'MISC', 'Miscellaneous'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        PAID = 'PAID', 'Paid'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='expenses',
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_expenses',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user} — ₹{self.amount} ({self.category}) on {self.date}"

    def get_absolute_url(self):
        return reverse('expenses:expense_detail', kwargs={'pk': self.pk})

    @property
    def status_color(self):
        return {
            'PENDING': 'warning',
            'APPROVED': 'success',
            'REJECTED': 'danger',
            'PAID': 'primary',
        }.get(self.approval_status, 'secondary')
