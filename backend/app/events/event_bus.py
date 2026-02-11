"""
Async event bus with pluggable backends.

Default backend is **InMemory** (asyncio tasks, single-process).
Set EVENT_BUS_BACKEND=redis to use Redis Streams for multi-process fan-out.

The interface mirrors Dapr pub/sub semantics so swapping to Dapr or Kafka
later requires only a new backend class — no changes to publishers or
subscribers.
"""
import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    """Single-process async event bus using ``asyncio.create_task``."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subscribers.setdefault(topic, []).append(handler)
        logger.info("EventBus: subscribed %s to '%s'", handler.__name__, topic)

    async def publish(self, topic: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Publish *event* to *topic*.  Returns the enriched event dict."""
        event["topic"] = topic
        logger.info(
            "EventBus: publishing %s to '%s' (task_id=%s)",
            event.get("event_type", "?"),
            topic,
            event.get("task_id"),
        )
        for handler in self._subscribers.get(topic, []):
            asyncio.create_task(self._safe_dispatch(handler, event))
        return event

    @staticmethod
    async def _safe_dispatch(handler: Callable, event: Dict[str, Any]) -> None:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception:
            logger.exception("EventBus: subscriber %s failed", handler.__name__)


class RedisEventBus:
    """Multi-process event bus backed by Redis Streams.

    Requires the ``redis`` package (``pip install redis``).
    Configure via ``REDIS_URL`` env var (default ``redis://localhost:6379``).

    Each subscriber runs in a background ``asyncio.Task`` reading from a
    Redis Stream consumer group, so events are delivered exactly-once per
    consumer group even across multiple worker processes.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}
        self._redis = None
        self._consumer_group = f"todo-api-{os.getpid()}"

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
        return self._redis

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subscribers.setdefault(topic, []).append(handler)
        logger.info("RedisEventBus: subscribed %s to '%s'", handler.__name__, topic)

    async def publish(self, topic: str, event: Dict[str, Any]) -> Dict[str, Any]:
        event["topic"] = topic
        r = await self._get_redis()
        await r.xadd(topic, {"data": json.dumps(event)})
        logger.info(
            "RedisEventBus: published %s to '%s' (task_id=%s)",
            event.get("event_type", "?"),
            topic,
            event.get("task_id"),
        )
        return event

    async def start_consumers(self) -> None:
        """Start background tasks that read from Redis Streams."""
        for topic, handlers in self._subscribers.items():
            asyncio.create_task(self._consume(topic, handlers))

    async def _consume(self, topic: str, handlers: List[Callable]) -> None:
        r = await self._get_redis()
        group = self._consumer_group
        consumer = f"worker-{os.getpid()}"

        # Create consumer group (ignore if exists)
        try:
            await r.xgroup_create(topic, group, id="0", mkstream=True)
        except Exception:
            pass  # group already exists

        while True:
            try:
                results = await r.xreadgroup(
                    group, consumer, {topic: ">"}, count=10, block=5000
                )
                for _stream, messages in results:
                    for msg_id, fields in messages:
                        event = json.loads(fields["data"])
                        for handler in handlers:
                            await InMemoryEventBus._safe_dispatch(handler, event)
                        await r.xack(topic, group, msg_id)
            except Exception:
                logger.exception("RedisEventBus: consumer error on '%s'", topic)
                await asyncio.sleep(1)


def _create_event_bus():
    """Factory — select backend from EVENT_BUS_BACKEND env var."""
    backend = os.getenv("EVENT_BUS_BACKEND", "memory").lower()
    if backend == "redis":
        logger.info("EventBus backend: Redis Streams")
        return RedisEventBus()
    logger.info("EventBus backend: InMemory")
    return InMemoryEventBus()


# ── Global singleton ───────────────────────────────────────────────────
event_bus = _create_event_bus()
