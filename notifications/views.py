from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from users.permissions import ManagerOrAdminMixin
from .models import GoogleCalendarFeed, Notification, NotificationEvent
from .forms import GoogleCalendarFeedForm, NotificationEventForm
from .utils import notify_event


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        # Mark all as read when user views this page
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return super().get(request, *args, **kwargs)


@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.mark_read()
    next_url = request.GET.get('next') or notif.link or '/'
    return redirect(next_url)


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:notification_list')


@login_required
def notifications_json(request):
    """AJAX endpoint: returns unread count + top 5."""
    qs = Notification.objects.filter(user=request.user, is_read=False)[:5]
    data = {
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'notifications': [
            {
                'id': n.pk,
                'title': n.title,
                'message': n.message,
                'category': n.category,
                'icon': n.icon,
                'color': n.color,
                'link': n.link,
                'created_at': n.created_at.strftime('%d %b %Y, %H:%M'),
            }
            for n in qs
        ],
    }
    return JsonResponse(data)


# -------- Notification Events (Meetings / Interviews / Reminders) --------

class EventListView(LoginRequiredMixin, ListView):
    model = NotificationEvent
    template_name = 'notifications/event_list.html'
    context_object_name = 'events'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        qs = NotificationEvent.objects.all()
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(Q(all_users=True) | Q(assigned_to=user))
        q = self.request.GET.get('q', '').strip()
        etype = self.request.GET.get('type', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        if etype:
            qs = qs.filter(event_type=etype)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['event_type_choices'] = NotificationEvent.EventType.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = NotificationEvent
    template_name = 'notifications/event_detail.html'
    context_object_name = 'event'


class EventCreateView(ManagerOrAdminMixin, CreateView):
    model = NotificationEvent
    form_class = NotificationEventForm
    template_name = 'notifications/event_form.html'
    success_url = reverse_lazy('notifications:event_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        notify_event(self.object)
        messages.success(self.request, "Event created and notifications sent.")
        return response


class EventUpdateView(ManagerOrAdminMixin, UpdateView):
    model = NotificationEvent
    form_class = NotificationEventForm
    template_name = 'notifications/event_form.html'
    success_url = reverse_lazy('notifications:event_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Event updated.")
        return response


class EventDeleteView(ManagerOrAdminMixin, DeleteView):
    model = NotificationEvent
    template_name = 'notifications/event_confirm_delete.html'
    success_url = reverse_lazy('notifications:event_list')


# -------- My Google Calendars (private, per-user) --------

@login_required
def my_calendars(request):
    """List + add the current user's private Google Calendar feeds."""
    feeds = GoogleCalendarFeed.objects.filter(owner=request.user)
    if request.method == 'POST':
        form = GoogleCalendarFeedForm(request.POST)
        if form.is_valid():
            feed = form.save(commit=False)
            feed.owner = request.user
            feed.save()
            from . import gcal
            try:
                n = gcal.sync_feed(feed)
                messages.success(request, f"Calendar connected — {n} events synced.")
            except Exception as exc:  # noqa: BLE001
                feed.last_error = str(exc)[:2000]
                feed.save(update_fields=['last_error'])
                messages.warning(
                    request,
                    "Calendar saved, but the first sync failed — check the URL. "
                    f"({exc})",
                )
            return redirect('notifications:my_calendars')
    else:
        form = GoogleCalendarFeedForm()
    return render(request, 'notifications/my_calendars.html', {
        'feeds': feeds,
        'form': form,
    })


@login_required
def my_calendar_delete(request, pk):
    """Remove one of the current user's feeds (and all its synced events)."""
    feed = get_object_or_404(GoogleCalendarFeed, pk=pk, owner=request.user)
    if request.method == 'POST':
        feed.delete()
        messages.success(request, f"Removed calendar '{feed.name}'.")
    return redirect('notifications:my_calendars')


@login_required
def my_calendar_sync(request, pk):
    """Manually re-sync one of the current user's feeds."""
    from django.utils import timezone as dj_tz
    from . import gcal
    feed = get_object_or_404(GoogleCalendarFeed, pk=pk, owner=request.user)
    try:
        n = gcal.sync_feed(feed)
        feed.last_error = ''
        messages.success(request, f"'{feed.name}' synced — {n} events.")
    except Exception as exc:  # noqa: BLE001
        feed.last_error = str(exc)[:2000]
        messages.error(request, f"Sync failed: {exc}")
    feed.last_synced = dj_tz.now()
    feed.save(update_fields=['last_synced', 'last_error'])
    return redirect('notifications:my_calendars')
