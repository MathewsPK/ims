"""
Utility helpers for creating notifications.
Import-safe: no circular imports because we use get_user_model() lazily.
"""
from django.contrib.auth import get_user_model


def notify_user(user, title, message='', link='', category='SYSTEM'):
    """Create a single in-app notification for `user`."""
    from .models import Notification
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        link=link,
        category=category,
    )


def notify_users(users, title, message='', link='', category='SYSTEM'):
    """Bulk-create notifications for an iterable of users."""
    from .models import Notification
    objs = [
        Notification(user=u, title=title, message=message, link=link, category=category)
        for u in users
    ]
    Notification.objects.bulk_create(objs)


def notify_all_active(title, message='', link='', category='SYSTEM'):
    """Send a notification to every active user."""
    User = get_user_model()
    users = User.objects.filter(is_active=True)
    notify_users(users, title, message, link, category)


def notify_event(event):
    """
    Dispatch Notification rows for a NotificationEvent.
    Called when an event is created/updated.
    """
    User = get_user_model()
    if event.all_users:
        recipients = User.objects.filter(is_active=True)
    else:
        recipients = event.assigned_to.filter(is_active=True)

    link = event.get_absolute_url()
    notify_users(
        recipients,
        title=f"[{event.get_event_type_display()}] {event.title}",
        message=event.description,
        link=link,
        category=event.event_type,
    )
