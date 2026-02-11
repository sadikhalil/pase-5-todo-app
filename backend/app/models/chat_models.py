"""
SQLModel Database Models
Following the specified database schema
"""
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class PriorityLevel(str, Enum):
    """Task priority levels"""
    low = "low"
    medium = "medium"
    high = "high"


class RecurrenceType(str, Enum):
    """Task recurrence patterns"""
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)  # Foreign key to users table
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = Field(default=None)
    reminder_date: Optional[datetime] = Field(default=None)
    priority: str = Field(default=PriorityLevel.medium.value)
    tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    recurrence: str = Field(default=RecurrenceType.none.value)
    reminder_enabled: bool = Field(default=False)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to messages
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)
    user_id: str = Field(index=True)
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to conversation
    conversation: Optional[Conversation] = Relationship(back_populates="messages")


# Define a base model for requests/responses if needed
class TaskCreate(SQLModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: PriorityLevel = PriorityLevel.medium
    tags: Optional[List[str]] = None
    recurrence: RecurrenceType = RecurrenceType.none
    reminder_enabled: bool = False


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: Optional[PriorityLevel] = None
    tags: Optional[List[str]] = None
    recurrence: Optional[RecurrenceType] = None
    reminder_enabled: Optional[bool] = None


class TaskResponse(SQLModel):
    """Read-only response schema — not a DB table."""
    id: Optional[int] = None
    user_id: str
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None
    priority: str = PriorityLevel.medium.value
    tags: Optional[List[str]] = None
    recurrence: str = RecurrenceType.none.value
    reminder_enabled: bool = False


class ChatRequest(SQLModel):
    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(SQLModel):
    response: str
    conversation_id: str
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Track tool calls made during the interaction
    task_operations: Optional[Dict[str, Any]] = None  # Track any task operations performed


class TaskOperationResult(SQLModel):
    """Response structure for task operations performed via chat"""
    status: str  # "success" or "error"
    message: str
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    tasks_list: Optional[List[Dict[str, Any]]] = None  # For list operations