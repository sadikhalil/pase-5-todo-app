---
id: 011
title: Update Helm Charts for Phase 4 Full Stack
stage: green
date: 2026-02-09
surface: agent
model: claude-opus-4-6
feature: 001-todo-app-features
branch: main
user: User
command: implement
labels: ["helm", "kubernetes", "postgresql", "redis", "infrastructure"]
links:
  spec: specs/001-todo-app-features/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - todo-chatbot/values.yaml
  - todo-chatbot/Chart.yaml
  - todo-chatbot/templates/backend-deployment.yaml
  - todo-chatbot/templates/postgresql-statefulset.yaml
  - todo-chatbot/templates/postgresql-service.yaml
  - todo-chatbot/templates/redis-deployment.yaml
  - todo-chatbot/templates/redis-service.yaml
  - todo-chatbot/templates/redis-pvc.yaml
  - todo-chatbot/templates/NOTES.txt
  - todo-chatbot/templates/tests/test-connection.yaml
tests:
  - helm template test-release todo-chatbot — renders all manifests without errors
  - helm lint todo-chatbot — 0 charts failed
---

## Prompt

update helm charts according to my phase 4, they are in folder todo-chatbot

## Response snapshot

Updated the Helm chart from a frontend+backend-only chart to a full-stack chart matching the Phase 4 docker-compose architecture. Changes:

1. **values.yaml** — Added `postgresql` section (postgres:15, auth config, persistence, healthcheck), `redis` section (redis:7-alpine, append-only, persistence), and `backend.env` section (SECRET_KEY, EVENT_BUS_BACKEND).

2. **Chart.yaml** — Bumped chart version 0.1.0 → 0.2.0, appVersion 1.16.0 → 4.0.0.

3. **backend-deployment.yaml** — Added `initContainers` (wait-for-postgresql using busybox nc), and `env` block with DATABASE_URL (dynamically constructed from postgresql values), REDIS_URL (from redis service name), SECRET_KEY, EVENT_BUS_BACKEND.

4. **postgresql-statefulset.yaml** (new) — StatefulSet with postgres:15, POSTGRES_DB/USER/PASSWORD env vars, pg_isready liveness/readiness probes (matching docker-compose healthcheck), volumeClaimTemplate for persistent data.

5. **postgresql-service.yaml** (new) — ClusterIP service on port 5432.

6. **redis-deployment.yaml** (new) — Deployment with redis:7-alpine, `--appendonly yes` args, redis-cli ping probes, PVC volume mount.

7. **redis-service.yaml** (new) — ClusterIP service on port 6379.

8. **redis-pvc.yaml** (new) — 500Mi PersistentVolumeClaim for Redis data.

9. **NOTES.txt** — Added section 2 showing PostgreSQL and Redis connection info post-install.

10. **test-connection.yaml** — Extended to test backend, PostgreSQL, and Redis connectivity.

All resources are conditionally rendered via `postgresql.enabled` and `redis.enabled` flags. Validated with `helm template` and `helm lint` — 0 failures.

## Outcome

- ✅ Impact: Helm chart now deploys the complete Phase 4 stack (frontend + backend + PostgreSQL + Redis) matching docker-compose.yml
- 🧪 Tests: helm template renders cleanly, helm lint passes with 0 failures
- 📁 Files: 10 files (3 modified, 7 new templates)
- 🔁 Next prompts: Consider using Kubernetes Secrets instead of plain-text passwords in values, add NetworkPolicy templates
- 🧠 Reflection: Used StatefulSet for PostgreSQL (stateful workload) and Deployment for Redis (acceptable for single-instance cache/bus). Init container pattern mirrors docker-compose healthcheck dependency.

## Evaluation notes (flywheel)

- Failure modes observed: values.yaml cannot use Go template syntax — caught and fixed by constructing DATABASE_URL/REDIS_URL in the deployment template instead
- Graders run and results (PASS/FAIL): helm template PASS, helm lint PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Extract PostgreSQL password into a Kubernetes Secret
