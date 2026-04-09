"""Serializers for tasks app."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Task

MAX_DESCRIPTION_CHARS = 5_000


class TaskSerializer(serializers.ModelSerializer):
    """
    Status changes go through `Task.transition_to()` so the state
    machine and `completed_at` stamping live in exactly one place.
    Direct PATCH `{"status": ...}` is supported, validated, and
    bookkeeping fields are kept in sync.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    worker_name = serializers.CharField(
        source="worker.full_name", read_only=True, default=None
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "title_th",
            "description",
            "description_th",
            "employer",
            "worker",
            "worker_name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "due_date",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["completed_at", "title_th", "description_th"]

    # ---- field-level validation ------------------------------------------

    def validate_title(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Title is required.")
        return value

    def validate_description(self, value: str) -> str:
        if value and len(value) > MAX_DESCRIPTION_CHARS:
            raise serializers.ValidationError(
                f"Description must be at most {MAX_DESCRIPTION_CHARS} characters."
            )
        return value

    # ---- cross-field validation ------------------------------------------

    def validate(self, data):
        request = self.context.get("request")
        target_employer = data.get("employer") or (
            self.instance.employer if self.instance else None
        )

        if request is not None and request.current_employer is not None:
            if target_employer and target_employer.pk != request.current_employer.pk:
                raise serializers.ValidationError(
                    {"employer": "Cannot create tasks for another employer."}
                )
            data["employer"] = request.current_employer

        worker = data.get("worker") or (self.instance.worker if self.instance else None)
        if worker and worker.employer_id != data["employer"].pk:
            raise serializers.ValidationError(
                {"worker": "Worker does not belong to this employer."}
            )

        # State-machine check happens in `update()` so the model is
        # the only source of truth. We just early-reject obvious bad
        # values for a nicer error message.
        return data

    # ---- write path ------------------------------------------------------

    def update(self, instance: Task, validated_data: dict) -> Task:
        new_status = validated_data.pop("status", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if new_status is not None and new_status != instance.status:
            try:
                instance.transition_to(new_status)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"status": exc.messages}) from exc
        instance.save()
        return instance
