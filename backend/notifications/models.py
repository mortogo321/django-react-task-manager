"""
Notifications: a thin event log + per-employer preferences.
Day 5 feature.
"""

from django.db import models

from workers.models import Employer


class NotificationPreference(models.Model):
    """Per-employer toggles for which events fire notifications."""

    employer = models.OneToOneField(
        Employer, on_delete=models.CASCADE, related_name="notification_pref"
    )
    on_task_created = models.BooleanField(default=True)
    on_task_status_changed = models.BooleanField(default=True)
    on_task_completed = models.BooleanField(default=True)
    on_task_overdue = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.employer}"

    def is_enabled(self, event_type: str) -> bool:
        return bool(getattr(self, f"on_{event_type}", True))


class Notification(models.Model):
    """Append-only log of fired notifications."""

    EVENT_CHOICES = [
        ("task_created", "Task created"),
        ("task_status_changed", "Task status changed"),
        ("task_completed", "Task completed"),
        ("task_overdue", "Task overdue"),
    ]

    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="notifications")
    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employer", "read_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.event}: {self.title}"
