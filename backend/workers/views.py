"""ViewSets for workers app."""

from django.db import transaction
from django.db.models import Count, Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.permissions import IsAuthenticatedEmployer, IsOwnerEmployer

from .models import Employer, Worker
from .serializers import EmployerSerializer, WorkerSerializer


class EmployerViewSet(viewsets.ModelViewSet):
    """
    Employers can only see/edit themselves. The dashboard action is
    locked to the same employer (no IDOR).
    """

    serializer_class = EmployerSerializer
    permission_classes = [IsAuthenticatedEmployer, IsOwnerEmployer]
    filterset_fields = ["plan", "preferred_language"]
    search_fields = ["first_name", "last_name", "email"]

    def get_queryset(self):
        qs = Employer.objects.annotate(worker_count=Count("workers"))
        emp = getattr(self.request, "current_employer", None)
        if emp is None:
            return qs.none()
        # An employer always sees only themselves.
        return qs.filter(pk=emp.pk)

    @extend_schema(
        responses={200: WorkerSerializer(many=True)},
        description="List all workers belonging to this employer.",
    )
    @action(detail=True, methods=["get"])
    def workers(self, request, pk=None):
        employer = self.get_object()
        workers = employer.workers.select_related("employer").all()
        serializer = WorkerSerializer(workers, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        description=(
            "Private dashboard for the authenticated employer — billing, "
            "headcount, salary roll-up. Only the owner can call this."
        ),
        responses={200: OpenApiResponse(description="Dashboard payload")},
    )
    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        employer = self.get_object()  # IsOwnerEmployer guards this
        active_workers = employer.workers.filter(is_active=True)
        agg = active_workers.aggregate(total_salary=Sum("salary"), count=Count("id"))
        return Response(
            {
                "employer": {
                    "id": employer.id,
                    "name": employer.full_name,
                    "email": employer.email,
                    "phone": employer.phone,
                    "plan": employer.plan,
                },
                "billing": {
                    "plan_price_thb": employer.plan_price_thb,
                    "total_monthly_salary": float(agg["total_salary"] or 0),
                    "worker_count": agg["count"] or 0,
                    "worker_limit": employer.worker_limit,
                },
                "workers_summary": [
                    {
                        "id": w.id,
                        "name": w.full_name,
                        "role": w.role,
                        "salary": float(w.salary),
                        "phone": w.phone,
                    }
                    for w in active_workers
                ],
            }
        )


class WorkerViewSet(viewsets.ModelViewSet):
    """CRUD for workers — scoped to the caller's employer."""

    serializer_class = WorkerSerializer
    permission_classes = [IsAuthenticatedEmployer, IsOwnerEmployer]
    filterset_fields = ["role", "is_active"]
    search_fields = ["first_name", "last_name", "nickname"]
    ordering_fields = ["created_at", "salary", "first_name"]

    def get_queryset(self):
        emp = getattr(self.request, "current_employer", None)
        if emp is None:
            return Worker.objects.none()
        return Worker.objects.select_related("employer").filter(employer=emp)

    def perform_create(self, serializer):
        employer = self.request.current_employer
        if employer is None:
            raise PermissionDenied("Authentication required.")
        with transaction.atomic():
            locked = Employer.lock_for_update(employer.pk)
            try:
                locked.assert_can_add_worker()
            except Exception as exc:
                raise ValidationError(str(exc)) from exc
            serializer.save(employer=locked)

    def perform_update(self, serializer):
        employer = serializer.instance.employer
        with transaction.atomic():
            locked = Employer.lock_for_update(employer.pk)
            # If the worker is being reactivated, recheck the limit.
            new_active = serializer.validated_data.get("is_active", serializer.instance.is_active)
            if new_active and not serializer.instance.is_active:
                try:
                    locked.assert_can_add_worker(exclude_pk=serializer.instance.pk)
                except Exception as exc:
                    raise ValidationError(str(exc)) from exc
            serializer.save()
