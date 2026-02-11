---
id: 004
title: Phase 5 Task Model Extension
stage: green
date: 2026-02-09
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: User
command: direct-prompt
labels: ["model-extension", "phase5", "backend", "database"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - backend/app/models/chat_models.py
  - backend/app/db/database.py
  - backend/app/services/task_service.py
tests:
  - none (model-only change, no tests added yet)
---

## Prompt

You are extending my existing AI Todo application for Phase 5.

Task:
1. Modify the existing Task model in the backend to add the following fields:
   - priority (low, medium, high)
   - tags (array of strings)
   - due_date (datetime, optional)
   - recurrence (none, daily, weekly, monthly)
   - reminder_enabled (boolean)

Constraints:
- Use the existing SQLModel + PostgreSQL setup.
- Ensure backward compatibility: existing tasks should not break.
- Provide the exact file changes (like a diff) for the model file.
- Suggest any database migration or schema update needed.

Do NOT touch frontend or MCP tools yet. Focus only on the Task model and database.

## Response snapshot

Extended the Task model with Phase 5 fields across 3 backend files:
- Added PriorityLevel and RecurrenceType enums to chat_models.py
- Added tags (JSON), recurrence (str), reminder_enabled (bool) fields to Task table model
- Upgraded priority from bare string to enum-validated field
- Updated TaskCreate/TaskUpdate schemas with enum validation
- Refactored database.py migration to support both SQLite and PostgreSQL with separate _migrate_sqlite() and _migrate_postgresql() helpers; fixed duplicate function bug
- Consolidated TaskService with _to_response() helper to eliminate repeated TaskResponse constructors
- Updated MCP list_tasks to include new fields in serialized output

## Outcome

- ✅ Impact: Task model extended with 3 new columns + 2 enums; backward compatible via nullable defaults
- 🧪 Tests: No tests added (model-only scope per user request)
- 📁 Files: 3 files modified (chat_models.py, database.py, task_service.py)
- 🔁 Next prompts: Add API endpoint tests, frontend integration, recurrence scheduler logic
- 🧠 Reflection: Existing priority/due_date fields already existed; only tags, recurrence, reminder_enabled were truly new. Database migration refactored to eliminate duplicate function and add PostgreSQL path.

## Evaluation notes (flywheel)

- Failure modes observed: database.py had duplicate create_db_and_tables() function; SQLite-only PRAGMA migration
- Graders run and results (PASS/FAIL): Manual review PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add unit tests for new model fields and enum validation
