"""
Shared task service layer for both REST API and MCP tools.

Ensures consistent database operations across all interfaces.
MCPTaskService methods return an ``event`` key in their result dict
so that async callers can publish it to the event bus in one line.
"""

from typing import List, Optional, Dict
from sqlmodel import Session, select
from datetime import datetime

from app.models.chat_models import (
    Task as TaskModel,
    TaskCreate, TaskUpdate, TaskResponse,
    PriorityLevel, RecurrenceType,
)
from app.events.event_types import (
    EVENT_TASK_CREATED,
    EVENT_TASK_UPDATED,
    EVENT_TASK_COMPLETED,
    EVENT_TASK_DELETED,
    make_task_event,
)


class TaskService:
    """Shared service layer for task operations"""

    @staticmethod
    def _to_response(task: TaskModel) -> TaskResponse:
        """Convert a Task model instance to a TaskResponse"""
        return TaskResponse(
            id=task.id,
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            completed=task.completed,
            created_at=task.created_at,
            updated_at=task.updated_at,
            due_date=task.due_date,
            reminder_date=task.reminder_date,
            priority=task.priority,
            tags=task.tags,
            recurrence=task.recurrence,
            reminder_enabled=task.reminder_enabled,
        )

    @staticmethod
    def create_task(session: Session, user_id: str, task_data: TaskCreate) -> TaskResponse:
        """Create a new task in the database"""
        new_task = TaskModel(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            completed=getattr(task_data, 'completed', False),
            due_date=getattr(task_data, 'due_date', None),
            reminder_date=getattr(task_data, 'reminder_date', None),
            priority=getattr(task_data, 'priority', 'medium'),
            tags=getattr(task_data, 'tags', None),
            recurrence=getattr(task_data, 'recurrence', 'none'),
            reminder_enabled=getattr(task_data, 'reminder_enabled', False),
        )

        session.add(new_task)
        session.commit()
        session.refresh(new_task)

        return TaskService._to_response(new_task)

    @staticmethod
    def get_tasks_for_user(session: Session, user_id: str) -> List[TaskResponse]:
        """Get all tasks for a specific user"""
        statement = select(TaskModel).where(TaskModel.user_id == user_id)
        tasks = session.exec(statement).all()
        return [TaskService._to_response(task) for task in tasks]

    @staticmethod
    def get_task_by_id(session: Session, task_id: int, user_id: str) -> Optional[TaskModel]:
        """Get a specific task by ID for a specific user"""
        statement = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.user_id == user_id
        )
        return session.exec(statement).first()

    @staticmethod
    def update_task(session: Session, task_id: int, user_id: str, task_data: TaskUpdate) -> Optional[TaskResponse]:
        """Update an existing task"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return None

        # Update task fields
        update_data = task_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)

        return TaskService._to_response(task)

    @staticmethod
    def delete_task(session: Session, task_id: int, user_id: str) -> bool:
        """Delete a task by ID for a specific user"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return False

        session.delete(task)
        session.commit()
        return True

    @staticmethod
    def toggle_task_completion(session: Session, task_id: int, user_id: str) -> Optional[TaskResponse]:
        """Toggle the completion status of a task"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return None

        task.completed = not task.completed
        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)

        return TaskService._to_response(task)

    @staticmethod
    def get_task_stats(session: Session, user_id: str) -> Dict[str, int]:
        """Get task statistics for a user"""
        statement = select(TaskModel).where(TaskModel.user_id == user_id)
        all_tasks = session.exec(statement).all()

        total = len(all_tasks)
        completed = len([t for t in all_tasks if t.completed])
        pending = total - completed

        return {
            "total": total,
            "completed": completed,
            "pending": pending
        }


# ── Event payload builder ──────────────────────────────────────────────

def _task_payload(task) -> Dict:
    """Build a serialisable event payload from a Task model or TaskResponse."""
    return {
        "title": getattr(task, "title", None),
        "description": getattr(task, "description", None),
        "completed": getattr(task, "completed", None),
        "priority": getattr(task, "priority", None),
        "tags": getattr(task, "tags", None) or [],
        "due_date": (
            task.due_date.isoformat() if getattr(task, "due_date", None) else None
        ),
        "recurrence": getattr(task, "recurrence", "none"),
        "reminder_enabled": getattr(task, "reminder_enabled", False),
    }


# MCP-specific convenience functions that map to the shared service
class MCPTaskService:
    """Convenience wrapper for MCP tools to use the shared service.

    Every mutating method returns an ``event`` key containing a pre-built
    event dict ready for ``await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])``.
    Read-only methods (``list_tasks``) return no event.
    """

    @staticmethod
    def add_task(
        session: Session,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        recurrence: str = "none",
        reminder_enabled: bool = False,
    ) -> Dict:
        """Add a task via MCP interface"""
        task_data = TaskCreate(
            title=title,
            description=description or "Added via chatbot",
            completed=False,
            priority=PriorityLevel(priority),
            tags=tags,
            due_date=due_date,
            recurrence=RecurrenceType(recurrence),
            reminder_enabled=reminder_enabled,
        )

        task_response = TaskService.create_task(session, user_id, task_data)

        # Fetch fresh model for complete event payload
        task_model = TaskService.get_task_by_id(session, task_response.id, user_id)

        return {
            "status": "success",
            "message": f"Task '{title}' added successfully",
            "task_id": task_response.id,
            "event": make_task_event(
                EVENT_TASK_CREATED,
                user_id,
                task_response.id,
                _task_payload(task_model) if task_model else {"title": title},
            ),
        }

    @staticmethod
    def update_task(
        session: Session,
        task_id: int,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        recurrence: Optional[str] = None,
        reminder_enabled: Optional[bool] = None,
    ) -> Dict:
        """Update a task via MCP interface"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return {"status": "error", "error": "Task not found"}

        # Build update payload with only provided fields
        update_fields = {}
        if title is not None:
            update_fields["title"] = title
        if description is not None:
            update_fields["description"] = description
        if completed is not None:
            update_fields["completed"] = completed
        if priority is not None:
            update_fields["priority"] = PriorityLevel(priority)
        if tags is not None:
            update_fields["tags"] = tags
        if due_date is not None:
            update_fields["due_date"] = due_date
        if recurrence is not None:
            update_fields["recurrence"] = RecurrenceType(recurrence)
        if reminder_enabled is not None:
            update_fields["reminder_enabled"] = reminder_enabled

        task_data = TaskUpdate(**update_fields)
        updated = TaskService.update_task(session, task_id, user_id, task_data)

        if not updated:
            return {"status": "error", "error": "Failed to update task"}

        # Re-read for complete payload
        task_after = TaskService.get_task_by_id(session, task_id, user_id)

        return {
            "status": "success",
            "message": f"Task '{updated.title}' updated successfully",
            "task_id": updated.id,
            "event": make_task_event(
                EVENT_TASK_UPDATED,
                user_id,
                task_id,
                _task_payload(task_after) if task_after else {},
            ),
        }

    @staticmethod
    def list_tasks(session: Session, user_id: str) -> Dict:
        """List tasks via MCP interface (read-only, no event)."""
        tasks = TaskService.get_tasks_for_user(session, user_id)

        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "user_id": task.user_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "reminder_date": task.reminder_date.isoformat() if task.reminder_date else None,
                "priority": task.priority,
                "tags": task.tags or [],
                "recurrence": task.recurrence,
                "reminder_enabled": task.reminder_enabled,
            })

        return {
            "status": "success",
            "tasks": task_list
        }

    @staticmethod
    def complete_task(session: Session, task_id: int, user_id: str) -> Dict:
        """Complete a task via MCP interface"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return {"status": "error", "error": "Task not found"}

        updated_task = TaskService.toggle_task_completion(session, task_id, user_id)

        # Re-read for updated state
        task_after = TaskService.get_task_by_id(session, task_id, user_id)

        return {
            "status": "success",
            "message": f"Task '{task.title}' marked as completed",
            "task_id": task_id,
            "event": make_task_event(
                EVENT_TASK_COMPLETED,
                user_id,
                task_id,
                _task_payload(task_after) if task_after else {},
            ),
        }

    @staticmethod
    def delete_task(session: Session, task_id: int, user_id: str) -> Dict:
        """Delete a task via MCP interface"""
        task = TaskService.get_task_by_id(session, task_id, user_id)
        if not task:
            return {"status": "error", "error": "Task not found"}

        # Capture payload BEFORE deletion
        payload_before = _task_payload(task)

        success = TaskService.delete_task(session, task_id, user_id)

        if success:
            return {
                "status": "success",
                "message": f"Task '{task.title}' deleted successfully",
                "task_id": task_id,
                "event": make_task_event(
                    EVENT_TASK_DELETED,
                    user_id,
                    task_id,
                    payload_before,
                ),
            }
        else:
            return {"status": "error", "error": "Failed to delete task"}