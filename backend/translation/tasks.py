"""
Translation glue for tasks.

`translate_task` is **synchronous** today — the call runs inside the
request thread, bounded by `TRANSLATION_TIMEOUT`. Production should move
this onto a queue (Celery / Redis Streams); see
`docs/TRANSLATION_SCALING.md` for the migration plan. The public name is
deliberately neutral so callers don't grow assumptions about delivery
mode.
"""

from __future__ import annotations

import logging

from .service import translate

log = logging.getLogger("baantask.translation")


def translate_task(task_id: int) -> None:
    # Imported lazily to avoid a circular import with `tasks.models`.
    from tasks.models import Task

    try:
        task = Task.objects.select_related("employer").get(pk=task_id)
    except Task.DoesNotExist:
        return

    target = "th"  # Workers in BaanTask are Thai.
    source = task.employer.preferred_language or "en"

    if target == source:
        return

    update_fields: list[str] = []

    title_result = translate(task.title, target=target, source=source)
    if title_result.text and title_result.text != task.title_th:
        task.title_th = title_result.text
        update_fields.append("title_th")

    if task.description:
        desc_result = translate(task.description, target=target, source=source)
        if desc_result.text and desc_result.text != task.description_th:
            task.description_th = desc_result.text
            update_fields.append("description_th")

    if update_fields:
        task.save(update_fields=update_fields)
        log.info(
            "translated task %s (%s → %s, fields=%s)",
            task_id,
            source,
            target,
            update_fields,
        )
