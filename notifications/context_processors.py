from .models import Notification


def unread_notifications(request):
    """
    Injects `unread_count` and the 5 most recent unread notifications
    into every template context for authenticated users.
    """
    if not request.user.is_authenticated:
        return {'unread_count': 0, 'recent_notifications': []}

    qs = Notification.objects.filter(user=request.user, is_read=False)
    return {
        'unread_count': qs.count(),
        'recent_notifications': qs[:5],
    }
