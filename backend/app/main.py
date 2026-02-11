"""
Main entry point for the Todo Application API Server — Phase 5
"""
from dotenv import load_dotenv
load_dotenv()

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import router as api_router
from app.api.mcp_endpoints import mcp_router
from app.api.task_endpoints import router as task_router
from app.db.database import create_db_and_tables

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Todo Application API",
    version="2.0.0",
    description="Event-driven Todo application with embedded MCP, async pub/sub, and stateless chatbot",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https?://localhost(:[0-9]+)?|https?://127\.0\.0\.1(:[0-9]+)?",
)

# ── Auth ────────────────────────────────────────────────────────────────
from app.auth import router as auth_router

# ── Routers ─────────────────────────────────────────────────────────────
app.include_router(task_router, tags=["tasks"])
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(mcp_router, tags=["mcp"])

# ── Startup ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialise database tables and register event subscribers."""
    create_db_and_tables()

    # Register event-bus subscribers (fire-and-forget async handlers)
    from app.events.event_bus import event_bus
    from app.events.event_types import TOPIC_TASK_LIFECYCLE
    from app.events.subscribers import (
        reminder_subscriber,
        recurrence_subscriber,
        notification_subscriber,
    )

    event_bus.subscribe(TOPIC_TASK_LIFECYCLE, reminder_subscriber)
    event_bus.subscribe(TOPIC_TASK_LIFECYCLE, recurrence_subscriber)
    event_bus.subscribe(TOPIC_TASK_LIFECYCLE, notification_subscriber)

    # If using Redis backend, start stream consumers
    if hasattr(event_bus, "start_consumers"):
        await event_bus.start_consumers()

    logger.info("Startup complete — event subscribers registered")


# ── Root & Health ───────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Todo Application API v2.0.0 (Event-Driven)"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "todo-api", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
