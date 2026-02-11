---
id: 012
title: Phase 5 UI Features Implementation
stage: green
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: user
command: implement
labels: ["frontend", "ui", "tags", "recurrence", "filtering", "sorting", "sse", "clear-completed"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - frontend/contexts/TodoContext.tsx
  - frontend/components/TodoInput.tsx
  - frontend/components/SortableTodoItem.tsx
  - frontend/components/TodoFilters.tsx
  - frontend/components/SortableTodoList.tsx
  - frontend/pages/todo.js
tests:
  - Manual verification via UI (tags input, recurrence dropdown, filter/sort controls, clear completed, SSE toasts)
---

## Prompt

Implement the following plan:

# Phase 5 UI Features - Implementation Plan

## Context
Phase 5 backend is fully built (event-driven architecture, task metadata extensions, SSE streaming), but the frontend UI is missing several features needed to surface these capabilities. This plan adds tags/recurrence inputs, advanced filtering/sorting, clear completed, SSE real-time notifications, and reminder toggle to the todo UI.

## Files to Modify (in order)

### Step 1: `frontend/contexts/TodoContext.tsx` - Extend state management
### Step 2: `frontend/components/TodoInput.tsx` - Tags + recurrence in create form
### Step 3: `frontend/components/SortableTodoItem.tsx` - Tags + recurrence in edit form
### Step 4: `frontend/components/TodoFilters.tsx` - Advanced filter/sort controls
### Step 5: `frontend/components/SortableTodoList.tsx` - Multi-stage filter + sort pipeline
### Step 6: `frontend/pages/todo.js` - Clear Completed + SSE EventToast
### Step 7: Implicit reminder_enabled (no explicit UI)

## Response snapshot

Implemented all 7 steps of the Phase 5 UI Features plan:

1. **TodoContext.tsx**: Extended `TodoState` with `sortBy`, `sortOrder`, `priorityFilter`, `tagFilter`. Extended `addTodo`/`updateTodo` signatures with `tags`/`recurrence` params. Added `SET_SORT_BY`, `SET_SORT_ORDER`, `SET_PRIORITY_FILTER`, `SET_TAG_FILTER` reducer cases. Added `reminder_enabled` to API calls (inferred from reminder date).

2. **TodoInput.tsx**: Added `tags` state with chip-style input (type + Enter to add, click X to remove). Added `recurrence` dropdown (none/daily/weekly/monthly). All new fields passed to `addTodo` and reset after submission.

3. **SortableTodoItem.tsx**: Added `editTags`, `editTagInput`, `editRecurrence` state pre-populated from todo. Added tag chip editor with X removal (using lucide-react `X` icon) and recurrence dropdown to edit form. Updated `onEdit` prop and `handleSubmit` to pass new fields.

4. **TodoFilters.tsx**: Rebuilt with 3 rows: status filter (All/Active/Completed), priority filter (All/High/Medium/Low with priority colors), sort+tag controls (sort dropdown + asc/desc toggle + dynamic tag filter from unique tags).

5. **SortableTodoList.tsx**: Replaced simple filter with `useMemo`-based multi-stage pipeline: status -> priority -> tag -> sort. Sort supports priority (high=3, medium=2, low=1), dueDate, name, createdAt. `SortableContext` disabled when `sortBy !== 'manual'`. Empty state message accounts for active filters.

6. **todo.js**: Extracted `TodoPageContent` inside `TodoProvider` so hooks work. Added `ClearCompletedSection` (hidden when 0 completed). Integrated `EventToast` + `useEventToasts` hook. SSE connection via `apiClient.connectEventStream()` with cleanup on unmount. Auto-refreshes todos on SSE events.

## Outcome

- Impact: Full Phase 5 UI feature set implemented - tags, recurrence, advanced filtering/sorting, clear completed, SSE real-time notifications
- Tests: Manual UI verification required
- Files: 6 files modified
- Next prompts: Build and test the application, verify all 10 verification steps from the plan
- Reflection: Clean implementation following the dependency order. Key design decisions maintained: client-side filtering, sort overrides drag-and-drop, tag filter derived from current todos, reminder_enabled inferred from date.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A - manual verification needed
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run the app and test all 10 verification steps
