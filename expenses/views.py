from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from users.permissions import ManagerOrAdminMixin
from notifications.utils import notify_user
from .models import Expense
from .forms import ExpenseForm, ExpenseReviewForm


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.select_related('user', 'project').all()
        if not user.can_view_all_reports():
            qs = qs.filter(user=user)

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        category = self.request.GET.get('category', '')
        status = self.request.GET.get('status', '')
        emp = self.request.GET.get('user_id', '')

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if category:
            qs = qs.filter(category=category)
        if status:
            qs = qs.filter(approval_status=status)
        if emp and user.can_view_all_reports():
            qs = qs.filter(user_id=emp)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        ctx['total_amount'] = qs.aggregate(t=Sum('amount'))['t'] or 0
        ctx['category_choices'] = Expense.Category.choices
        ctx['status_choices'] = Expense.ApprovalStatus.choices
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.all()
        if not user.can_view_all_reports():
            qs = qs.filter(user=user)
        return qs


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        # Notify managers
        from users.models import User
        for mgr in User.objects.filter(role__in=['ADMIN', 'MANAGER'], is_active=True):
            notify_user(
                mgr,
                title="New expense submitted",
                message=f"{self.request.user.name} submitted ₹{self.object.amount} for review.",
                link=self.object.get_absolute_url(),
                category='EXPENSE',
            )
        messages.success(self.request, "Expense submitted for review.")
        return response


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user, approval_status='PENDING')

    def form_valid(self, form):
        messages.success(self.request, "Expense updated.")
        return super().form_valid(form)


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.all()
        if not user.is_admin:
            qs = qs.filter(user=user, approval_status='PENDING')
        return qs


@login_required
def review_expense(request, pk):
    """Admin/Manager review action."""
    if not request.user.can_approve_expenses():
        messages.error(request, "No permission.")
        return redirect('expenses:expense_list')

    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseReviewForm(request.POST, instance=expense)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.reviewed_by = request.user
            exp.reviewed_at = timezone.now()
            exp.save()
            notify_user(
                expense.user,
                title=f"Expense {exp.get_approval_status_display()}",
                message=exp.review_note,
                link=expense.get_absolute_url(),
                category='EXPENSE',
            )
            messages.success(request, "Expense reviewed.")
            return redirect('expenses:expense_list')
    else:
        form = ExpenseReviewForm(instance=expense)

    return render(request, 'expenses/expense_review.html',
                  {'expense': expense, 'form': form})
