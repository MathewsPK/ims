from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
    PasswordChangeView, PasswordChangeDoneView,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.db.models import Q

from .models import User
from .forms import (
    EmailAuthenticationForm, UserRegistrationForm,
    UserProfileForm, UserAdminEditForm,
)
from .permissions import AdminRequiredMixin, admin_required


# -------------------- Auth views --------------------

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    next_page = 'users:login'


class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:password_change_done')


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'users/password_change_done.html'


# -------------------- Profile --------------------

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile.html', {'form': form})


# -------------------- Admin user management --------------------

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        if role:
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['role_choices'] = User.Role.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_role'] = self.request.GET.get('role', '')
        return ctx


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        messages.success(self.request, "User created successfully.")
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminEditForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        messages.success(self.request, "User updated successfully.")
        return super().form_valid(form)


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        messages.success(self.request, "User deleted.")
        return super().form_valid(form)


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'viewed_user'
