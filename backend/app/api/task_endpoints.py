"""
REST /tasks/ endpoints consumed by the Next.js frontend.

Provides standard CRUD operations with JWT authentication.
Delegates all DB work to the shared TaskService layer and publishes
lifecycle events to the async event bus.
"""
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from app.db.database import get_session
from app.auth import get_current_user
from app.models.user import User
from app.models.chat_models import (
    Task as TaskModel,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    PriorityLevel,
    RecurrenceType,
)
from app.services.task_service import TaskService, _task_payload
from app.events.event_bus import event_bus
from app.events.event_types import (
    TOPIC_TASK_LIFECYCLE,
    make_task_event,
    EVENT_TASK_CREATED,
    EVENT_TASK_UPDATED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_DELETED,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── Request / Response helpers ────────────────────────────────────────

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: str = "medium"
    tags: Optional[List[str]] = None
    recurrence: str = "none"
    reminder_enabled: bool = False
    status: Optional[str] = None  # frontend sends "incomplete"


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    recurrence: Optional[str] = None
    reminder_enabled: Optional[bool] = None


class StatusUpdateRequest(BaseModel):
    status: str  # "complete" or "incomplete"


def _task_to_dict(task) -> Dict:
    """Serialise a TaskResponse or TaskModel to the shape the frontend expects."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
        "user_id": task.user_id,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "reminder_date": task.reminder_date.isoformat() if getattr(task, "reminder_date", None) else None,
        "priority": task.priority,
        "tags": task.tags or [],
        "recurrence": task.recurrence,
        "reminder_enabled": task.reminder_enabled,
    }


# ── GET /tasks/ ───────────────────────────────────────────────────────

@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)
    tasks = TaskService.get_tasks_for_user(session, user_id)

    # Filter by status
    if status == "complete":
        tasks = [t for t in tasks if t.completed]
    elif status == "incomplete":
        tasks = [t for t in tasks if not t.completed]

    # Sort
    reverse = order == "desc"
    if sort_by in ("created_at", "updated_at", "due_date", "priority", "title"):
        tasks.sort(key=lambda t: getattr(t, sort_by) or "", reverse=reverse)

    # Paginate
    total = len(tasks)
    tasks = tasks[offset: offset + limit]

    return {
        "tasks": [_task_to_dict(t) for t in tasks],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── POST /tasks/ ──────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)

    task_data = TaskCreate(
        title=request.title,
        description=request.description,
        due_date=request.due_date,
        reminder_date=request.reminder_date,
        priority=PriorityLevel(request.priority) if request.priority else PriorityLevel.medium,
        tags=request.tags,
        recurrence=RecurrenceType(request.recurrence) if request.recurrence else RecurrenceType.none,
        reminder_enabled=request.reminder_enabled,
    )

    task_response = TaskService.create_task(session, user_id, task_data)

    # Publish event
    task_model = TaskService.get_task_by_id(session, task_response.id, user_id)
    if task_model:
        event = make_task_event(
            EVENT_TASK_CREATED, user_id, task_response.id, _task_payload(task_model)
        )
        await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)

    return _task_to_dict(task_response)


# ── PUT /tasks/{task_id} ──────────────────────────────────────────────

@router.put("/{task_id}")
async def update_task(
    task_id: int,
    request: UpdateTaskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)

    update_fields = {}
    if request.title is not None:
        update_fields["title"] = request.title
    if request.description is not None:
        update_fields["description"] = request.description
    if request.completed is not None:
        update_fields["completed"] = request.completed
    if request.due_date is not None:
        update_fields["due_date"] = request.due_date
    if request.reminder_date is not None:
        update_fields["reminder_date"] = request.reminder_date
    if request.priority is not None:
        update_fields["priority"] = PriorityLevel(request.priority)
    if request.tags is not None:
        update_fields["tags"] = request.tags
    if request.recurrence is not None:
        update_fields["recurrence"] = RecurrenceType(request.recurrence)
    if request.reminder_enabled is not None:
        update_fields["reminder_enabled"] = request.reminder_enabled

    task_update = TaskUpdate(**update_fields)
    updated = TaskService.update_task(session, task_id, user_id, task_update)

    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    # Publish event
    task_after = TaskService.get_task_by_id(session, task_id, user_id)
    if task_after:
        event = make_task_event(
            EVENT_TASK_UPDATED, user_id, task_id, _task_payload(task_after)
        )
        await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)

    return _task_to_dict(updated)


# ── PATCH /tasks/{task_id}/status ─────────────────────────────────────

@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: int,
    request: StatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)

    task = TaskService.get_task_by_id(session, task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    new_completed = request.status == "complete"
    task_update = TaskUpdate(completed=new_completed)
    updated = TaskService.update_task(session, task_id, user_id, task_update)

    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    # Publish event
    task_after = TaskService.get_task_by_id(session, task_id, user_id)
    event_type = EVENT_TASK_COMPLETED if new_completed else EVENT_TASK_UPDATED
    if task_after:
        event = make_task_event(event_type, user_id, task_id, _task_payload(task_after))
        await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)

    return _task_to_dict(updated)


# ── DELETE /tasks/{task_id} ───────────────────────────────────────────

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)

    task = TaskService.get_task_by_id(session, task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    payload_before = _task_payload(task)
    success = TaskService.delete_task(session, task_id, user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete task")

    # Publish event
    event = make_task_event(EVENT_TASK_DELETED, user_id, task_id, payload_before)
    await event_bus.publish(TOPIC_TASK_LIFECYCLE, event)

    return {"status": "success", "task_id": task_id}


# ── GET /tasks/stats ──────────────────────────────────────────────────

@router.get("/stats")
async def get_task_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = str(current_user.id)
    return TaskService.get_task_stats(session, user_id)
