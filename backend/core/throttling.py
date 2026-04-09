"""Custom throttle that scopes by `current_employer` instead of user."""

from rest_framework.throttling import SimpleRateThrottle


class PerEmployerRateThrottle(SimpleRateThrottle):
    """
    Rate-limit per authenticated employer. Falls back to the IP address
    when no employer header is present (which the
    `IsAuthenticatedEmployer` permission rejects shortly after, but the
    throttle still protects the auth path itself).
    """

    scope = "employer"

    def get_cache_key(self, request, view):
        emp = getattr(request, "current_employer", None)
        if emp is not None:
            ident = f"emp:{emp.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
