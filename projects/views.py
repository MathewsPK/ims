import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.contenttypes.models import ContentType

from core.models import ActivityLog, log_activity
from users.permissions import ManagerOrAdminMixin
from .models import Project, ProjectMedia
from .forms import ProjectForm, ProjectMediaForm


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12

    def get_queryset(self):
        qs = Project.objects.all()
        # Staff & Engineer only see projects they're assigned to
        user = self.request.user
        if not (user.is_superuser or user.role in ('ADMIN', 'MANAGER')):
            qs = qs.filter(assigned_users=user)

        # Search & filter
        q = self.request.GET.get('q', '').strip()
        # Default to Ongoing on a bare visit (no query params at all yet);
        # an explicit ?status=ALL (from the "All" tab) or any other value
        # overrides that default.
        if 'status' not in self.request.GET:
            status = Project.Status.ONGOING
        else:
            status = self.request.GET.get('status', '').strip()
            if status == 'ALL':
                status = ''
        self._effective_status = status
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(client__icontains=q) | Q(location__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)

        sort_map = {
            'start_asc':  'start_date',
            'start_desc': '-start_date',
            'end_asc':    'end_date',
            'end_desc':   '-end_date',
            'name_asc':   'name',
            'name_desc':  '-name',
        }
        sort = self.request.GET.get('sort', '').strip()
        order = sort_map.get(sort, '-created_at')
        return qs.distinct().order_by(order)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Project.Status.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = getattr(self, '_effective_status', self.request.GET.get('status', ''))
        ctx['selected_sort'] = self.request.GET.get('sort', '')
        return ctx


class OngoingProjectListView(ProjectListView):
    def get_queryset(self):
        return super().get_queryset().filter(status=Project.Status.ONGOING)


class CompletedProjectListView(ProjectListView):
    def get_queryset(self):
        return super().get_queryset().filter(status=Project.Status.COMPLETED)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        ct = ContentType.objects.get_for_model(Project)
        ctx['timeline'] = ActivityLog.objects.filter(
            content_type=ct, object_id=project.pk
        )[:50]
        ctx['media'] = project.media.all()
        ctx['tasks'] = project.tasks.all()[:10]
        ctx['media_form'] = ProjectMediaForm()
        return ctx


class ProjectCreateView(ManagerOrAdminMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(
            self.request.user, ActivityLog.Action.CREATED,
            f"Created project '{self.object.name}'", self.object,
        )
        messages.success(self.request, "Project created.")
        return response


class ProjectUpdateView(ManagerOrAdminMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(
            self.request.user, ActivityLog.Action.UPDATED,
            f"Updated project '{self.object.name}'", self.object,
        )
        messages.success(self.request, "Project updated.")
        return response


class ProjectDeleteView(ManagerOrAdminMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')

    def form_valid(self, form):
        name = self.get_object().name
        messages.success(self.request, f"Project '{name}' deleted.")
        return super().form_valid(form)


@login_required
def upload_project_media(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectMediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.project = project
            media.uploaded_by = request.user
            media.save()
            log_activity(
                request.user, ActivityLog.Action.UPLOADED,
                f"Uploaded image to '{project.name}'", project,
            )
            messages.success(request, "Image uploaded.")
    return redirect('projects:project_detail', pk=pk)


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    'id', 'name', 'client', 'location', 'status',
    'start_date', 'end_date', 'description',
    'created_at', 'updated_at', 'created_by',
    'assigned_users', 'progress_percent',
]


@login_required
def export_projects_csv(request):
    """Download all visible projects as a CSV file."""
    user = request.user
    if user.is_superuser or user.role in ('ADMIN', 'MANAGER'):
        qs = Project.objects.select_related('created_by').prefetch_related('assigned_users').all()
    else:
        qs = Project.objects.select_related('created_by').prefetch_related('assigned_users').filter(assigned_users=user)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="projects_export.csv"'

    writer = csv.writer(response)
    writer.writerow(CSV_FIELDS)

    for project in qs:
        assigned = '; '.join(
            u.name or u.email for u in project.assigned_users.all()
        )
        # Format timestamps in IST-friendly format
        created_at = project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else ''
        updated_at = project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else ''
        created_by = ''
        if project.created_by:
            created_by = project.created_by.name or project.created_by.email

        writer.writerow([
            project.pk,
            project.name,
            project.client,
            project.location,
            project.status,
            project.start_date.strftime('%Y-%m-%d') if project.start_date else '',
            project.end_date.strftime('%Y-%m-%d') if project.end_date else '',
            project.description,
            created_at,
            updated_at,
            created_by,
            assigned,
            project.progress_percent,
        ])

    return response


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

@login_required
def import_projects_csv(request):
    """Upload a CSV to create or update Project records."""
    if not (request.user.is_superuser or request.user.role in ('ADMIN', 'MANAGER')):
        raise PermissionDenied

    # Serve a blank sample template
    if request.GET.get('sample'):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="projects_sample.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'client', 'location', 'status',
                         'start_date', 'end_date', 'description'])
        writer.writerow(['Sample Project', 'Client Name', 'City',
                         'PLANNING', '2024-01-01', '2024-12-31', 'Optional description'])
        return response

    results = None

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        dry_run = 'dry_run' in request.POST

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a .csv file.')
            return render(request, 'projects/import_csv.html', {'results': None})

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)
        except Exception as e:
            messages.error(request, f'Could not read file: {e}')
            return render(request, 'projects/import_csv.html', {'results': None})

        from datetime import date as date_cls

        VALID_STATUSES = {s[0] for s in Project.Status.choices}
        results = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': [], 'dry_run': dry_run, 'total': len(rows)}

        for i, row in enumerate(rows, 1):
            # Normalise column names
            row = {k.strip().lower().replace(' ', '_'): (v or '').strip() for k, v in row.items()}

            name = row.get('name', '').strip()
            if not name:
                results['skipped'] += 1
                results['errors'].append(f'Row {i}: missing "name" — skipped.')
                continue

            client = row.get('client', '').strip() or 'Unknown'
            location = row.get('location', '').strip()
            description = row.get('description', '').strip()
            status_raw = row.get('status', 'PLANNING').strip().upper()
            status = status_raw if status_raw in VALID_STATUSES else 'PLANNING'

            # Parse dates
            def _parse_date(val):
                if not val:
                    return None
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
                    try:
                        from datetime import datetime
                        return datetime.strptime(val.strip(), fmt).date()
                    except ValueError:
                        continue
                return None

            start_date = _parse_date(row.get('start_date')) or date_cls.today()
            end_date = _parse_date(row.get('end_date'))

            try:
                existing = Project.objects.filter(name__iexact=name).first()
                if existing:
                    if not dry_run:
                        existing.client = client
                        existing.location = location
                        existing.description = description
                        existing.status = status
                        existing.start_date = start_date
                        if end_date:
                            existing.end_date = end_date
                        existing.save()
                    results['updated'] += 1
                else:
                    if not dry_run:
                        Project.objects.create(
                            name=name,
                            client=client,
                            location=location,
                            description=description,
                            status=status,
                            start_date=start_date,
                            end_date=end_date,
                            created_by=request.user,
                        )
                    results['created'] += 1
            except Exception as e:
                results['errors'].append(f'Row {i} ({name}): {e}')
                results['skipped'] += 1

        if not dry_run and (results['created'] or results['updated']):
            messages.success(
                request,
                f"Import complete: {results['created']} created, {results['updated']} updated."
            )

    return render(request, 'projects/import_csv.html', {'results': results})
