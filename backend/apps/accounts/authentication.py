from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Use Django sessions for authenticated API requests, but skip DRF's CSRF
    enforcement. This keeps the SPA flow simple while the frontend and backend
    are running as separate development origins.
    """

    def enforce_csrf(self, request):
        return
