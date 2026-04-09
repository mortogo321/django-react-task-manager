"""Task app tests — state machine, scoping, transitions, stats."""

from datetime import timedelta

import pytest
from django.utils import timezone

from tasks.models import Task


# ---- model: state machine -------------------------------------------------


class TestTaskTransitions:
    def test_created_can_become_assigned(self, task):
        assert task.can_transition_to("assigned")
        task.transition_to("assigned")
        assert task.status == "assigned"

    def test_in_progress_to_completed_stamps_completed_at(self, task):
        task.status = "in_progress"
        task.transition_to("completed")
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_completed_to_verified_is_terminal(self, task):
        task.status = "completed"
        task.completed_at = timezone.now()
        task.transition_to("verified")
        assert task.status == "verified"
        # `verified` is terminal — nothing flows out of it.
        assert not task.can_transition_to("completed")
        assert not task.can_transition_to("in_progress")

    def test_illegal_transition_raises(self, task):
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            task.transition_to("verified")  # created → verified is illegal

    def test_reopening_clears_completed_at(self, task):
        task.status = "completed"
        task.completed_at = timezone.now()
        task.transition_to("in_progress")
        assert task.completed_at is None


# ---- API: scoping ----------------------------------------------------------


@pytest.mark.django_db
class TestTaskScoping:
    def test_employer_only_sees_own_tasks(self, api, api_other, task, other_employer):
        # Create a task on the other employer.
        Task.objects.create(
            title="Other employer's task",
            employer=other_employer,
            status="created",
            priority="low",
        )

        own_resp = api.get("/api/tasks/")
        assert own_resp.status_code == 200
        own_titles = [t["title"] for t in own_resp.data["results"]]
        assert task.title in own_titles
        assert "Other employer's task" not in own_titles

        other_resp = api_other.get("/api/tasks/")
        other_titles = [t["title"] for t in other_resp.data["results"]]
        assert "Other employer's task" in other_titles
        assert task.title not in other_titles

    def test_anonymous_request_is_rejected(self, api_anon, task):
        resp = api_anon.get("/api/tasks/")
        assert resp.status_code == 403

    def test_cannot_retrieve_other_employers_task(self, api_other, task):
        resp = api_other.get(f"/api/tasks/{task.id}/")
        # 404 from queryset scoping (preferred over 403 to avoid existence leak)
        assert resp.status_code == 404


# ---- API: create + transition + complete -----------------------------------


@pytest.mark.django_db
class TestTaskApi:
    def test_create_task_assigns_caller_employer(self, api, employer, worker):
        resp = api.post(
            "/api/tasks/",
            {
                "title": "Mop the floor",
                "description": "kitchen and hallway",
                "worker": worker.id,
                "priority": "medium",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data
        task = Task.objects.get(pk=resp.data["id"])
        assert task.employer_id == employer.id

    def test_blank_title_rejected(self, api):
        resp = api.post("/api/tasks/", {"title": "  "}, format="json")
        assert resp.status_code == 400
        assert "title" in resp.data

    def test_transition_endpoint_validates_state_machine(self, api, task):
        # Illegal first: created → verified is not allowed.
        resp = api.post(
            f"/api/tasks/{task.id}/transition/",
            {"status": "verified"},
            format="json",
        )
        assert resp.status_code == 400

        # Legal walk: created → assigned → in_progress → completed → verified
        for next_status in ("assigned", "in_progress", "completed", "verified"):
            resp = api.post(
                f"/api/tasks/{task.id}/transition/",
                {"status": next_status},
                format="json",
            )
            assert resp.status_code == 200, (next_status, resp.data)
        task.refresh_from_db()
        assert task.status == "verified"
        assert task.completed_at is not None

    def test_patch_status_routes_through_state_machine(self, api, task):
        """PATCH must respect the state machine, not just write the field."""
        # Illegal direct PATCH is rejected.
        resp = api.patch(
            f"/api/tasks/{task.id}/", {"status": "verified"}, format="json"
        )
        assert resp.status_code == 400

        # Legal PATCH walk also stamps `completed_at`.
        for next_status in ("assigned", "in_progress", "completed"):
            resp = api.patch(
                f"/api/tasks/{task.id}/", {"status": next_status}, format="json"
            )
            assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_complete_action_stamps_completed_at(self, api, task):
        task.status = "in_progress"
        task.save(update_fields=["status"])
        resp = api.post(f"/api/tasks/{task.id}/complete/", format="json")
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_complete_action_rejects_illegal_state(self, api, task):
        resp = api.post(f"/api/tasks/{task.id}/complete/", format="json")
        assert resp.status_code == 400  # created → completed is illegal

    def test_stats_includes_overdue(self, api, employer, worker):
        Task.objects.create(
            title="Overdue task",
            employer=employer,
            worker=worker,
            status="in_progress",
            due_date=timezone.now() - timedelta(days=1),
        )
        resp = api.get("/api/tasks/stats/")
        assert resp.status_code == 200
        assert resp.data["overdue"] >= 1
        assert "by_status" in resp.data
        assert "by_priority" in resp.data
