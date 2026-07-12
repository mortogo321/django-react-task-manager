"""Task Manager URL configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from core.views import HealthCheckView
from tasks.views import TaskViewSet
from workers.views import EmployerViewSet, WorkerViewSet

router = DefaultRouter()
router.register(r"workers", WorkerViewSet, basename="worker")
router.register(r"employers", EmployerViewSet, basename="employer")
router.register(r"tasks", TaskViewSet, basename="task")

api_urlpatterns = [
    path("", include(router.urls)),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("notifications/", include("notifications.urls")),
    path("translation/", include("translation.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_urlpatterns)),
]
