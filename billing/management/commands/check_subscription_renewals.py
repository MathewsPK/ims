"""
Checks all active subscriptions for upcoming/overdue renewals and sends
an in-app notification + email to the responsible person (or all
Admins/Managers if no one is assigned).

Run manually:
    python manage.py check_subscription_renewals

Runs once a day from cron.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import Subscription
from notifications.utils import notify_user


class Command(BaseCommand):
    help = "Send renewal/payment reminders for subscriptions due soon or overdue."

    def handle(self, *args, **options):
        today = timezone.now().date()
        subs = Subscription.objects.filter(is_active=True).select_related('managed_by')

        sent = 0
        for sub in subs:
            if not (sub.is_due_soon or sub.is_overdue):
                continue
            if sub.last_reminder_sent == today:
                continue  # already reminded today

            recipients = [sub.managed_by] if sub.managed_by else self._admins_and_managers()
            status = "OVERDUE" if sub.is_overdue else f"due in {sub.days_to_renewal} day(s)"
            title = f"Subscription payment {status}: {sub.name}"
            message = (
                f"{sub.name} ({sub.get_category_display()}) — "
                f"{sub.currency} {sub.cost} / {sub.get_billing_cycle_display()}.\n"
                f"Renewal date: {sub.next_renewal_date:%d %b %Y}."
            )

            for user in recipients:
                if not user:
                    continue
                notify_user(
                    user, title=title, message=message,
                    link=sub.get_absolute_url(), category='BILLING',
                )
                if user.email:
                    try:
                        send_mail(
                            subject=f"[IMS] {title}",
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        self.stderr.write(f"Email failed for {user.email}: {e}")

            sub.last_reminder_sent = today
            sub.save(update_fields=['last_reminder_sent'])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Checked {subs.count()} subscriptions, sent {sent} reminder(s)."))

    def _admins_and_managers(self):
        from users.models import User
        return list(User.objects.filter(role__in=['ADMIN', 'MANAGER'], is_active=True))
