"""
Database Connection Module
Using SQLModel with PostgreSQL
"""
from sqlmodel import create_engine, Session, SQLModel
from typing import Generator
import os

# Get database URL from config
from app.config import DATABASE_URL

# Create single engine instance with connection pooling and proper SSL settings
if "postgresql" in DATABASE_URL:
    # PostgreSQL-specific settings
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Recycle connections every 5 minutes
        pool_size=5,
        max_overflow=10,
        pool_timeout=20,
        connect_args={
            "connect_timeout": 15,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
        }
    )
else:
    # SQLite settings
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

# Import models to register them with SQLModel after engine is created
from app.models.user import User
from app.models.chat_models import Task, Conversation, Message


def _migrate_sqlite(conn):
    """Add missing columns for SQLite databases"""
    from sqlalchemy import text

    result = conn.execute(text("PRAGMA table_info(tasks)")).fetchall()
    existing_columns = [row[1] for row in result]

    migrations = {
        "due_date": "ALTER TABLE tasks ADD COLUMN due_date DATETIME DEFAULT NULL",
        "reminder_date": "ALTER TABLE tasks ADD COLUMN reminder_date DATETIME DEFAULT NULL",
        "priority": "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'",
        "tags": "ALTER TABLE tasks ADD COLUMN tags JSON DEFAULT NULL",
        "recurrence": "ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'none'",
        "reminder_enabled": "ALTER TABLE tasks ADD COLUMN reminder_enabled BOOLEAN DEFAULT 0",
    }

    for col_name, ddl in migrations.items():
        if col_name not in existing_columns:
            conn.execute(text(ddl))
            conn.commit()


def _migrate_postgresql(conn):
    """Add missing columns for PostgreSQL databases"""
    from sqlalchemy import text

    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'tasks'"
    )).fetchall()
    existing_columns = [row[0] for row in result]

    migrations = {
        "due_date": "ALTER TABLE tasks ADD COLUMN due_date TIMESTAMP DEFAULT NULL",
        "reminder_date": "ALTER TABLE tasks ADD COLUMN reminder_date TIMESTAMP DEFAULT NULL",
        "priority": "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'",
        "tags": "ALTER TABLE tasks ADD COLUMN tags JSON DEFAULT NULL",
        "recurrence": "ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'none'",
        "reminder_enabled": "ALTER TABLE tasks ADD COLUMN reminder_enabled BOOLEAN DEFAULT FALSE",
    }

    for col_name, ddl in migrations.items():
        if col_name not in existing_columns:
            conn.execute(text(ddl))
            conn.commit()


def create_db_and_tables():
    """
    Create database tables and migrate schema if needed.
    Handles both SQLite and PostgreSQL backends.
    """
    # Create all tables if they don't exist
    SQLModel.metadata.create_all(engine)

    # Add any missing columns for existing tables
    with engine.connect() as conn:
        if "postgresql" in DATABASE_URL:
            _migrate_postgresql(conn)
        else:
            _migrate_sqlite(conn)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    One session per request pattern
    """
    with Session(engine) as session:
        yield session
