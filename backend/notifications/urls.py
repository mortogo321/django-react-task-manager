from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationPreferenceView, NotificationViewSet

router = DefaultRouter()
router.register(r"items", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-prefs"),
]
