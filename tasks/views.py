import uuid
from datetime import datetime, timezone as dt_timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from core.models import ActivityLog, log_activity
from notifications.utils import notify_user
from .models import Task, TimeLog, OutOfOffice
from .forms import TaskForm, TimeLogForm, OutOfOfficeForm


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.select_related('assigned_to', 'project').all()

        # Engineers/Staff see tasks assigned to them or on their projects
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(Q(assigned_to=user) | Q(project__assigned_users=user))

        # Filters
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        priority = self.request.GET.get('priority', '').strip()
        assigned = self.request.GET.get('assigned', '').strip()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned == 'me':
            qs = qs.filter(assigned_to=user)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Task.Status.choices
        ctx['priority_choices'] = Task.Priority.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_priority'] = self.request.GET.get('priority', '')
        ctx['selected_assigned'] = self.request.GET.get('assigned', '')
        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['time_logs'] = self.object.time_logs.select_related('user').all()
        ctx['total_hours'] = self.object.time_logs.aggregate(
            total=Sum('hours'))['total'] or 0
        ctx['timelog_form'] = TimeLogForm(initial={'date': timezone.now().date()})

        # Build a Google Calendar "Add Event" link for this task
        from datetime import timedelta
        task = self.object
        dates = task.start_date.strftime('%Y%m%d') + '/' + (task.end_date + timedelta(days=1)).strftime('%Y%m%d')
        details_parts = []
        if task.description:
            details_parts.append(task.description)
        details_parts.append(f'Status: {task.get_status_display()}')
        details_parts.append(f'Priority: {task.get_priority_display()}')
        if task.project:
            details_parts.append(f'Project: {task.project.name}')
        import urllib.parse
        gcal_params = urllib.parse.urlencode({
            'action': 'TEMPLATE',
            'text': task.title,
            'dates': dates,
            'details': '\n'.join(details_parts),
        })
        ctx['gcal_link'] = f'https://calendar.google.com/calendar/render?{gcal_params}'
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_initial(self):
        initial = super().get_initial()
        project_pk = self.request.GET.get('project')
        if project_pk:
            initial['project'] = project_pk
        return initial

    def get_success_url(self):
        # If task was linked to a project, return to that project's detail page
        if self.object.project:
            return self.object.project.get_absolute_url()
        return super().get_success_url()

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(
            self.request.user, ActivityLog.Action.CREATED,
            f"Created task '{self.object.title}'", self.object,
        )
        # Notify assignee
        if self.object.assigned_to and self.object.assigned_to != self.request.user:
            notify_user(
                self.object.assigned_to,
                title="New task assigned",
                message=f"You have been assigned: {self.object.title}",
                link=self.object.get_absolute_url(),
                category='TASK',
            )
        messages.success(self.request, "Task created.")
        return response


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def form_valid(self, form):
        old_status = Task.objects.get(pk=self.object.pk).status
        old_assigned = Task.objects.get(pk=self.object.pk).assigned_to
        response = super().form_valid(form)
        action = ActivityLog.Action.UPDATED
        desc = f"Updated task '{self.object.title}'"
        if old_status != self.object.status:
            action = ActivityLog.Action.STATUS_CHANGED
            desc = f"Changed status: {old_status} → {self.object.status}"
        log_activity(self.request.user, action, desc, self.object)

        # Notify on re-assignment
        if old_assigned != self.object.assigned_to and self.object.assigned_to \
                and self.object.assigned_to != self.request.user:
            notify_user(
                self.object.assigned_to,
                title="Task assigned to you",
                message=f"{self.object.title}",
                link=self.object.get_absolute_url(),
                category='TASK',
            )
        messages.success(self.request, "Task updated.")
        return response


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')


@login_required
def log_time(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TimeLogForm(request.POST)
        if form.is_valid():
            tl = form.save(commit=False)
            tl.task = task
            tl.user = request.user
            tl.save()
            messages.success(request, f"Logged {tl.hours}h on '{task.title}'.")
    return redirect('tasks:task_detail', pk=pk)


def _can_manage_ooo_for_others(user):
    return user.is_superuser or user.role in ('ADMIN', 'MANAGER')


@login_required
def out_of_office_list(request):
    user = request.user
    qs = OutOfOffice.objects.select_related('user').all()
    if not _can_manage_ooo_for_others(user):
        qs = qs.filter(user=user)
    return render(request, 'tasks/out_of_office_list.html', {'entries': qs})


@login_required
def out_of_office_create(request):
    can_pick_user = _can_manage_ooo_for_others(request.user)
    if request.method == 'POST':
        form = OutOfOfficeForm(request.POST, can_pick_user=can_pick_user, current_user=request.user)
        if form.is_valid():
            ooo = form.save(commit=False)
            if not can_pick_user:
                ooo.user = request.user
            ooo.created_by = request.user
            ooo.save()
            messages.success(request, "Out of office added to the calendar.")
            return redirect('tasks:out_of_office_list')
    else:
        form = OutOfOfficeForm(can_pick_user=can_pick_user, current_user=request.user)
    return render(request, 'tasks/out_of_office_form.html', {'form': form})


@login_required
def out_of_office_delete(request, pk):
    ooo = get_object_or_404(OutOfOffice, pk=pk)
    if ooo.user != request.user and not _can_manage_ooo_for_others(request.user):
        messages.error(request, "No permission.")
        return redirect('tasks:out_of_office_list')
    if request.method == 'POST':
        ooo.delete()
        messages.success(request, "Removed.")
        return redirect('tasks:out_of_office_list')
    return render(request, 'tasks/out_of_office_confirm_delete.html', {'object': ooo})


# Colour palette for per-user calendar colouring
USER_COLOR_PALETTE = [
    '#4e79a7',  # steel blue
    '#f28e2b',  # orange
    '#e15759',  # red
    '#76b7b2',  # teal
    '#59a14f',  # green
    '#edc948',  # yellow
    '#b07aa1',  # purple
    '#ff9da7',  # pink
    '#9c755f',  # brown
    '#2d6a4f',  # dark green
    '#023e8a',  # navy
    '#d4a373',  # tan
    '#6d6875',  # mauve
    '#ef233c',  # crimson
    '#457b9d',  # muted blue
]


def _user_color(user_pk: int) -> str:
    """Return a deterministic colour from the palette for a given user pk."""
    return USER_COLOR_PALETTE[(user_pk - 1) % len(USER_COLOR_PALETTE)]


@login_required
def calendar_view(request):
    from users.models import User
    # Build a legend mapping user → colour so it can be rendered server-side,
    # as an interactive checklist (default: only the logged-in user checked).
    users = User.objects.filter(is_active=True).order_by('name')
    legend = [
        {'pk': u.pk, 'name': u.name or u.email, 'color': _user_color(u.pk)}
        for u in users
    ]

    from notifications.models import GoogleCalendarFeed
    gcal_legend = [
        {'name': f.name, 'color': f.color}
        for f in GoogleCalendarFeed.objects.filter(enabled=True).filter(
            Q(owner__isnull=True) | Q(owner=request.user)
        )
    ]
    from core.models import Holiday
    holiday_legend = [
        {'name': label, 'color': Holiday.REGION_COLORS[key]}
        for key, label in Holiday.Region.choices
        if Holiday.objects.filter(region=key).exists()
    ]
    return render(request, 'tasks/calendar.html', {
        'user_legend': legend,
        'gcal_legend': gcal_legend,
        'holiday_legend': holiday_legend,
        'current_user_pk': request.user.pk,
    })


@login_required
def calendar_events(request):
    """JSON endpoint for FullCalendar — events coloured by assigned user.

    Supports ?users=1,2,3 (comma-separated user pks, 'unassigned' allowed)
    to filter which people's tasks/out-of-office blocks are shown. If the
    param is absent entirely (very first load), defaults to just the
    logged-in user so the calendar isn't overwhelming by default.
    """
    user = request.user
    qs = Task.objects.select_related('assigned_to').all()
    if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
        qs = qs.filter(Q(assigned_to=user) | Q(project__assigned_users=user))

    if 'users' in request.GET:
        raw = request.GET.get('users', '')
        selected = set(raw.split(',')) if raw else set()
    else:
        selected = {str(user.pk)}
    show_unassigned = 'unassigned' in selected
    selected_pks = {int(x) for x in selected if x.isdigit()}

    events = []
    for t in qs.distinct():
        if t.assigned_to:
            if t.assigned_to.pk not in selected_pks:
                continue
            color = _user_color(t.assigned_to.pk)
            user_name = t.assigned_to.name or t.assigned_to.email
            user_pk = t.assigned_to.pk
        else:
            if not show_unassigned:
                continue
            color = '#adb5bd'
            user_name = 'Unassigned'
            user_pk = None

        events.append({
            'id': t.pk,
            'title': t.title,
            'start': t.start_date.isoformat(),
            'end': t.end_date.isoformat(),
            'url': t.get_absolute_url(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'status': t.get_status_display(),
                'priority': t.get_priority_display(),
                'userName': user_name,
                'userPk': user_pk,
            },
        })

    # ── Out of office blocks (only for currently-selected people) ──
    if selected_pks:
        ooo_qs = OutOfOffice.objects.select_related('user').filter(user_id__in=selected_pks)
        for o in ooo_qs:
            color = _user_color(o.user.pk)
            events.append({
                'id': f'ooo-{o.pk}',
                'title': f'{o.user.name or o.user.email} — Out of Office',
                'start': o.start_date.isoformat(),
                'end': (o.end_date + __import__('datetime').timedelta(days=1)).isoformat(),
                'allDay': True,
                'backgroundColor': '#e2e8f0',
                'borderColor': '#94a3b8',
                'textColor': '#475569',
                'extendedProps': {
                    'source': 'ooo',
                    'status': 'Out of Office',
                    'priority': '',
                    'userName': o.user.name or o.user.email,
                    'userPk': o.user.pk,
                    'reason': o.reason,
                },
            })

    # ── Google Calendar events (synced via secret iCal feeds) ──
    from notifications import gcal
    from notifications.models import GoogleCalendarEvent
    gcal.sync_all()  # throttled; never raises
    gcal_qs = GoogleCalendarEvent.objects.select_related('feed').filter(
        feed__enabled=True,
    ).filter(
        Q(feed__owner__isnull=True) | Q(feed__owner=user)  # private feeds: owner only
    )
    for e in gcal_qs:
        events.append({
            'id': f'gcal-{e.pk}',
            'title': e.title,
            'start': e.start.isoformat(),
            'end': e.end.isoformat(),
            'allDay': e.all_day,
            'backgroundColor': e.feed.color,
            'borderColor': e.feed.color,
            'extendedProps': {
                'status': 'Google Calendar',
                'priority': '',
                'userName': e.feed.name,
                'userPk': None,
                'source': 'google',
                'location': e.location,
            },
        })

    # ── Public holidays (National / Odisha / Vadodara) with special marking ──
    from core.models import Holiday
    for h in Holiday.objects.all():
        d = h.date.isoformat()
        # Labelled all-day chip
        events.append({
            'id': f'holiday-{h.pk}',
            'title': h.name,
            'start': d,
            'allDay': True,
            'backgroundColor': h.color,
            'borderColor': h.color,
            'extendedProps': {
                'source': 'holiday',
                'region': h.get_region_display(),
                'status': 'Holiday',
                'priority': '',
                'userName': h.get_region_display(),
                'userPk': None,
            },
        })
        # Soft background shading of the whole day cell
        events.append({
            'id': f'holiday-bg-{h.pk}',
            'start': d,
            'display': 'background',
            'color': h.color,
        })
    return JsonResponse(events, safe=False)


@login_required
def workload_view(request):
    """Workload visualization — tasks per user."""
    from users.models import User
    from projects.models import Project
    users_qs = (
        User.objects.filter(is_active=True)
        .annotate(
            pending=Count('assigned_tasks', filter=Q(assigned_tasks__status='PENDING')),
            in_progress=Count('assigned_tasks', filter=Q(assigned_tasks__status='IN_PROGRESS')),
            completed=Count('assigned_tasks', filter=Q(assigned_tasks__status='COMPLETED')),
        )
    )
    # Attach projects per user
    users_data = []
    for u in users_qs:
        u.active_projects = Project.objects.filter(
            assigned_users=u, status='ONGOING'
        ).order_by('name')
        users_data.append(u)
    return render(request, 'tasks/workload.html', {'users_data': users_data})


def _ical_escape(value):
    """Escape special characters for iCal text fields."""
    if not value:
        return ''
    return str(value).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n').replace('\r', '')


def _ical_datetime(d):
    """Format a date as an iCal DATE value (all-day)."""
    return d.strftime('%Y%m%d')


def _ical_now():
    """Current UTC timestamp in iCal format."""
    return datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


@login_required
def ical_feed(request):
    """
    Export tasks as an iCalendar (.ics) feed.
    Each task becomes an all-day VEVENT spanning start_date → end_date.
    Users can subscribe to this URL in Google Calendar or any other app.
    """
    user = request.user
    qs = Task.objects.select_related('assigned_to', 'project').all()
    if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
        qs = qs.filter(Q(assigned_to=user) | Q(project__assigned_users=user)).distinct()

    now_str = _ical_now()
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//IMS Project//Task Calendar//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:IMS Tasks',
        'X-WR-TIMEZONE:UTC',
    ]

    for task in qs:
        # Build a stable UID from the task pk
        uid = f'task-{task.pk}@ims-project'
        summary = _ical_escape(task.title)
        description_parts = []
        if task.description:
            description_parts.append(task.description)
        description_parts.append(f'Status: {task.get_status_display()}')
        description_parts.append(f'Priority: {task.get_priority_display()}')
        if task.assigned_to:
            description_parts.append(f'Assigned to: {task.assigned_to.name or task.assigned_to.email}')
        if task.project:
            description_parts.append(f'Project: {task.project.name}')
        description = _ical_escape('\n'.join(description_parts))

        # iCal all-day events: DTSTART = start_date, DTEND = end_date + 1 day (exclusive)
        from datetime import timedelta
        dtstart = _ical_datetime(task.start_date)
        dtend = _ical_datetime(task.end_date + timedelta(days=1))

        lines += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{now_str}',
            f'DTSTART;VALUE=DATE:{dtstart}',
            f'DTEND;VALUE=DATE:{dtend}',
            f'SUMMARY:{summary}',
            f'DESCRIPTION:{description}',
            f'STATUS:{"COMPLETED" if task.status == "COMPLETED" else "NEEDS-ACTION"}',
            'END:VEVENT',
        ]

    lines.append('END:VCALENDAR')

    content = '\r\n'.join(lines) + '\r\n'
    response = HttpResponse(content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ims-tasks.ics"'
    return response
