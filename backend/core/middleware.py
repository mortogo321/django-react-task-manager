"""
Header-based dev authentication for BaanTask.

⚠️  This is intentionally simple — it trusts request headers and is meant
    only for the candidate-test environment. In production this layer
    must be replaced with a real auth backend (DRF Token, SimpleJWT, or
    session auth) and the headers stripped at the proxy.
"""

import logging

from workers.models import Employer

log = logging.getLogger("baantask.auth")


class SimpleAuthMiddleware:
    """
    Reads `X-Employer-Id` and `X-User-Role` from request headers and
    attaches `current_employer` and `user_role` to the request object.

    Both attributes are always set so views can rely on them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_employer = self._resolve_employer(request)
        request.user_role = self._resolve_role(request)
        return self.get_response(request)

    @staticmethod
    def _resolve_employer(request):
        raw = request.headers.get("X-Employer-Id")
        if not raw:
            return None
        try:
            return Employer.objects.get(pk=int(raw))
        except (Employer.DoesNotExist, ValueError, TypeError):
            log.debug("auth: unknown X-Employer-Id %r", raw)
            return None

    @staticmethod
    def _resolve_role(request):
        role = (request.headers.get("X-User-Role") or "").strip().lower()
        return role if role in {"employer", "worker"} else "employer"
