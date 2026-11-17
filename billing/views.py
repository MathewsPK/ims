from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import Lower
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from core.models import log_activity
from users.permissions import ManagerOrAdminMixin
from notifications.utils import notify_user
from .models import Subscription
from .forms import SubscriptionForm


class SubscriptionListView(ManagerOrAdminMixin, ListView):
    model = Subscription
    template_name = 'billing/subscription_list.html'
    context_object_name = 'subscriptions'

    # ?sort=<key> -> ordering
    SORT_OPTIONS = {
        'name': (Lower('name').asc(),),
        '-name': (Lower('name').desc(),),
        'cost': ('cost', Lower('name').asc()),
        '-cost': ('-cost', Lower('name').asc()),
    }

    def get_sort(self):
        sort = self.request.GET.get('sort', '')
        return sort if sort in self.SORT_OPTIONS else ''

    def get_queryset(self):
        qs = Subscription.objects.select_related('managed_by').all()
        category = self.request.GET.get('category', '')
        status = self.request.GET.get('status', '')
        if category:
            qs = qs.filter(category=category)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        sort = self.get_sort()
        if sort:
            qs = qs.order_by(*self.SORT_OPTIONS[sort])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        active_qs = Subscription.objects.filter(is_active=True)
        ctx['category_choices'] = Subscription.PlatformCategory.choices
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_sort'] = self.get_sort()
        # Rough monthly-equivalent total spend across active subscriptions
        monthly_total = 0
        for sub in active_qs:
            if sub.billing_cycle == 'MONTHLY':
                monthly_total += sub.cost
            elif sub.billing_cycle == 'QUARTERLY':
                monthly_total += sub.cost / 3
            elif sub.billing_cycle == 'YEARLY':
                monthly_total += sub.cost / 12
        ctx['monthly_total'] = monthly_total
        ctx['due_soon_count'] = sum(1 for s in active_qs if s.is_due_soon or s.is_overdue)
        return ctx


class SubscriptionDetailView(ManagerOrAdminMixin, DetailView):
    model = Subscription
    template_name = 'billing/subscription_detail.html'
    context_object_name = 'subscription'


class SubscriptionCreateView(ManagerOrAdminMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'billing/subscription_form.html'
    success_url = reverse_lazy('billing:subscription_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATED', f"Added subscription: {self.object.name}", self.object)
        messages.success(self.request, "Subscription added.")
        return response


class SubscriptionUpdateView(ManagerOrAdminMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'billing/subscription_form.html'
    success_url = reverse_lazy('billing:subscription_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATED', f"Updated subscription: {self.object.name}", self.object)
        messages.success(self.request, "Subscription updated.")
        return response


class SubscriptionDeleteView(ManagerOrAdminMixin, DeleteView):
    model = Subscription
    template_name = 'billing/subscription_confirm_delete.html'
    success_url = reverse_lazy('billing:subscription_list')


@login_required
def mark_subscription_paid(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if not (request.user.is_superuser or request.user.role in ('ADMIN', 'MANAGER')):
        messages.error(request, "No permission.")
        return redirect('billing:subscription_list')

    if request.method == 'POST':
        old_date = subscription.next_renewal_date
        subscription.mark_paid()
        log_activity(
            request.user, 'UPDATED',
            f"Marked '{subscription.name}' as paid (renewal moved from {old_date} to {subscription.next_renewal_date})",
            subscription,
        )
        if subscription.managed_by:
            notify_user(
                subscription.managed_by,
                title=f"Payment recorded: {subscription.name}",
                message=f"Next renewal is now {subscription.next_renewal_date:%d %b %Y}.",
                link=subscription.get_absolute_url(),
                category='BILLING',
            )
        messages.success(request, f"Marked as paid. Next renewal: {subscription.next_renewal_date:%d %b %Y}.")
    return redirect('billing:subscription_list')


@csrf_exempt
def cron_check_renewals(request):
    """
    HTTP-triggerable version of `check_subscription_renewals` for hosts
    without a native cron/scheduler (e.g. a free web-service-only Render plan).
    Point an external pinger (Render Cron Job, GitHub Actions, cron-job.org)
    at this URL once a day with ?token=<CRON_SECRET>.
    """
    token = request.GET.get('token', '')
    expected = getattr(settings, 'CRON_SECRET', '')
    if not expected or token != expected:
        return HttpResponseForbidden("Invalid or missing token.")

    from django.core.management import call_command
    call_command('check_subscription_renewals')
    return HttpResponse("OK")
