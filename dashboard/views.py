from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # ---- Tasks ----
    from tasks.models import Task
    task_qs = Task.objects.all()
    if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
        task_qs = task_qs.filter(
            Q(assigned_to=user) | Q(project__assigned_users=user)
        ).distinct()

    my_tasks = task_qs.filter(assigned_to=user)
    tasks_by_status = {
        'pending': my_tasks.filter(status='PENDING').count(),
        'in_progress': my_tasks.filter(status='IN_PROGRESS').count(),
        'completed': my_tasks.filter(status='COMPLETED').count(),
        'overdue': my_tasks.filter(status__in=['PENDING', 'IN_PROGRESS'], end_date__lt=today).count(),
    }
    upcoming_tasks = my_tasks.filter(
        status__in=['PENDING', 'IN_PROGRESS'],
        end_date__gte=today, end_date__lte=today + timedelta(days=7),
    ).order_by('end_date')[:5]

    # ---- Projects ----
    from projects.models import Project
    if user.is_superuser or user.role in ('ADMIN', 'MANAGER'):
        projects = Project.objects.all()
    else:
        projects = user.projects.all()

    projects_by_status = {
        'ongoing': projects.filter(status='ONGOING').count(),
        'planning': projects.filter(status='PLANNING').count(),
        'completed': projects.filter(status='COMPLETED').count(),
        'on_hold': projects.filter(status='ON_HOLD').count(),
    }
    recent_projects = projects.order_by('-created_at')[:5]

    # ---- AMC ----
    from amc.models import AMCProject
    amc_expiring = AMCProject.objects.filter(
        amc_end_date__gte=today,
        amc_end_date__lte=today + timedelta(days=30),
    ).select_related('project')[:5]
    amc_expired = AMCProject.objects.filter(amc_end_date__lt=today).count()

    # ---- Expenses ----
    from expenses.models import Expense
    exp_qs = Expense.objects.filter(user=user)
    my_monthly_spend = exp_qs.filter(date__gte=month_start).aggregate(
        total=Sum('amount')
    )['total'] or 0
    pending_expense_count = exp_qs.filter(approval_status='PENDING').count()

    # ---- Billing / Subscriptions (Admin/Manager only) ----
    subscriptions_due = []
    if user.is_superuser or user.role in ('ADMIN', 'MANAGER'):
        from billing.models import Subscription
        subscriptions_due = [
            s for s in Subscription.objects.filter(is_active=True).select_related('managed_by')
            if s.is_due_soon or s.is_overdue
        ][:5]

    # ---- Recent Activity ----
    from core.models import ActivityLog
    activity_qs = ActivityLog.objects.select_related('user')
    if not user.can_view_all_reports():
        activity_qs = activity_qs.filter(user=user)
    recent_activity = activity_qs[:10]

    # ---- Upcoming Events ----
    from notifications.models import NotificationEvent
    events_qs = NotificationEvent.objects.filter(event_datetime__gte=timezone.now())
    if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
        events_qs = events_qs.filter(Q(all_users=True) | Q(assigned_to=user))
    upcoming_events = events_qs.distinct().order_by('event_datetime')[:5]

    # ---- Reports ----
    from reports.models import AMCReport
    pending_reports = AMCReport.objects.filter(status='SUBMITTED').count() if user.can_view_all_reports() else 0

    # ---- Chart data: monthly expense categories (JSON for Chart.js) ----
    import json
    cat_data = (
        exp_qs.filter(date__gte=month_start)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_labels = [d['category'] for d in cat_data]
    chart_values = [float(d['total']) for d in cat_data]

    ctx = {
        'today': today,
        'tasks_by_status': tasks_by_status,
        'upcoming_tasks': upcoming_tasks,
        'projects_by_status': projects_by_status,
        'recent_projects': recent_projects,
        'amc_expiring': amc_expiring,
        'amc_expired': amc_expired,
        'my_monthly_spend': my_monthly_spend,
        'pending_expense_count': pending_expense_count,
        'subscriptions_due': subscriptions_due,
        'pending_reports': pending_reports,
        'recent_activity': recent_activity,
        'upcoming_events': upcoming_events,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'dashboard/dashboard.html', ctx)
