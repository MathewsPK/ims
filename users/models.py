from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Email-based user manager."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        # Username is auto-derived from email since the schema uses email as primary login
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with role-based access.
    Email is the login identifier; username is retained but auto-populated.
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        ENGINEER = 'ENGINEER', 'Engineer'
        STAFF = 'STAFF', 'Staff'

    email = models.EmailField('Email address', unique=True)
    name = models.CharField('Full name', max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    phone = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Always keep username in sync with email so the unique constraint never
        # fires on an empty/stale username value (e.g. when created via admin).
        if self.email:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or self.email} ({self.get_role_display()})"

    # Convenience role checks for templates/views
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_engineer(self):
        return self.role == self.Role.ENGINEER

    @property
    def is_staff_role(self):
        return self.role == self.Role.STAFF

    def can_manage_projects(self):
        return self.is_admin or self.is_manager

    def can_approve_expenses(self):
        return self.is_admin or self.is_manager

    def can_view_all_reports(self):
        return self.is_admin or self.is_manager
