"""
Main Todo Application API Server — Phase 5 (Event-Driven)

Stateless chatbot that:
  1. Parses user intent via lightweight NLP.
  2. Executes task operations through the embedded MCP service layer.
  3. Publishes lifecycle events to the async event bus.
  4. Stores conversation history in the database (zero in-memory state).
  5. Returns an immediate confirmation to the caller.

All background work (reminders, recurrence, notifications) is handled by
subscriber services consuming events from the bus — the chatbot never
blocks on them.
"""
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncio
import json as json_module

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse
import jwt

from app.db.database import get_session
from app.models.chat_models import (
    Conversation,
    Message,
    TaskCreate as ModelTaskCreate,
    TaskUpdate as ModelTaskUpdate,
    PriorityLevel,
    RecurrenceType,
)
from app.models.user import User, TokenData
from app.services.task_service import MCPTaskService, TaskService, _task_payload
from app.events.event_bus import event_bus
from app.events.event_types import TOPIC_TASK_LIFECYCLE, make_task_event, EVENT_TASK_UPDATED
from app.events.subscribers import sse_connect, sse_disconnect

import os

logger = logging.getLogger(__name__)

# ── Router ──────────────────────────────────────────────────────────────
router = APIRouter()

# ── JWT / Auth ──────────────────────────────────────────────────────────
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-super-secret-and-long-random-string-here-change-this-in-production",
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.email == token_data.email)).first()
    if user is None:
        raise credentials_exception
    return user


# ── Request / Response Models ───────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    task_operations: Optional[Dict[str, Any]] = None
    events_published: Optional[List[Dict[str, Any]]] = None


# ── NLP Helpers (stateless, pure functions) ──────────────────────────────

_PRIORITY_MAP = {
    "high": "high", "urgent": "high", "important": "high",
    "medium": "medium", "normal": "medium", "default": "medium",
    "low": "low", "minor": "low",
}

_RECURRENCE_MAP = {
    "daily": "daily", "every day": "daily",
    "weekly": "weekly", "every week": "weekly",
    "monthly": "monthly", "every month": "monthly",
}


def _extract_task_metadata(message: str) -> Dict[str, Any]:
    """Extract Phase 5 metadata from a natural-language message.

    Returns a dict with keys: priority, tags, due_date, recurrence,
    reminder_enabled.  All values default to safe fallbacks so that
    callers never need to guard against ``None``.
    """
    lower = message.lower()

    # Priority
    priority = "medium"
    for keyword, level in _PRIORITY_MAP.items():
        if keyword in lower:
            priority = level
            break

    # Tags — #tag patterns
    tags = re.findall(r"#(\w+)", message)

    # Due date — "by YYYY-MM-DD" or "due YYYY-MM-DD"
    due_date = None
    date_match = re.search(r"(?:by|due|before)\s+(\d{4}-\d{2}-\d{2})", lower)
    if date_match:
        try:
            due_date = datetime.fromisoformat(date_match.group(1))
        except ValueError:
            pass

    # Recurrence
    recurrence = "none"
    for keyword, pattern in _RECURRENCE_MAP.items():
        if keyword in lower:
            recurrence = pattern
            break

    # Reminder
    reminder_enabled = any(kw in lower for kw in ["remind", "reminder", "alert me"])

    return {
        "priority": priority,
        "tags": tags or None,
        "due_date": due_date,
        "recurrence": recurrence,
        "reminder_enabled": reminder_enabled,
    }


def _extract_title(message: str) -> Optional[str]:
    """Pull a task title from natural language.

    Tries quoted strings first, then falls back to keyword extraction.
    """
    # Quoted title
    match = re.search(r'"([^"]+)"', message)
    if match:
        return match.group(1).strip()

    # After "task/todo" keyword
    match = re.search(
        r"(?:add|create|make)\s+(?:a\s+|an\s+|the\s+)?(?:task|todo)\s+"
        r"(?:to\s+|for\s+|about\s+)?(.+?)(?:\.|!|\?|$)",
        message,
        re.IGNORECASE,
    )
    if match:
        title = match.group(1).strip()
        # Strip trailing metadata tokens so they don't leak into the title
        title = re.sub(
            r"\s*(?:#\w+|(?:high|low|medium|urgent)\s+priority|"
            r"(?:by|due)\s+\d{4}-\d{2}-\d{2}|daily|weekly|monthly|"
            r"remind(?:er)?(?:\s+me)?).*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        return title or None

    return None


def _extract_task_id(message: str) -> Optional[int]:
    """Find the first integer (optionally preceded by '#') in *message*."""
    match = re.search(r"#?(\d+)", message)
    return int(match.group(1)) if match else None


def _extract_update_fields(message: str) -> Dict[str, Any]:
    """Parse partial-update fields from an update command.

    Supports:
        title   — update task 1 title to "new name"
        priority — set priority to high
        tags    — add tag #work
    """
    fields: Dict[str, Any] = {}

    # Title
    title_match = re.search(r'(?:title\s+)?(?:to|as|is)\s+"([^"]*)"', message)
    if title_match:
        fields["title"] = title_match.group(1).strip()

    # Priority
    pri_match = re.search(
        r"(?:priority|pri)\s+(?:to\s+)?(high|medium|low|urgent)", message, re.IGNORECASE
    )
    if pri_match:
        fields["priority"] = _PRIORITY_MAP.get(pri_match.group(1).lower(), "medium")

    # Tags (additive)
    tags = re.findall(r"#(\w+)", message)
    if tags:
        fields["tags"] = tags

    return fields


# ── Helper: publish event returned by MCPTaskService ──────────────────

async def _publish_if_present(result: Dict[str, Any], events_published: list) -> None:
    """If *result* contains an ``event`` key, publish it and track it."""
    event = result.get("event")
    if event:
        await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)
        events_published.append(event)


# ── Intent Detection ────────────────────────────────────────────────────

def _is_add(msg: str) -> bool:
    return (
        any(w in msg for w in ("add", "create", "make"))
        and any(w in msg for w in ("task", "todo"))
    )


def _is_list(msg: str) -> bool:
    return (
        any(w in msg for w in ("list", "show", "display", "get"))
        and any(w in msg for w in ("task", "todo", "my"))
    )


def _is_complete(msg: str) -> bool:
    return (
        any(w in msg for w in ("complete", "finish", "done", "mark"))
        and any(w in msg for w in ("task", "todo"))
    )


def _is_delete(msg: str) -> bool:
    return (
        any(w in msg for w in ("delete", "remove", "cancel"))
        and any(w in msg for w in ("task", "todo"))
    )


def _is_update(msg: str) -> bool:
    return (
        any(w in msg for w in ("update", "change", "modify", "edit", "set"))
        and any(w in msg for w in ("task", "todo"))
    )


# ── Chat Endpoint ───────────────────────────────────────────────────────

@router.post("/{user_id}/chat", response_model=ChatResponse)
async def chat_endpoint(
    user_id: str,
    request: ChatRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """Stateless chat endpoint.

    Flow for every request:
      1. Authenticate → derive effective_user_id
      2. Parse intent + extract metadata
      3. Execute via MCPTaskService (writes to DB)
      4. Publish lifecycle event (fire-and-forget)
      5. Persist conversation turn (user msg + assistant msg)
      6. Return immediate ChatResponse
    """
    try:
        effective_user_id = str(current_user.id)
        logger.info("Chat request from user %s", effective_user_id)

        msg_lower = request.message.lower()

        response_text = ""
        tool_calls: List[Dict[str, Any]] = []
        task_operations: Dict[str, Any] = {}
        events_published: List[Dict[str, Any]] = []

        # ── ADD TASK ────────────────────────────────────────────────
        if _is_add(msg_lower):
            title = _extract_title(request.message)
            if title:
                meta = _extract_task_metadata(request.message)

                result = MCPTaskService.add_task(
                    session=session,
                    user_id=effective_user_id,
                    title=title,
                    description="Added via chatbot",
                    priority=meta["priority"],
                    tags=meta["tags"],
                    due_date=meta["due_date"],
                    recurrence=meta["recurrence"],
                    reminder_enabled=meta["reminder_enabled"],
                )

                tool_calls.append({"name": "add_task", "arguments": {"title": title, **meta}})

                if result.get("status") == "success":
                    task_id = result["task_id"]
                    await _publish_if_present(result, events_published)

                    task_operations["add_task"] = {
                        "status": "success",
                        "task_id": task_id,
                        "title": title,
                    }
                    response_text = f"I've added the task '{title}' to your list (ID: {task_id})."
                else:
                    task_operations["add_task"] = {"status": "error", "message": result.get("message", "Unknown error")}
                    response_text = "Sorry, I couldn't add that task. Please try again."
            else:
                task_operations["add_task"] = {"status": "error", "message": "No task title found"}
                response_text = (
                    "I need a title for the new task. Please specify what task you'd "
                    "like to add (e.g., 'add task Buy groceries')."
                )

        # ── LIST TASKS ──────────────────────────────────────────────
        elif _is_list(msg_lower):
            result = MCPTaskService.list_tasks(session=session, user_id=effective_user_id)
            tasks = result.get("tasks", [])
            tool_calls.append({"name": "list_tasks", "arguments": {"count": len(tasks)}})

            if tasks:
                lines = []
                for t in tasks:
                    stat = "completed" if t["completed"] else "pending"
                    pri = t.get("priority", "medium")
                    tags_str = " ".join(f"#{tg}" for tg in (t.get("tags") or []))
                    line = f"  - #{t['id']}: {t['title']} ({stat}, {pri})"
                    if tags_str:
                        line += f" {tags_str}"
                    if t.get("due_date"):
                        line += f" due {t['due_date'][:10]}"
                    if t.get("recurrence", "none") != "none":
                        line += f" [{t['recurrence']}]"
                    lines.append(line)

                response_text = f"Here are your {len(tasks)} tasks:\n" + "\n".join(lines)
                task_operations["list_tasks"] = {"status": "success", "count": len(tasks), "tasks": tasks}
            else:
                response_text = "You have no tasks yet. Try 'add task Buy groceries' to get started!"
                task_operations["list_tasks"] = {"status": "success", "count": 0, "tasks": []}

        # ── COMPLETE TASK ───────────────────────────────────────────
        elif _is_complete(msg_lower):
            task_id = _extract_task_id(request.message)
            if task_id:
                result = MCPTaskService.complete_task(
                    session=session, task_id=task_id, user_id=effective_user_id
                )
                tool_calls.append({"name": "complete_task", "arguments": {"task_id": task_id}})

                if result.get("status") == "success":
                    await _publish_if_present(result, events_published)

                    task_after = TaskService.get_task_by_id(session, task_id, effective_user_id)
                    task_title = task_after.title if task_after else f"#{task_id}"
                    task_operations["complete_task"] = {
                        "status": "success",
                        "task_id": task_id,
                        "title": task_title,
                        "completed": True,
                    }
                    response_text = f"I've marked task #{task_id} '{task_title}' as completed."
                else:
                    task_operations["complete_task"] = {
                        "status": "error",
                        "task_id": task_id,
                        "message": "Task not found",
                    }
                    response_text = f"Task #{task_id} not found."
            else:
                task_operations["complete_task"] = {"status": "error", "message": "No task ID found"}
                response_text = "Please specify which task to complete (e.g., 'complete task 1')."

        # ── DELETE TASK ─────────────────────────────────────────────
        elif _is_delete(msg_lower):
            task_id = _extract_task_id(request.message)
            if task_id:
                result = MCPTaskService.delete_task(
                    session=session, task_id=task_id, user_id=effective_user_id
                )
                tool_calls.append({"name": "delete_task", "arguments": {"task_id": task_id}})

                if result.get("status") == "success":
                    await _publish_if_present(result, events_published)

                    task_operations["delete_task"] = {"status": "success", "task_id": task_id}
                    response_text = f"I've deleted task #{task_id}."
                else:
                    task_operations["delete_task"] = {
                        "status": "error",
                        "task_id": task_id,
                        "message": "Task not found",
                    }
                    response_text = f"Task #{task_id} not found."
            else:
                task_operations["delete_task"] = {"status": "error", "message": "No task ID found"}
                response_text = "Please specify which task to delete (e.g., 'delete task 1')."

        # ── UPDATE TASK ─────────────────────────────────────────────
        elif _is_update(msg_lower):
            task_id = _extract_task_id(request.message)
            if task_id:
                fields = _extract_update_fields(request.message)
                # Also merge any metadata extracted from the message
                meta = _extract_task_metadata(request.message)
                if "priority" not in fields and meta["priority"] != "medium":
                    fields["priority"] = meta["priority"]
                if "tags" not in fields and meta["tags"]:
                    fields["tags"] = meta["tags"]

                if fields:
                    result = MCPTaskService.update_task(
                        session=session,
                        task_id=task_id,
                        user_id=effective_user_id,
                        **fields,
                    )
                    tool_calls.append({
                        "name": "update_task",
                        "arguments": {"task_id": task_id, **fields},
                    })

                    if result.get("status") == "success":
                        task_after = TaskService.get_task_by_id(session, task_id, effective_user_id)
                        event = make_task_event(
                            EVENT_TASK_UPDATED,
                            effective_user_id,
                            task_id,
                            _task_payload(task_after) if task_after else {},
                        )
                        await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)
                        events_published.append(event)

                        changed = ", ".join(f"{k}={v}" for k, v in fields.items())
                        task_operations["update_task"] = {
                            "status": "success",
                            "task_id": task_id,
                            "updated_fields": fields,
                        }
                        response_text = f"I've updated task #{task_id} ({changed})."
                    else:
                        task_operations["update_task"] = {
                            "status": "error",
                            "task_id": task_id,
                            "message": "Task not found",
                        }
                        response_text = f"Task #{task_id} not found."
                else:
                    task_operations["update_task"] = {
                        "status": "error",
                        "message": "No update details found",
                    }
                    response_text = (
                        f"Please specify what to change on task #{task_id} "
                        f'(e.g., \'update task {task_id} title to "new title"\').'
                    )
            else:
                task_operations["update_task"] = {"status": "error", "message": "No task ID found"}
                response_text = "Please specify which task to update (e.g., 'update task 1')."

        # ── FALLBACK ────────────────────────────────────────────────
        else:
            response_text = (
                f"I received your message: '{request.message}'. "
                "How can I help you with your tasks today? You can say things like "
                "'add task Buy groceries', 'list my tasks', 'complete task 1', "
                "'update task 1 priority to high', or 'delete task 2'."
            )
            task_operations["general_query"] = {"status": "success", "message": "General query processed"}

        # ── Persist conversation (stateless — DB is sole state store) ───
        conversation_id = (
            getattr(request, "conversation_id", None)
            or f"conv_{effective_user_id}_{int(datetime.now().timestamp())}"
        )

        existing_conv = session.exec(
            select(Conversation).where(Conversation.id == conversation_id)
        ).first()
        if not existing_conv:
            session.add(
                Conversation(
                    id=conversation_id,
                    user_id=effective_user_id,
                    title=(
                        request.message[:50] + "..."
                        if len(request.message) > 50
                        else request.message
                    ),
                )
            )

        session.add(
            Message(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                role="user",
                content=request.message,
            )
        )
        session.add(
            Message(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                role="assistant",
                content=response_text,
            )
        )
        session.commit()

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            tool_calls=tool_calls,
            task_operations=task_operations,
            events_published=events_published or None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat processing error")
        raise HTTPException(status_code=500, detail=f"Chat processing error: {e}")


# ── SSE Event Stream ───────────────────────────────────────────────────

@router.get("/{user_id}/events")
async def event_stream(
    user_id: str,
    request: Request,
    token: str = None,
    session: Session = Depends(get_session),
):
    """Server-Sent Events endpoint for real-time task event updates.

    Accepts auth via ``?token=`` query param (EventSource can't set headers).
    The client opens a persistent connection and receives JSON events
    whenever a task lifecycle event is published for the authenticated user.
    """
    # Authenticate via query-param token (EventSource limitation)
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    effective_user_id = str(user.id)
    queue = sse_connect(effective_user_id)

    async def _generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.get("event_type", "task.event"),
                        "data": json_module.dumps(event),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield {"comment": "keepalive"}
        finally:
            sse_disconnect(effective_user_id, queue)

    return EventSourceResponse(_generate())


# ── Health ──────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "todo-api"}
