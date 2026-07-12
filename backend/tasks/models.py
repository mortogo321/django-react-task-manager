"""Task management models — core feature of Task Manager."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from workers.models import Employer, Worker

# Forward-only state machine. `verified` is the terminal state.
TASK_TRANSITIONS: dict[str, list[str]] = {
    "created": ["assigned", "in_progress"],
    "assigned": ["in_progress", "created"],
    "in_progress": ["completed"],
    "completed": ["verified", "in_progress"],
    "verified": [],
}


class Task(models.Model):
    """A task assigned by an employer to a worker."""

    STATUS_CHOICES = [
        ("created", "Created"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("verified", "Verified"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    description_th = models.TextField(
        blank=True,
        help_text="Auto-translated Thai description (Day 4)",
    )
    title_th = models.CharField(
        max_length=400,
        blank=True,
        help_text="Auto-translated Thai title (Day 4)",
    )
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="tasks")
    worker = models.ForeignKey(
        Worker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employer", "status"]),
            models.Index(fields=["worker", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in TASK_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str) -> None:
        """
        Validate and apply a status transition. Stamps `completed_at`
        when entering `completed`. Raises ValidationError on illegal moves.
        """
        if new_status == self.status:
            return
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot change status from '{self.status}' to '{new_status}'.")
        self.status = new_status
        if new_status == "completed" and self.completed_at is None:
            self.completed_at = timezone.now()
        if new_status in ("created", "assigned", "in_progress"):
            # Re-opening a task clears the previous completion stamp.
            self.completed_at = None

    def clean(self):
        super().clean()
        if self.worker_id and self.worker.employer_id != self.employer_id:
            raise ValidationError({"worker": "Worker does not belong to this employer."})
        # Existing tasks may end up with past due dates over time;
        # only enforce on first save.
        if self.due_date and self.due_date < timezone.now() and self._state.adding:
            raise ValidationError({"due_date": "Due date cannot be in the past."})
