"""Serializers for workers app."""

from rest_framework import serializers

from .models import Employer, Worker


class EmployerSerializer(serializers.ModelSerializer):
    worker_count = serializers.IntegerField(read_only=True)
    worker_limit = serializers.IntegerField(read_only=True)
    plan_price_thb = serializers.IntegerField(read_only=True)

    class Meta:
        model = Employer
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "preferred_language",
            "plan",
            "worker_count",
            "worker_limit",
            "plan_price_thb",
            "created_at",
            "updated_at",
        ]


class WorkerSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source="employer.full_name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Worker
        fields = [
            "id",
            "first_name",
            "last_name",
            "nickname",
            "phone",
            "role",
            "role_display",
            "employer",
            "employer_name",
            "salary",
            "start_date",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]

    def validate_salary(self, value):
        if value < 0:
            raise serializers.ValidationError("Salary must be non-negative.")
        return value

    def validate(self, data):
        request = self.context.get("request")
        target_employer = data.get("employer") or (
            self.instance.employer if self.instance else None
        )
        # Force the employer to be the caller's own — never let an
        # employer create workers under someone else's account.
        if request is not None and request.current_employer is not None:
            if target_employer and target_employer.pk != request.current_employer.pk:
                raise serializers.ValidationError(
                    {"employer": "Cannot assign workers to another employer."}
                )
            data["employer"] = request.current_employer
        return data
