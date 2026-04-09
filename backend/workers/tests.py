"""Worker app tests — limit, scoping, dashboard IDOR."""

from datetime import date, timedelta

import pytest

from workers.models import Employer, Worker


@pytest.mark.django_db
class TestWorkerLimit:
    def test_create_within_limit_succeeds(self, api, employer):
        resp = api.post(
            "/api/workers/",
            {
                "first_name": "Niran",
                "last_name": "S",
                "phone": "+66891111111",
                "role": "driver",
                "salary": "20000",
                "start_date": str(date.today() - timedelta(days=10)),
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data

    def test_exceeding_limit_is_rejected(self, api, employer):
        # employer plan = "home" → limit 3
        for i in range(3):
            Worker.objects.create(
                first_name=f"W{i}",
                last_name="X",
                phone="+6680000000",
                role="maid",
                employer=employer,
                salary=15_000,
                start_date=date.today(),
            )

        resp = api.post(
            "/api/workers/",
            {
                "first_name": "Overflow",
                "last_name": "Y",
                "phone": "+6680000001",
                "role": "cook",
                "salary": "15000",
                "start_date": str(date.today()),
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "worker limit" in str(resp.data).lower()


@pytest.mark.django_db
class TestWorkerScoping:
    def test_caller_only_sees_own_workers(self, api, api_other, worker, other_employer):
        Worker.objects.create(
            first_name="Other",
            last_name="W",
            phone="+6680000099",
            role="cook",
            employer=other_employer,
            salary=10_000,
            start_date=date.today(),
        )
        own = api.get("/api/workers/").data["results"]
        other = api_other.get("/api/workers/").data["results"]
        assert {w["first_name"] for w in own} == {worker.first_name}
        assert {w["first_name"] for w in other} == {"Other"}

    def test_cannot_create_worker_for_another_employer(
        self, api, other_employer
    ):
        resp = api.post(
            "/api/workers/",
            {
                "first_name": "Hijack",
                "last_name": "Y",
                "phone": "+6680000002",
                "role": "guard",
                "employer": other_employer.id,
                "salary": "10000",
                "start_date": str(date.today()),
            },
            format="json",
        )
        # Either 400 (validation) — viewset overrides employer to caller's
        assert resp.status_code in (201, 400)
        if resp.status_code == 201:
            # If accepted, the employer must have been forced to the caller
            assert resp.data["employer"] != other_employer.id


@pytest.mark.django_db
class TestEmployerDashboard:
    def test_dashboard_idor_blocked(self, api, api_other, employer, other_employer):
        # api is employer, api_other is other_employer
        own = api.get(f"/api/employers/{employer.id}/dashboard/")
        assert own.status_code == 200

        cross = api_other.get(f"/api/employers/{employer.id}/dashboard/")
        assert cross.status_code in (403, 404)

    def test_dashboard_aggregates_active_workers_only(self, api, employer, worker):
        # Add an inactive worker — the salary roll-up must exclude it.
        Worker.objects.create(
            first_name="Inactive",
            last_name="X",
            phone="+6680000098",
            role="cook",
            employer=employer,
            salary=99_999,
            start_date=date.today(),
            is_active=False,
        )
        resp = api.get(f"/api/employers/{employer.id}/dashboard/")
        assert resp.status_code == 200
        assert resp.data["billing"]["total_monthly_salary"] == float(worker.salary)
        assert resp.data["billing"]["worker_count"] == 1
        assert resp.data["billing"]["plan_price_thb"] == 599  # home plan


@pytest.mark.django_db
class TestThrottleAndPermissions:
    def test_anon_request_is_blocked(self, api_anon):
        resp = api_anon.get("/api/workers/")
        assert resp.status_code == 403

    def test_unknown_employer_id_is_blocked(self):
        from rest_framework.test import APIClient

        client = APIClient()
        client.credentials(HTTP_X_EMPLOYER_ID="999999", HTTP_X_USER_ROLE="employer")
        resp = client.get("/api/workers/")
        assert resp.status_code == 403
