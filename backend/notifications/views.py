"""Notification list / mark-read / preferences endpoints."""

from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAuthenticatedEmployer

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedEmployer]
    filterset_fields = ["event"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        emp = getattr(self.request, "current_employer", None)
        if emp is None:
            return Notification.objects.none()
        return Notification.objects.filter(employer=emp)

    @extend_schema(
        responses=inline_serializer(
            name="NotificationUnread",
            fields={"unread": serializers.IntegerField()},
        )
    )
    @action(detail=False, methods=["get"])
    def unread(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"unread": count})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if notif.read_at is None:
            notif.read_at = timezone.now()
            notif.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = (
            self.get_queryset()
            .filter(read_at__isnull=True)
            .update(read_at=timezone.now())
        )
        return Response({"marked": updated})


class NotificationPreferenceView(APIView):
    """Singleton GET/PATCH for the caller's preferences."""

    permission_classes = [IsAuthenticatedEmployer]

    def _get_or_create(self, request) -> NotificationPreference:
        pref, _ = NotificationPreference.objects.get_or_create(
            employer=request.current_employer
        )
        return pref

    @extend_schema(responses={200: NotificationPreferenceSerializer})
    def get(self, request):
        pref = self._get_or_create(request)
        return Response(NotificationPreferenceSerializer(pref).data)

    @extend_schema(
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer},
    )
    def patch(self, request):
        pref = self._get_or_create(request)
        serializer = NotificationPreferenceSerializer(
            pref, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
