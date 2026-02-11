"""
Event-driven infrastructure for the Todo application.

Provides an async pub/sub event bus with pluggable backends:
- InMemory (default, single-process)
- Redis Streams (production, multi-process)
- Dapr / Kafka (future, via adapter)
"""
from app.events.event_bus import event_bus
from app.events.event_types import (
    TOPIC_TASK_LIFECYCLE,
    EVENT_TASK_CREATED,
    EVENT_TASK_UPDATED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_DELETED,
    make_task_event,
)
from app.events.subscribers import sse_connect, sse_disconnect

__all__ = [
    "event_bus",
    "TOPIC_TASK_LIFECYCLE",
    "EVENT_TASK_CREATED",
    "EVENT_TASK_UPDATED",
    "EVENT_TASK_COMPLETED",
    "EVENT_TASK_DELETED",
    "make_task_event",
    "sse_connect",
    "sse_disconnect",
]
