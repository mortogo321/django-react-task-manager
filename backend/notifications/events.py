"""
Event emitters used by other apps.

Keeps notification logic out of business code: callers fire-and-forget,
this module decides whether to log a notification based on the
employer's preferences. Preference rows are auto-created on first read
and cached per process for the lifetime of the worker — they change
rarely and a small staleness window is acceptable.
"""

from __future__ import annotations

from functools import lru_cache
import logging

from .models import Notification, NotificationPreference

log = logging.getLogger("baantask.notifications")


@lru_cache(maxsize=1024)
def _pref_id_for(employer_id: int) -> int:
    pref, _ = NotificationPreference.objects.get_or_create(employer_id=employer_id)
    return pref.pk


def _pref_for(employer) -> NotificationPreference:
    """Cheap fast-path: cache id, then fetch a fresh row when needed."""
    return NotificationPreference.objects.get(pk=_pref_id_for(employer.pk))


def _emit(
    employer,
    event: str,
    title: str,
    body: str = "",
    payload: dict | None = None,
) -> None:
    pref = _pref_for(employer)
    if not pref.is_enabled(event):
        return
    Notification.objects.create(
        employer=employer,
        event=event,
        title=title,
        body=body,
        payload=payload or {},
    )
    log.info("notification: emp=%s event=%s title=%s", employer.pk, event, title)


def emit_task_created(task) -> None:
    _emit(
        task.employer,
        "task_created",
        title=f"New task: {task.title}",
        body=(task.description or "")[:200],
        payload={"task_id": task.id, "priority": task.priority},
    )


def emit_task_status_changed(task) -> None:
    event = "task_completed" if task.status == "completed" else "task_status_changed"
    _emit(
        task.employer,
        event,
        title=f"{task.title} → {task.get_status_display()}",
        payload={"task_id": task.id, "status": task.status},
    )
