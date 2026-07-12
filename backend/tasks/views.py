"""ViewSets for tasks app."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.permissions import IsAuthenticatedEmployer, IsOwnerEmployer

from .models import TASK_TRANSITIONS, Task
from .serializers import TaskSerializer

log = logging.getLogger("baantask.tasks")


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD for tasks — scoped to the caller's employer."""

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedEmployer, IsOwnerEmployer]
    filterset_fields = ["status", "priority", "worker"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date", "priority"]

    # ---- queryset --------------------------------------------------------

    def get_queryset(self):
        emp = getattr(self.request, "current_employer", None)
        if emp is None:
            return Task.objects.none()
        return Task.objects.select_related("employer", "worker").filter(employer=emp)

    # ---- create + post-create side effects -------------------------------

    def perform_create(self, serializer):
        task = serializer.save()
        self._after_create(task)

    def _after_create(self, task: Task) -> None:
        """
        Cross-cutting work that fires *after* the task is committed.
        Translation and notifications are best-effort: each failure is
        logged but never propagates back to the API caller.
        """
        self._safely(self._kick_translation, task)
        self._safely(self._notify_created, task)

    @staticmethod
    def _safely(fn, task: Task) -> None:
        try:
            fn(task)
        except Exception:
            log.exception("post-create hook failed for task %s", task.id)

    @staticmethod
    def _kick_translation(task: Task) -> None:
        # Lazy import — keeps the dependency optional during tests.
        from translation.tasks import translate_task

        translate_task(task.id)

    @staticmethod
    def _notify_created(task: Task) -> None:
        from notifications.events import emit_task_created

        emit_task_created(task)

    # ---- transition (single source of truth for status changes) ----------

    def _apply_transition(self, task: Task, new_status: str) -> Task:
        if not new_status:
            raise ValidationError({"status": "This field is required."})
        with transaction.atomic():
            try:
                task.transition_to(new_status)
            except DjangoValidationError as exc:
                raise ValidationError({"status": exc.messages}) from exc
            task.save(update_fields=["status", "completed_at", "updated_at"])

        self._safely(self._notify_status_changed, task)
        return task

    @staticmethod
    def _notify_status_changed(task: Task) -> None:
        from notifications.events import emit_task_status_changed

        emit_task_status_changed(task)

    @extend_schema(
        request=inline_serializer(
            name="TaskTransitionRequest",
            fields={"status": drf_serializers.CharField()},
        ),
        responses={200: TaskSerializer},
        description=(
            "Move a task to a new status, validating the state machine " f"({TASK_TRANSITIONS})."
        ),
    )
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        task = self.get_object()
        new_status = (request.data or {}).get("status")
        task = self._apply_transition(task, new_status)
        return Response(self.get_serializer(task).data)

    @extend_schema(
        responses={200: TaskSerializer},
        description="Shortcut for `POST /tasks/{id}/transition/` with status=completed.",
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task = self._apply_transition(task, "completed")
        return Response(self.get_serializer(task).data)

    # ---- aggregate stats -------------------------------------------------

    @extend_schema(
        responses=inline_serializer(
            name="TaskStats",
            fields={
                "total": drf_serializers.IntegerField(),
                "by_status": drf_serializers.DictField(child=drf_serializers.IntegerField()),
                "by_priority": drf_serializers.DictField(child=drf_serializers.IntegerField()),
                "overdue": drf_serializers.IntegerField(),
            },
        )
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = self.get_queryset()

        by_status = {key: 0 for key, _ in Task.STATUS_CHOICES}
        for row in qs.values("status").annotate(c=Count("id")):
            by_status[row["status"]] = row["c"]

        by_priority = {key: 0 for key, _ in Task.PRIORITY_CHOICES}
        for row in qs.values("priority").annotate(c=Count("id")):
            by_priority[row["priority"]] = row["c"]

        overdue = (
            qs.filter(due_date__lt=timezone.now())
            .exclude(status__in=["completed", "verified"])
            .count()
        )

        return Response(
            {
                "total": qs.count(),
                "by_status": by_status,
                "by_priority": by_priority,
                "overdue": overdue,
            }
        )
