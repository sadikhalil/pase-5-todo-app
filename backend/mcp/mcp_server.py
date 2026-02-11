"""
MCP (Micro Control Plane) Server for Todo Application
Handles task operations through API endpoints using shared service layer

Note: This standalone server is deprecated.  The canonical MCP endpoints
live in app.api.mcp_endpoints and are served by the main FastAPI app.
This file is kept for reference / fallback only.
"""
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, create_engine
from datetime import datetime
import os
import uvicorn

# Import the shared service
from app.services.task_service import MCPTaskService
from app.db.database import get_session, engine


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


def create_db_and_tables():
    from sqlmodel import SQLModel
    from app.models.chat_models import Task
    SQLModel.metadata.create_all(engine)


# Create FastAPI app
app = FastAPI(title="Todo MCP Server", version="2.0.0")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# ---------------------------------------------------------------------------
# Tool endpoints - using shared service layer
# ---------------------------------------------------------------------------

@app.post("/mcp/tools/add_task")
def add_task(request: AddTaskRequest):
    session = next(get_session())
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
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        session.close()


@app.post("/mcp/tools/update_task")
def update_task(request: UpdateTaskRequest):
    session = next(get_session())
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
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        session.close()


@app.post("/mcp/tools/list_tasks")
def list_tasks(request: ListTasksRequest):
    session = next(get_session())
    try:
        result = MCPTaskService.list_tasks(
            session=session,
            user_id=request.user_id,
        )
        return result
    finally:
        session.close()


@app.post("/mcp/tools/complete_task")
def complete_task(request: CompleteTaskRequest):
    session = next(get_session())
    try:
        result = MCPTaskService.complete_task(
            session=session,
            task_id=request.task_id,
            user_id=request.user_id,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    finally:
        session.close()


@app.post("/mcp/tools/delete_task")
def delete_task(request: DeleteTaskRequest):
    session = next(get_session())
    try:
        result = MCPTaskService.delete_task(
            session=session,
            task_id=request.task_id,
            user_id=request.user_id,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Info endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Todo MCP Server v2.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "mcp-server"}


if __name__ == "__main__":
    uvicorn.run(
        "mcp.mcp_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
