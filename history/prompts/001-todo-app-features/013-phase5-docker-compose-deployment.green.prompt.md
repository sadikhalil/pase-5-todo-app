---
id: 013
title: Phase 5 Docker Compose Production Deployment
stage: green
date: 2026-02-11
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: user
command: implement
labels: ["deployment", "docker", "docker-compose", "mcp", "production", "phase5"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - docker-compose.yml
  - backend/Dockerfile.mcp
  - backend/.dockerignore
  - frontend/.dockerignore
  - frontend/Dockerfile
  - .env.production
tests:
  - docker compose up --build (all 5 services start)
  - MCP server not reachable from host (no port mapping)
  - Backend reaches MCP internally at http://mcp-server:8001
  - Both backend and MCP share same PostgreSQL database
  - Chatbot persists tasks to the same DB as the dashboard
---

## Prompt

You are acting as a senior DevOps + Backend engineer. My project already has a Next.js frontend, a FastAPI backend, an MCP server used by the chatbot, PostgreSQL, and Dockerfiles for frontend and backend. Phase 5 requirement: production-ready public deployment using Docker Compose (not Kubernetes). Tasks: Review Dockerfiles, create docker-compose.yml with MCP as separate internal service, wire environment variables, ensure chatbot persists to same DB, provide deployment commands and Phase 5 explanation.

## Response snapshot

Full audit of 15+ source files revealed:
- Standalone MCP server (backend/mcp/mcp_server.py) runs as separate FastAPI on port 8001, shares MCPTaskService + same DATABASE_URL
- Backend chatbot calls MCPTaskService in-process (not over HTTP) — no business logic change needed
- Both processes write to same PostgreSQL via shared service layer

Created production docker-compose.yml with 5 services:
1. frontend (port 3000, public) — Next.js with build-time API URL injection
2. todo-api (port 8000, public) — FastAPI backend with embedded MCP routes + event bus
3. mcp-server (port 8001, INTERNAL ONLY via expose, no host mapping) — standalone MCP
4. db (internal) — PostgreSQL 15 with healthcheck + persistent volume
5. redis (internal) — Redis 7 for event bus Streams + persistent volume

Created Dockerfile.mcp (same codebase, different entrypoint). Added .dockerignore files. Created .env.production template.

## Outcome

- Impact: Production-ready 5-service Docker Compose deployment with proper network isolation
- Tests: Manual deployment verification required
- Files: 6 files created/modified
- Next prompts: Deploy on VM and verify all services
- Reflection: MCP isolation via expose-only (no ports) is the correct Docker pattern for internal services

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Deploy and smoke test
