"""
Middleware to stash the current request on the thread for audit logs.
Lets model signals access `request.user` without passing it explicitly.
"""
import threading

_local = threading.local()


def get_current_request():
    return getattr(_local, 'request', None)


def get_current_user():
    req = get_current_request()
    if req and hasattr(req, 'user') and req.user.is_authenticated:
        return req.user
    return None


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            _local.request = None
        return response
