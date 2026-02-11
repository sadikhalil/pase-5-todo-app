"""
Event type constants and payload factory for task lifecycle events.

Topic layout (Dapr / Kafka compatible):
    task.lifecycle  — single topic carrying all task CRUD events

Event types:
    task.created    — a new task was added
    task.updated    — one or more fields on a task changed
    task.completed  — a task was toggled to completed
    task.deleted    — a task was removed
"""
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Topics ─────────────────────────────────────────────────────────────
TOPIC_TASK_LIFECYCLE = "task.lifecycle"

# ── Event types ────────────────────────────────────────────────────────
EVENT_TASK_CREATED = "task.created"
EVENT_TASK_UPDATED = "task.updated"
EVENT_TASK_COMPLETED = "task.completed"
EVENT_TASK_DELETED = "task.deleted"


def make_task_event(
    event_type: str,
    user_id: str,
    task_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standardised task lifecycle event envelope.

    Example output::

        {
            "event_type": "task.created",
            "user_id": "abc-123",
            "task_id": 42,
            "timestamp": "2026-02-09T14:30:00.000000",
            "payload": {
                "title": "Buy groceries",
                "priority": "high",
                "tags": ["shopping"],
                "recurrence": "none",
                "reminder_enabled": false
            }
        }
    """
    return {
        "event_type": event_type,
        "user_id": user_id,
        "task_id": task_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload or {},
    }
