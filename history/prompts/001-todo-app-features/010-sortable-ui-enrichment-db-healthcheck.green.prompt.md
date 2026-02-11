---
id: 010
title: Enrich SortableTodoItem UI + Add DB Healthcheck
stage: green
date: 2026-02-09
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: User
command: implement plan
labels: ["ui-enrichment", "docker", "healthcheck", "metadata-display"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - frontend/types/todo.ts
  - frontend/contexts/TodoContext.tsx
  - frontend/components/SortableTodoItem.tsx
  - docker-compose.yml
tests:
  - Manual: verify dashboard shows priority badge, due date, created date, tags, recurrence
  - Manual: verify edit form on dashboard includes description, priority, due date, reminder
  - Manual: docker-compose up confirms db healthy before todo-api starts
---

## Prompt

Implement the following plan:

# Plan: Enrich SortableTodoItem UI + Add DB Healthcheck

## Context

The backend returns rich task metadata (priority, tags, due_date, created_at, updated_at, recurrence, reminder_enabled) but the primary dashboard component (`SortableTodoItem`) only renders the title, a status toggle, and a delete button. The richer `TodoItem` component (on `/todo`) already shows description, priority badges, and due dates — so we have an existing pattern to follow. Additionally, the `docker-compose.yml` db service lacks a healthcheck, meaning `todo-api` can start before PostgreSQL is ready.

## Changes

1. Add `tags` and `recurrence` to the frontend Todo type
2. Map `tags` and `recurrence` from backend responses in TodoContext
3. Enrich `SortableTodoItem` to show task metadata (priority badge, due date, created date, tags, recurrence)
4. Update `onEdit` prop signature and add rich edit form
5. Add PostgreSQL healthcheck to docker-compose

## Response snapshot

Implemented all 5 planned changes across 4 files:

1. **`frontend/types/todo.ts`** - Added `tags?: string[]` and `recurrence?: string` to the Todo interface.

2. **`frontend/contexts/TodoContext.tsx`** - Added `tags: todo.tags || []` and `recurrence: todo.recurrence || 'none'` mapping in both `fetchTodos` and `refreshTodos` blocks.

3. **`frontend/components/SortableTodoItem.tsx`** - Major enrichment:
   - Updated `onEdit` prop signature to match TodoItem: `(id, text, description?, dueDate?, reminderDate?, priority?)`
   - Added edit state for description, dueDate, reminderDate, priority
   - Added rich edit form with description textarea, priority select, due date, and reminder fields (matching TodoItem pattern)
   - Added metadata display row below title: priority badge (color-coded), due date with calendar emoji, recurrence with repeat icon, tag chips, and created date
   - Layout changed from single-row flex to stacked layout to accommodate metadata

4. **`docker-compose.yml`** - Added `healthcheck` to db service using `pg_isready -U postgres` with 5s interval/timeout/5 retries, and changed `todo-api` depends_on to use `condition: service_healthy` for db and `condition: service_started` for redis.

## Outcome

- ✅ Impact: Dashboard task cards now show full metadata matching the /todo page, and PostgreSQL readiness is verified before API starts
- 🧪 Tests: Manual verification required - dashboard metadata display, edit form fields, docker healthcheck
- 📁 Files: 4 files modified (todo.ts, TodoContext.tsx, SortableTodoItem.tsx, docker-compose.yml)
- 🔁 Next prompts: Consider adding tag editing in the edit form, add automated frontend tests
- 🧠 Reflection: Reused existing TodoItem visual patterns for consistency across dashboard and todo page

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A - manual verification
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add tag input field to edit form
