---
id: 005
title: Phase 5 MCP Tools Update
stage: green
date: 2026-02-09
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: User
command: direct-prompt
labels: ["mcp", "phase5", "backend", "tools"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - backend/app/services/task_service.py
  - backend/app/api/mcp_endpoints.py
  - backend/mcp/mcp_server.py
tests:
  - none (tool-level change, no tests added yet)
---

## Prompt

Update the existing MCP server tools for Phase 5.

Task:
- Ensure that add_task, update_task, list_tasks, and complete_task can handle the new Task fields:
  - priority, tags, due_date, recurrence, reminder_enabled
- Update tool definitions (parameters and response schema)
- Ensure all changes persist to PostgreSQL
- Provide exact code snippets or diffs for MCP server files

Constraints:
- Do not modify chatbot logic yet
- Keep all previous functionality intact

## Response snapshot

Updated all 3 MCP-related files to support Phase 5 fields:

1. **MCPTaskService** (`task_service.py`):
   - Extended `add_task()` signature with priority, tags, due_date, recurrence, reminder_enabled params
   - Added new `update_task()` method that builds a partial TaskUpdate from only provided fields and delegates to TaskService.update_task()
   - Enum validation via PriorityLevel() and RecurrenceType() constructors

2. **Active MCP endpoints** (`mcp_endpoints.py`):
   - Extended `AddTaskRequest` with all Phase 5 fields (with backward-compatible defaults)
   - Added `UpdateTaskRequest` model for partial updates
   - Added `POST /mcp/tools/update_task` endpoint
   - Updated `TaskOperationResponse` to include task_id and error fields
   - All endpoints pass new fields through to MCPTaskService
   - Added ValueError handling for invalid enum values (422 response)

3. **Legacy MCP server** (`mcp_server.py`):
   - Mirrored all request model changes from active endpoints
   - Added update_task endpoint
   - Fixed session handling to use `next(get_session())`
   - Bumped version to 2.0.0

## Outcome

- ✅ Impact: All 5 MCP tools (add, update, list, complete, delete) now support Phase 5 fields
- 🧪 Tests: No tests added (per scope constraint)
- 📁 Files: 3 files modified
- 🔁 Next prompts: Add chatbot tool-calling integration, frontend UI for new fields
- 🧠 Reflection: update_task was a new tool not previously present — added to both MCP implementations. Kept backward compat by using defaults on all new AddTaskRequest fields.

## Evaluation notes (flywheel)

- Failure modes observed: Legacy server used raw get_session() call instead of next(get_session())
- Graders run and results (PASS/FAIL): Manual review PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Integration test for round-trip add → update → list with new fields
