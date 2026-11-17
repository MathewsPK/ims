import calendar
from datetime import date

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel


def add_months(source_date, months):
    """Add `months` calendar months to a date, clamping the day to the
    last valid day of the resulting month (handles Jan 31 + 1mo -> Feb 28/29)."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class Subscription(TimeStampedModel):
    """A recurring platform/software subscription paid by the office
    (AI tools, Adobe, hosting, etc.) tracked for renewal/payment reminders."""

    class PlatformCategory(models.TextChoices):
        AI = 'AI', 'AI Subscription'
        DESIGN = 'DESIGN', 'Design & Creative'
        HOSTING = 'HOSTING', 'Hosting & Infrastructure'
        PRODUCTIVITY = 'PRODUCTIVITY', 'Productivity & Office'
        OTHER = 'OTHER', 'Other'

    class BillingCycle(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly'
        QUARTERLY = 'QUARTERLY', 'Quarterly'
        YEARLY = 'YEARLY', 'Yearly'
        ONE_TIME = 'ONE_TIME', 'One-time'

    CYCLE_MONTHS = {
        'MONTHLY': 1,
        'QUARTERLY': 3,
        'YEARLY': 12,
    }

    name = models.CharField(
        max_length=150,
        help_text="e.g. 'ChatGPT Plus', 'Adobe Creative Cloud', 'Claude Pro'",
    )
    category = models.CharField(
        max_length=20, choices=PlatformCategory.choices, default=PlatformCategory.OTHER,
    )
    vendor = models.CharField(
        max_length=150, blank=True,
        help_text="e.g. OpenAI, Adobe Inc., Anthropic",
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY,
    )
    next_renewal_date = models.DateField(help_text="Next date payment/renewal is due")
    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subscriptions',
        help_text="Person notified about this subscription. Leave blank to notify all Admins/Managers.",
    )
    account_email = models.EmailField(
        blank=True, help_text="Login/account email used to sign up for this platform",
    )
    payment_method = models.CharField(
        max_length=100, blank=True,
        help_text="e.g. Company card ending 4321, UPI, Bank transfer",
    )
    reminder_days_before = models.PositiveIntegerField(
        default=7, help_text="How many days before renewal to start sending reminders",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    last_reminder_sent = models.DateField(
        null=True, blank=True,
        help_text="Internal: date the last reminder was sent (avoids duplicate same-day pings)",
    )

    class Meta:
        ordering = ['next_renewal_date']

    def __str__(self):
        return f"{self.name} — {self.currency} {self.cost} ({self.get_billing_cycle_display()})"

    def get_absolute_url(self):
        return reverse('billing:subscription_detail', kwargs={'pk': self.pk})

    @property
    def days_to_renewal(self):
        today = timezone.now().date()
        return (self.next_renewal_date - today).days

    @property
    def is_overdue(self):
        return self.days_to_renewal < 0

    @property
    def is_due_soon(self):
        """Within the reminder window (inclusive of today) but not yet overdue."""
        return 0 <= self.days_to_renewal <= self.reminder_days_before

    @property
    def needs_attention(self):
        return self.is_active and (self.is_due_soon or self.is_overdue)

    @property
    def status_color(self):
        if self.is_overdue:
            return 'danger'
        if self.is_due_soon:
            return 'warning'
        return 'success'

    def mark_paid(self):
        """Advance the subscription to its next billing cycle after payment is confirmed."""
        months = self.CYCLE_MONTHS.get(self.billing_cycle)
        if months:
            self.next_renewal_date = add_months(self.next_renewal_date, months)
        self.last_reminder_sent = None
        self.save(update_fields=['next_renewal_date', 'last_reminder_sent', 'updated_at'])
