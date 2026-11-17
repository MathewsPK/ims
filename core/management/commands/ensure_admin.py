"""
python manage.py ensure_admin

Creates a default admin account ONLY if the database has no users at all
(fresh install). Never touches an existing database.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create default admin account on a fresh (empty) database"

    def handle(self, *args, **kwargs):
        from users.models import User
        if User.objects.exists():
            self.stdout.write("Users already exist — nothing to do.")
            return
        u = User.objects.create(
            email="admin@ims.local",
            username="admin@ims.local",
            name="Admin",
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
        )
        u.set_password("admin123")
        u.save()
        self.stdout.write(self.style.SUCCESS(
            "Created admin@ims.local / admin123 — CHANGE THIS PASSWORD after first login."
        ))
