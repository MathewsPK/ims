from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from core.models import ActivityLog, log_activity
from notifications.utils import notify_all_active
from users.permissions import ManagerOrAdminMixin
from .models import AMCProject, Equipment
from .forms import AMCProjectForm, EquipmentForm


class AMCListView(LoginRequiredMixin, ListView):
    model = AMCProject
    template_name = 'amc/amc_list.html'
    context_object_name = 'amc_projects'
    paginate_by = 20

    def get_queryset(self):
        qs = AMCProject.objects.select_related('project').all()
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        if q:
            qs = qs.filter(
                Q(project__name__icontains=q) | Q(contract_number__icontains=q)
            )
        if status == 'active':
            today = timezone.now().date()
            qs = qs.filter(amc_start_date__lte=today, amc_end_date__gte=today)
        elif status == 'expired':
            today = timezone.now().date()
            qs = qs.filter(amc_end_date__lt=today)
        elif status == 'expiring':
            from datetime import timedelta
            today = timezone.now().date()
            qs = qs.filter(amc_end_date__gte=today, amc_end_date__lte=today + timedelta(days=30))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        from datetime import timedelta
        today = timezone.now().date()
        ctx['expiring_count'] = AMCProject.objects.filter(
            amc_end_date__gte=today, amc_end_date__lte=today + timedelta(days=30)
        ).count()
        ctx['expired_count'] = AMCProject.objects.filter(amc_end_date__lt=today).count()
        return ctx


class AMCDetailView(LoginRequiredMixin, DetailView):
    model = AMCProject
    template_name = 'amc/amc_detail.html'
    context_object_name = 'amc'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['equipment_list'] = self.object.equipment.all()
        ctx['today'] = timezone.now().date()
        from core.models import ActivityLog
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(AMCProject)
        ctx['timeline'] = ActivityLog.objects.filter(
            content_type=ct, object_id=self.object.pk
        )[:20]
        return ctx


class AMCCreateView(ManagerOrAdminMixin, CreateView):
    model = AMCProject
    form_class = AMCProjectForm
    template_name = 'amc/amc_form.html'
    success_url = reverse_lazy('amc:amc_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(
            self.request.user, ActivityLog.Action.CREATED,
            f"Created AMC contract for '{self.object.project.name}'", self.object,
        )
        messages.success(self.request, "AMC contract created.")
        return response


class AMCUpdateView(ManagerOrAdminMixin, UpdateView):
    model = AMCProject
    form_class = AMCProjectForm
    template_name = 'amc/amc_form.html'
    success_url = reverse_lazy('amc:amc_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(
            self.request.user, ActivityLog.Action.UPDATED,
            f"Updated AMC contract for '{self.object.project.name}'", self.object,
        )
        messages.success(self.request, "AMC contract updated.")
        return response


class AMCDeleteView(ManagerOrAdminMixin, DeleteView):
    model = AMCProject
    template_name = 'amc/amc_confirm_delete.html'
    success_url = reverse_lazy('amc:amc_list')


class EquipmentDetailView(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = 'amc/equipment_detail.html'
    context_object_name = 'eq'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['today'] = timezone.now().date()
        return ctx


class EquipmentCreateView(ManagerOrAdminMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'amc/equipment_form.html'

    def get_success_url(self):
        return reverse_lazy('amc:amc_detail', kwargs={'pk': self.object.amc_project.pk})

    def form_valid(self, form):
        messages.success(self.request, "Equipment added.")
        return super().form_valid(form)


class EquipmentUpdateView(ManagerOrAdminMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'amc/equipment_form.html'

    def get_success_url(self):
        return reverse_lazy('amc:amc_detail', kwargs={'pk': self.object.amc_project.pk})


class EquipmentDeleteView(ManagerOrAdminMixin, DeleteView):
    model = Equipment
    template_name = 'amc/equipment_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('amc:amc_detail', kwargs={'pk': self.object.amc_project.pk})


# ---------------------------------------------------------------------------
# CSV Import (web UI)
# ---------------------------------------------------------------------------

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import csv
import io


@login_required
def import_csv_view(request):
    """Upload a CSV file and import equipment records (myth db format)."""
    if not (request.user.is_superuser or request.user.role in ('ADMIN', 'MANAGER')):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    results = None
    errors = []

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        dry_run = 'dry_run' in request.POST

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a .csv file.')
            return render(request, 'amc/import_csv.html', {'results': None})

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)
        except Exception as e:
            messages.error(request, f'Could not read file: {e}')
            return render(request, 'amc/import_csv.html', {'results': None})

        # Run through the same importer used by the management command
        from core.management.commands.import_data import (
            Command as ImportCommand, clean, parse_date,
        )
        from projects.models import Project
        from .models import AMCProject, Equipment
        from users.models import User
        from datetime import date as date_cls

        admin = (
            User.objects.filter(role='ADMIN').first()
            or User.objects.filter(is_superuser=True).first()
        )

        project_cache = {}
        amc_cache = {}
        results = {'created': 0, 'skipped': 0, 'errors': []}

        for i, row in enumerate(rows, 1):
            # normalise column names
            row = {k.strip().rstrip('.').lower().replace(' ', '_'): v for k, v in row.items()}

            eq_name = clean(row.get('name'))
            if not eq_name:
                results['skipped'] += 1
                continue

            proj_name   = clean(row.get('project'))
            client_name = clean(row.get('client')) or 'Unknown'

            if not proj_name:
                results['errors'].append(f'Row {i} ({eq_name}): missing project column')
                results['skipped'] += 1
                continue

            try:
                if proj_name not in project_cache:
                    proj, _ = Project.objects.get_or_create(
                        name=proj_name,
                        defaults={
                            'client': client_name,
                            'start_date': date_cls.today(),
                            'status': 'ONGOING',
                            'created_by': admin,
                        },
                    ) if not dry_run else (
                        Project.objects.filter(name=proj_name).first()
                        or Project(name=proj_name, client=client_name,
                                   start_date=date_cls.today(), status='ONGOING'),
                        False,
                    )
                    project_cache[proj_name] = proj
                project = project_cache[proj_name]

                contract_no = clean(row.get('amc_contract_number')) or ''
                amc_key = (getattr(project, 'pk', proj_name), contract_no)

                if amc_key not in amc_cache:
                    amc_end   = parse_date(row.get('amc_end_date'))
                    amc_start = parse_date(row.get('amc_date')) or date_cls.today()
                    amc_end   = amc_end or amc_start
                    if not dry_run:
                        amc, _ = AMCProject.objects.get_or_create(
                            project=project,
                            contract_number=contract_no,
                            defaults={
                                'amc_start_date': amc_start,
                                'amc_end_date':   amc_end,
                                'notes':          clean(row.get('notes')) or '',
                            },
                        )
                    else:
                        amc = AMCProject.objects.filter(
                            project=project, contract_number=contract_no
                        ).first()
                    amc_cache[amc_key] = amc

                amc = amc_cache[amc_key]
                if amc is None:
                    results['errors'].append(f'Row {i}: AMC contract could not be resolved')
                    results['skipped'] += 1
                    continue

                serial = clean(row.get('serial_number')) or ''
                if not dry_run:
                    _, created = Equipment.objects.get_or_create(
                        amc_project=amc,
                        name=eq_name,
                        serial_number=serial,
                        defaults={
                            'brand':             clean(row.get('brand'))        or '',
                            'model_number':      clean(row.get('model_number')) or '',
                            'location':          clean(row.get('location'))     or '',
                            'installation_date': parse_date(row.get('installation_date')),
                            'warranty_expiry':   parse_date(row.get('warranty_expiry')),
                            'amc_date':          parse_date(row.get('amc_date')),
                            'amc_end_date':      parse_date(row.get('amc_end_date')),
                            'invoice_date':      parse_date(row.get('invoice_date')),
                            'invoice_no':        clean(row.get('invoice_no'))   or '',
                            'win_license':       clean(row.get('win_license'))  or '',
                            'notes':             clean(row.get('notes'))        or '',
                        },
                    )
                    if created:
                        results['created'] += 1
                    else:
                        results['skipped'] += 1
                else:
                    results['created'] += 1   # pretend for dry run

            except Exception as e:
                results['errors'].append(f'Row {i} ({eq_name}): {e}')
                results['skipped'] += 1

        results['dry_run'] = dry_run
        results['total'] = len(rows)
        if not dry_run and results['created']:
            messages.success(request, f"Imported {results['created']} equipment records successfully.")

    return render(request, 'amc/import_csv.html', {'results': results})
