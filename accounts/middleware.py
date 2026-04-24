from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from django.conf import settings


class SessionTimeoutMiddleware:
    """10 daqiqa harakatsizlikda avtomatik chiqish"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            timeout = getattr(settings, 'SESSION_COOKIE_AGE', 600)

            if last_activity:
                elapsed = (timezone.now().timestamp() - last_activity)
                if elapsed > timeout:
                    logout(request)
                    return redirect(settings.LOGIN_URL + '?timeout=1')

            request.session['last_activity'] = timezone.now().timestamp()

        return self.get_response(request)
