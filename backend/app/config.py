import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TODO_DB_PATH = PROJECT_ROOT / "todo_app.db"

# Use PostgreSQL from environment variable, fallback to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{TODO_DB_PATH}"

# ── Event Bus ───────────────────────────────────────────────────────────
# "memory" (default, single-process) | "redis" (multi-process via Streams)
EVENT_BUS_BACKEND = os.getenv("EVENT_BUS_BACKEND", "memory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
