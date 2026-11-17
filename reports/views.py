from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from notifications.utils import notify_user
from .models import AMCReport, ReportImage, InstallationReport, InstallationDocument
from .forms import AMCReportForm, ReportReviewForm, InstallationReportForm


class ReportListView(LoginRequiredMixin, ListView):
    model = AMCReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = AMCReport.objects.select_related('engineer', 'project').all()
        if not user.can_view_all_reports():
            qs = qs.filter(engineer=user)

        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        project = self.request.GET.get('project', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if q:
            qs = qs.filter(
                Q(project__name__icontains=q) | Q(work_done__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if project:
            qs = qs.filter(project_id=project)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        ctx['status_choices'] = AMCReport.Status.choices
        ctx['projects'] = Project.objects.filter(status='ONGOING')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_project'] = self.request.GET.get('project', '')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        return ctx


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = AMCReport
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        user = self.request.user
        qs = AMCReport.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(engineer=user)
        return qs


class ReportCreateView(LoginRequiredMixin, CreateView):
    model = AMCReport
    form_class = AMCReportForm
    template_name = 'reports/report_form.html'
    success_url = reverse_lazy('reports:report_list')

    def form_valid(self, form):
        form.instance.engineer = self.request.user
        response = super().form_valid(form)

        # Handle multiple image uploads
        for f in self.request.FILES.getlist('images'):
            ReportImage.objects.create(report=self.object, image=f)

        # Notify managers
        from users.models import User
        for mgr in User.objects.filter(role__in=['ADMIN', 'MANAGER'], is_active=True):
            notify_user(
                mgr,
                title="New AMC report submitted",
                message=f"{self.request.user.name} submitted report for {self.object.project.name}",
                link=self.object.get_absolute_url(),
                category='REPORT',
            )
        messages.success(self.request, "AMC report submitted.")
        return response


class ReportUpdateView(LoginRequiredMixin, UpdateView):
    model = AMCReport
    form_class = AMCReportForm
    template_name = 'reports/report_form.html'

    def get_queryset(self):
        return AMCReport.objects.filter(
            engineer=self.request.user, status=AMCReport.Status.SUBMITTED,
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        for f in self.request.FILES.getlist('images'):
            ReportImage.objects.create(report=self.object, image=f)
        messages.success(self.request, "Report updated.")
        return response


@login_required
def review_report(request, pk):
    if not request.user.can_view_all_reports():
        messages.error(request, "No permission.")
        return redirect('reports:report_list')

    report = get_object_or_404(AMCReport, pk=pk)
    if request.method == 'POST':
        form = ReportReviewForm(request.POST, instance=report)
        if form.is_valid():
            r = form.save(commit=False)
            r.reviewed_by = request.user
            r.reviewed_at = timezone.now()
            r.save()
            notify_user(
                report.engineer,
                title=f"Report {r.get_status_display()}",
                message=r.review_note,
                link=report.get_absolute_url(),
                category='REPORT',
            )
            messages.success(request, "Report reviewed.")
            return redirect('reports:report_detail', pk=pk)
    else:
        form = ReportReviewForm(instance=report)

    return render(request, 'reports/report_review.html', {'report': report, 'form': form})


# ---------------------------------------------------------------------------
# Installation Log (simple, no approval workflow)
# ---------------------------------------------------------------------------

class InstallationListView(LoginRequiredMixin, ListView):
    model = InstallationReport
    template_name = 'reports/installation_list.html'
    context_object_name = 'installations'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = InstallationReport.objects.select_related('installed_by', 'project').all()
        if not user.can_view_all_reports():
            qs = qs.filter(installed_by=user)

        q = self.request.GET.get('q', '')
        project = self.request.GET.get('project', '')
        if q:
            qs = qs.filter(Q(project__name__icontains=q) | Q(notes__icontains=q))
        if project:
            qs = qs.filter(project_id=project)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from projects.models import Project
        ctx['projects'] = Project.objects.all()
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_project'] = self.request.GET.get('project', '')
        return ctx


class InstallationDetailView(LoginRequiredMixin, DetailView):
    model = InstallationReport
    template_name = 'reports/installation_detail.html'
    context_object_name = 'installation'

    def get_queryset(self):
        user = self.request.user
        qs = InstallationReport.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(installed_by=user)
        return qs


class InstallationCreateView(LoginRequiredMixin, CreateView):
    model = InstallationReport
    form_class = InstallationReportForm
    template_name = 'reports/installation_form.html'
    success_url = reverse_lazy('reports:installation_list')

    def form_valid(self, form):
        form.instance.installed_by = self.request.user
        response = super().form_valid(form)
        for f in self.request.FILES.getlist('documents'):
            InstallationDocument.objects.create(installation=self.object, file=f)
        messages.success(self.request, "Installation logged.")
        return response


class InstallationUpdateView(LoginRequiredMixin, UpdateView):
    model = InstallationReport
    form_class = InstallationReportForm
    template_name = 'reports/installation_form.html'
    success_url = reverse_lazy('reports:installation_list')

    def get_queryset(self):
        return InstallationReport.objects.filter(installed_by=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        for f in self.request.FILES.getlist('documents'):
            InstallationDocument.objects.create(installation=self.object, file=f)
        messages.success(self.request, "Installation updated.")
        return response


class InstallationDeleteView(LoginRequiredMixin, DeleteView):
    model = InstallationReport
    template_name = 'reports/installation_confirm_delete.html'
    success_url = reverse_lazy('reports:installation_list')

    def get_queryset(self):
        user = self.request.user
        qs = InstallationReport.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(installed_by=user)
        return qs
