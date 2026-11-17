"""
Role-based access control utilities.
Use as decorators on function-based views or mixins on class-based views.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin


def role_required(*roles):
    """Decorator: only allow users whose `role` is in the given list."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to access this page.")
        return _wrapped
    return decorator


def admin_required(view_func):
    return role_required('ADMIN')(view_func)


def manager_or_admin(view_func):
    return role_required('ADMIN', 'MANAGER')(view_func)


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Class-based view mixin. Set `allowed_roles` on the view.
    Example:
        class MyView(RoleRequiredMixin, ListView):
            allowed_roles = ['ADMIN', 'MANAGER']
    """
    allowed_roles = []

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.is_superuser or user.role in self.allowed_roles
        )


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['ADMIN']


class ManagerOrAdminMixin(RoleRequiredMixin):
    allowed_roles = ['ADMIN', 'MANAGER']
