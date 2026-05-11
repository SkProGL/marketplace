import time

from django.db import DatabaseError
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth import get_user_model


User = get_user_model()

#class AutoLoginMiddleware:
#    def __init__(self, get_response):
#        self.get_response = get_response
#
#    def __call__(self, request):
#        if settings.DEBUG and not request.user.is_authenticated:
#            superuser = User.objects.filter(is_superuser=True).first()
#            if superuser:
#                login(request, superuser, backend='django.contrib.auth.backends.ModelBackend')
#        
#        response = self.get_response(request)
#        return response


# Path prefixes that should never be logged: too noisy or recursive
SKIP_PREFIXES = (
    '/static/',
    '/media/',
    '/admin/jsi18n/',
    '/__reload__/',
    '/favicon.ico',
    '/activity/',  # don't log views of the activity dashboard itself
)


def _classify_action(method, path):
    """Map (method, path) to an ActivityLog.Action value."""
    from core.models import ActivityLog
    A = ActivityLog.Action

    if path.startswith('/login') and method == 'POST':
        return A.LOGIN
    if path.startswith('/logout'):
        return A.LOGOUT
    if path.startswith('/signup') and method == 'POST':
        return A.SIGNUP
    if path.startswith('/add-to-cart/') and method == 'POST':
        return A.ADD_TO_CART
    if path.startswith('/cart/'):
        return A.CART_UPDATE
    if path.startswith('/checkout') and method == 'POST':
        return A.CHECKOUT
    if path.startswith('/order-confirmation/'):
        return A.ORDER_PLACED
    if path.startswith('/review/') and method == 'POST':
        return A.REVIEW
    if path.startswith('/community/') and method == 'POST':
        return A.COMMUNITY_POST
    return A.PAGE_VIEW


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Records one ActivityLog row per non-skipped request."""

    def process_request(self, request):
        request._activity_started_at = time.monotonic()

    def process_response(self, request, response):
        path = request.path
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return response

        # Failed login: form re-renders as 200, so look at the auth signal indirectly:
        # if the path is /login, method is POST, and user is still anonymous → failure.
        from core.models import ActivityLog
        action = _classify_action(request.method, path)
        if action == ActivityLog.Action.LOGIN and not request.user.is_authenticated:
            action = ActivityLog.Action.LOGIN_FAILED

        started = getattr(request, '_activity_started_at', None)
        duration_ms = int((time.monotonic() - started) * 1000) if started else None

        user = request.user if request.user.is_authenticated else None
        user_category = getattr(user, 'category', '') if user else ''

        # Synthetic traffic tags itself via header so the dashboard can split it out.
        is_synthetic = request.META.get('HTTP_X_SYNTHETIC_TRAFFIC') == '1'

        try:
            ActivityLog.objects.create(
                user=user,
                user_category=user_category or '',
                session_key=request.session.session_key or '',
                method=request.method,
                path=path[:255],
                status_code=response.status_code,
                duration_ms=duration_ms,
                action=action,
                ip_address=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                is_synthetic=is_synthetic,
            )
        except DatabaseError:
            # Never let logging break the response (e.g. migration not yet applied).
            pass

        return response
