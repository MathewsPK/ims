from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.permissions import manager_or_admin

from . import runner
from .models import TenderRun


@manager_or_admin
def home(request):
    rows, error = runner.open_tenders()
    q = request.GET.get('q', '').strip().lower()
    label = request.GET.get('label', '')
    portal = request.GET.get('portal', '')
    portals = sorted({r['portal_name'] for r in rows})
    if q:
        rows = [r for r in rows if q in (r['title'] + ' ' + r['authority']).lower()]
    if label:
        rows = [r for r in rows if r['label'] == label]
    if portal:
        rows = [r for r in rows if r['portal_name'] == portal]
    return render(request, 'tenders/home.html', {
        'tenders': rows,
        'tenders_error': error,
        'config_problem': runner.check_config(),
        'active': runner.active_run(),
        'runs': TenderRun.objects.select_related('triggered_by')[:10],
        'portals': portals, 'q': request.GET.get('q', ''), 'selected_label': label, 'selected_portal': portal,
        'urgent_count': sum(1 for r in rows if r['urgent']),
    })


@manager_or_admin
@require_POST
def start(request):
    kind = request.POST.get('kind', TenderRun.Kind.SEARCH)
    if kind not in TenderRun.Kind.values:
        kind = TenderRun.Kind.SEARCH
    try:
        run = runner.start_run(kind, request.user)
    except runner.RunInProgress as e:
        messages.warning(request, str(e))
        return redirect('tenders:run_detail', pk=e.run.pk)
    except runner.RadarNotConfigured as e:
        messages.error(request, f"Tender Radar is not set up on this server: {e}")
        return redirect('tenders:home')
    if kind == TenderRun.Kind.SEARCH:
        messages.success(request, "Search started. It takes a few minutes; the email goes out when it finishes.")
    else:
        messages.success(request, "Re-sending the current list of open tenders.")
    return redirect('tenders:run_detail', pk=run.pk)


@manager_or_admin
def run_detail(request, pk):
    run = get_object_or_404(TenderRun.objects.select_related('triggered_by'), pk=pk)
    return render(request, 'tenders/run_detail.html', {'run': run})


@manager_or_admin
def run_status(request, pk):
    run = get_object_or_404(TenderRun, pk=pk)
    return JsonResponse({
        'status': run.status, 'status_display': run.get_status_display(), 'active': run.is_active,
        'summary': run.summary, 'log_tail': "\n".join(run.log.splitlines()[-25:]), 'duration': run.duration,
    })
