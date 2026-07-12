"""Core views — health checks and utilities."""

from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Public health check — DB + cache."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    _open_endpoint = True  # bypass IsAuthenticatedEmployer

    def get(self, request):
        db_ok = self._check_db()
        cache_ok = self._check_cache()

        status = "healthy" if db_ok and cache_ok else "degraded"
        http_status = 200 if status == "healthy" else 503

        return Response(
            {
                "status": status,
                "database": "ok" if db_ok else "error",
                "cache": "ok" if cache_ok else "error",
                "service": "Task Manager API",
                "version": "0.2.0",
            },
            status=http_status,
        )

    @staticmethod
    def _check_db() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    @staticmethod
    def _check_cache() -> bool:
        try:
            cache.set("__health__", "1", 5)
            return cache.get("__health__") == "1"
        except Exception:
            return False
