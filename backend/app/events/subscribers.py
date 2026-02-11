"""
Event subscriber handlers for async background processing.

These handlers are registered on the ``task.lifecycle`` topic at startup
and run as fire-and-forget ``asyncio`` tasks.  They MUST be idempotent
(safe to retry) and MUST NOT mutate the HTTP response — the chatbot has
already returned an immediate confirmation to the user.

Production note:
    When scaling beyond a single process, move these handlers into
    dedicated consumer microservices reading from Kafka / Redis Streams.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ── Date helpers ──────────────────────────────────────────────────────

_RECURRENCE_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),  # approximate; use dateutil for calendar-month
}


def _compute_next_due(current_due: Optional[str], recurrence: str) -> Optional[str]:
    """Return the next ISO-8601 due date string based on recurrence pattern.

    If *current_due* is ``None`` or *recurrence* is ``"none"``, returns ``None``.
    """
    if not current_due or recurrence == "none":
        return None
    delta = _RECURRENCE_DELTAS.get(recurrence)
    if delta is None:
        return None
    try:
        base = datetime.fromisoformat(current_due)
    except (ValueError, TypeError):
        return None
    return (base + delta).isoformat()


# ── Reminder Service ───────────────────────────────────────────────────

# In-process schedule store (replaced by APScheduler / Dapr in production)
_pending_reminders: dict = {}   # task_id → scheduled_time (ISO str)


async def reminder_subscriber(event: dict) -> None:
    """Schedule, update, or cancel reminders based on task lifecycle events.

    Reacts to:
        task.created  — schedule reminder if reminder_enabled + due_date
        task.updated  — reschedule / cancel based on new values
        task.deleted  — cancel any pending reminder
        task.completed — cancel reminder (task is done)
    """
    event_type = event.get("event_type")
    task_id = event.get("task_id")
    payload = event.get("payload", {})

    if event_type in ("task.created", "task.updated"):
        reminder_enabled = payload.get("reminder_enabled", False)
        due_date = payload.get("due_date")

        if reminder_enabled and due_date:
            _pending_reminders[task_id] = due_date
            logger.info(
                "[ReminderService] Scheduled reminder for task #%s at %s",
                task_id,
                due_date,
            )
        elif task_id in _pending_reminders:
            del _pending_reminders[task_id]
            logger.info(
                "[ReminderService] Cancelled reminder for task #%s (reminder_enabled=%s)",
                task_id,
                reminder_enabled,
            )

    elif event_type in ("task.deleted", "task.completed"):
        if task_id in _pending_reminders:
            del _pending_reminders[task_id]
            logger.info(
                "[ReminderService] Cleared reminder for task #%s (%s)",
                task_id,
                event_type,
            )


# ── Recurrence Service ─────────────────────────────────────────────────

async def recurrence_subscriber(event: dict) -> None:
    """Create the next instance of a recurring task when the current one
    is marked as completed.

    Reacts to:
        task.completed — if recurrence != 'none', compute next due date
                         and create a new task via MCPTaskService.

    The DB session is acquired lazily inside this handler so it runs
    independently of the HTTP request that triggered the event.
    """
    if event.get("event_type") != "task.completed":
        return

    payload = event.get("payload", {})
    recurrence = payload.get("recurrence", "none")

    if recurrence == "none":
        return

    task_id = event.get("task_id")
    user_id = event.get("user_id")
    title = payload.get("title", "Recurring task")
    due_date = payload.get("due_date")

    next_due = _compute_next_due(due_date, recurrence)

    logger.info(
        "[RecurrenceService] Task #%s completed (recurrence=%s). "
        "Creating next instance for user %s with due=%s.",
        task_id,
        recurrence,
        user_id,
        next_due,
    )

    try:
        # Lazy import to avoid circular dependency at module level
        from app.db.database import get_session
        from app.services.task_service import MCPTaskService

        session = next(get_session())
        try:
            result = MCPTaskService.add_task(
                session=session,
                user_id=user_id,
                title=f"{title} (recurring)",
                description=f"Auto-created from recurring task #{task_id}",
                priority=payload.get("priority", "medium"),
                tags=payload.get("tags"),
                due_date=(
                    datetime.fromisoformat(next_due) if next_due else None
                ),
                recurrence=recurrence,
                reminder_enabled=payload.get("reminder_enabled", False),
            )

            if result.get("status") == "success":
                new_id = result["task_id"]
                logger.info(
                    "[RecurrenceService] Created recurring task #%s from #%s",
                    new_id,
                    task_id,
                )

                # Publish the event for the newly created recurring task
                from app.events.event_bus import event_bus
                from app.events.event_types import TOPIC_TASK_LIFECYCLE
                if result.get("event"):
                    await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])
            else:
                logger.warning(
                    "[RecurrenceService] Failed to create recurring task: %s",
                    result.get("error", "unknown"),
                )
        finally:
            session.close()

    except Exception:
        logger.exception(
            "[RecurrenceService] Error creating recurring task from #%s", task_id
        )


# ── SSE Connection Manager ─────────────────────────────────────────────

import asyncio
import json

_sse_queues: dict[str, list[asyncio.Queue]] = {}  # user_id → list of queues


def sse_connect(user_id: str) -> asyncio.Queue:
    """Register an SSE client for a user. Returns the queue to read from."""
    q: asyncio.Queue = asyncio.Queue()
    _sse_queues.setdefault(user_id, []).append(q)
    logger.info("[SSE] Client connected for user %s (total=%d)", user_id, len(_sse_queues[user_id]))
    return q


def sse_disconnect(user_id: str, q: asyncio.Queue) -> None:
    """Unregister an SSE client."""
    queues = _sse_queues.get(user_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _sse_queues.pop(user_id, None)
    logger.info("[SSE] Client disconnected for user %s", user_id)


# ── Notification Service ───────────────────────────────────────────────

async def notification_subscriber(event: dict) -> None:
    """Fan-out user notifications for task lifecycle events.

    Reacts to:
        all event types — structured log for audit trail + SSE push

    Pushes events to all connected SSE clients for the affected user.
    """
    event_type = event.get("event_type")
    task_id = event.get("task_id")
    user_id = event.get("user_id")
    payload = event.get("payload", {})
    title = payload.get("title", "")
    timestamp = event.get("timestamp", "")

    logger.info(
        "[NotificationService] event=%s task=#%s title='%s' user=%s ts=%s",
        event_type,
        task_id,
        title,
        user_id,
        timestamp,
    )

    # Push to SSE clients for this user
    sse_event = {
        "event_type": event_type,
        "task_id": task_id,
        "user_id": user_id,
        "title": title,
        "timestamp": timestamp,
        "payload": payload,
    }
    for q in _sse_queues.get(user_id, []):
        try:
            q.put_nowait(sse_event)
        except asyncio.QueueFull:
            logger.warning("[SSE] Queue full for user %s, dropping event", user_id)
