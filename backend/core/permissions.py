"""
Permission classes for BaanTask.

Auth lives in `core.middleware.SimpleAuthMiddleware` (dev-only header
auth). `IsAuthenticatedEmployer` is the global default — it requires
the header to resolve to a real Employer and downgrades the `worker`
role to read-only. `IsOwnerEmployer` is an object-level check the
viewsets attach for retrieve/update/delete.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

# Local import is intentional — keeps the module importable from
# settings without app-loading races at startup.


class IsAuthenticatedEmployer(BasePermission):
    """Allow only requests carrying a resolved employer."""

    message = "Authentication required (set X-Employer-Id header)."

    def has_permission(self, request, view):
        if getattr(view, "_open_endpoint", False):
            return True
        if getattr(request, "current_employer", None) is None:
            return False
        if getattr(request, "user_role", "employer") == "worker":
            return request.method in SAFE_METHODS
        return True


class IsOwnerEmployer(BasePermission):
    """Object-level: the resource must belong to the caller's employer."""

    message = "You do not have access to this resource."

    def has_object_permission(self, request, view, obj):
        # Local import avoids circular dependency at app load.
        from workers.models import Employer

        emp = getattr(request, "current_employer", None)
        if emp is None:
            return False
        if isinstance(obj, Employer):
            return obj.pk == emp.pk
        return getattr(obj, "employer_id", None) == emp.pk
