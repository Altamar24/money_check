from django.shortcuts import redirect

_ALLOWED_PREFIXES = (
    '/login/',
    '/logout/',
    '/auth/',
    '/pricing/',
    '/payment/',
    '/admin/',
    '/static/',
)


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            if not any(request.path.startswith(p) for p in _ALLOWED_PREFIXES):
                sub = getattr(request.user, 'subscription', None)
                if not sub or not sub.is_active:
                    return redirect('/pricing/')
        return self.get_response(request)
