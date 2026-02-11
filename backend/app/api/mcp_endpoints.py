"""
MCP (Micro Control Plane) endpoints integrated into the main server
Handles task operations through API endpoints using shared service layer
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session
from datetime import datetime

from app.models.chat_models import PriorityLevel, RecurrenceType
from app.services.task_service import MCPTaskService
from app.db.database import get_session
from app.api.main import get_current_user_from_token  # Reuse authentication
from app.events.event_bus import event_bus
from app.events.event_types import TOPIC_TASK_LIFECYCLE


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AddTaskRequest(BaseModel):
    user_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    recurrence: str = "none"
    reminder_enabled: bool = False


class UpdateTaskRequest(BaseModel):
    user_id: str
    task_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    recurrence: Optional[str] = None
    reminder_enabled: Optional[bool] = None


class CompleteTaskRequest(BaseModel):
    user_id: str
    task_id: int


class DeleteTaskRequest(BaseModel):
    user_id: str
    task_id: int


class ListTasksRequest(BaseModel):
    user_id: str


class ListTasksResponse(BaseModel):
    status: str
    tasks: List[Dict]


class TaskOperationResponse(BaseModel):
    status: str
    message: Optional[str] = None
    task_id: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------------

@mcp_router.post("/tools/add_task", response_model=TaskOperationResponse)
async def add_task(
    request: AddTaskRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """Add a task via MCP interface with full Phase 5 field support."""
    if str(current_user.id) != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot modify other users' tasks")

    try:
        result = MCPTaskService.add_task(
            session=session,
            user_id=request.user_id,
            title=request.title,
            description=request.description,
            priority=request.priority,
            tags=request.tags,
            due_date=request.due_date,
            recurrence=request.recurrence,
            reminder_enabled=request.reminder_enabled,
        )
        if result.get("event"):
            await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/update_task", response_model=TaskOperationResponse)
async def update_task(
    request: UpdateTaskRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """Update a task via MCP interface — supports partial updates on all fields."""
    if str(current_user.id) != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot modify other users' tasks")

    try:
        result = MCPTaskService.update_task(
            session=session,
            task_id=request.task_id,
            user_id=request.user_id,
            title=request.title,
            description=request.description,
            completed=request.completed,
            priority=request.priority,
            tags=request.tags,
            due_date=request.due_date,
            recurrence=request.recurrence,
            reminder_enabled=request.reminder_enabled,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result["error"])
        if result.get("event"):
            await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/list_tasks", response_model=ListTasksResponse)
async def list_tasks(
    request: ListTasksRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """List tasks via MCP interface — response includes all Phase 5 fields."""
    if str(current_user.id) != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access other users' tasks")

    try:
        result = MCPTaskService.list_tasks(
            session=session,
            user_id=request.user_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/complete_task", response_model=TaskOperationResponse)
async def complete_task(
    request: CompleteTaskRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """Complete a task via MCP interface."""
    if str(current_user.id) != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot modify other users' tasks")

    try:
        result = MCPTaskService.complete_task(
            session=session,
            task_id=request.task_id,
            user_id=request.user_id,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result["error"])
        if result.get("event"):
            await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/tools/delete_task", response_model=TaskOperationResponse)
async def delete_task(
    request: DeleteTaskRequest,
    current_user=Depends(get_current_user_from_token),
    session: Session = Depends(get_session),
):
    """Delete a task via MCP interface."""
    if str(current_user.id) != request.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot modify other users' tasks")

    try:
        result = MCPTaskService.delete_task(
            session=session,
            task_id=request.task_id,
            user_id=request.user_id,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result["error"])
        if result.get("event"):
            await event_bus.publish(TOPIC_TASK_LIFECYCLE, result["event"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Info endpoints
# ---------------------------------------------------------------------------

@mcp_router.get("/", response_model=Dict)
def mcp_root():
    """Root endpoint for MCP functionality"""
    return {"message": "Todo MCP Endpoints - Integrated into Main Server", "status": "active"}


@mcp_router.get("/health", response_model=Dict)
def mcp_health_check():
    """Health check for MCP endpoints"""
    return {"status": "healthy", "service": "mcp-integrated"}
