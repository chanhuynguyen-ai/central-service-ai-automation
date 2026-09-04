# Implementation Status

This file maps the current codebase to the project source-of-truth in `docs/project/`.
It is intentionally conservative: a phase is not marked complete merely because a file or UI
placeholder exists.

## Status legend

- **DONE** - implemented and verifiable in the repository.
- **PARTIAL** - meaningful implementation exists, but acceptance criteria are not yet met.
- **MISSING** - required capability is not implemented.
- **CANNOT VERIFY** - repository contains an artifact/specification, but real-environment evidence is not available.

## Roadmap audit

| Roadmap area | Status | Evidence in current repository | Main gap |
| --- | --- | --- | --- |
| Phase 0 - repository foundation | DONE | README, Docker, CI, docs, env example | Keep source-of-truth docs synchronized |
| Phase 0 - PostgreSQL/Redis/MinIO infrastructure | PARTIAL | PostgreSQL Docker service; Redis/MinIO added in project-start hardening | Redis/MinIO are not consumed by the application yet |
| Phase 1 - FastAPI foundation | DONE | FastAPI app, health/readiness, config, request ID/logging | Expand operational metrics later |
| Phase 1 - SQLAlchemy/Alembic | PARTIAL | SQLAlchemy models; Alembic baseline added in project-start hardening | Domain schema still reflects the simplified prototype |
| Phase 2 - authentication | PARTIAL | Argon2 password hashing, expiring JWT, `/auth/me` | Refresh rotation, logout/revocation, SSO/OIDC adapter |
| Phase 2 - RBAC | PARTIAL | employee/approver/admin server-side checks | Role table/scopes, manager relationship, service roles, centralized contextual policies |
| Phase 3 - frontend shell | DONE | React/TypeScript workspace, login, navigation, API client | Split monolithic workspace into domain features as functionality grows |
| Phase 4 - request catalog/versioning | MISSING | Fixed category choices only | `request_types`, versioned schemas, publish lifecycle |
| Phase 4 - dynamic forms/drafts | MISSING | Single hard-coded request form | JSON form schema, draft API, renderer, server validation |
| Phase 5 - deterministic workflow engine | MISSING | Single direct approve/reject transition | Workflow definitions/versions/instances/steps and approver resolvers |
| Phase 5 - approval inbox/actions | PARTIAL | API approve/reject and dashboard placeholder | Assigned approval tasks, inbox UI, request changes, concurrency protection |
| Phase 6 - request timeline/audit | PARTIAL | AuditEvent persistence | Request detail timeline UI, broader admin audit log, append-only policy |
| Phase 7 - service fulfillment | PARTIAL | Generic status update | Service work item, queue, assignee permissions, wait/resolve/close lifecycle |
| Phase 8 - attachments | MISSING | None | MinIO/S3 presigned upload and download authorization |
| Phase 9 - notifications/worker | MISSING | Automation run records only | Redis worker, in-app notifications, email adapter, retry/idempotency |
| Phase 10 - AI intake | PARTIAL | AI category/priority/summary, provider fallback | Schema-aware field extraction, missing-field clarification, evaluation dataset |
| Phase 11 - policy RAG | PARTIAL | Lexical retrieval with grounded article citation | document ingestion, chunks, pgvector/hybrid retrieval, access scope, offline eval |
| Phase 12 - admin configuration | MISSING | None | Request type/workflow/user/policy admin editors |
| Phase 13 - SLA/escalation | PARTIAL | Due timestamp and dashboard metric | business calendar, scheduled checker, warnings/escalation |
| Phase 14 - analytics | PARTIAL | API KPIs, Power BI feed/spec | trend endpoints, approval/resolution duration, real Power BI evidence |
| Phase 15 - hardening | PARTIAL | tests, CI, responsible-AI document | rate limits, refresh sessions, security tests, failure/load tests, observability |
| Phase 16 - deployment | PARTIAL | Docker Compose and container images | staging deployment, TLS/secrets, backup/restore, OpenTelemetry |

## Current verified milestone

The repository is a strong **prototype/POC**, but it has not yet reached project milestone M3
from the source-of-truth roadmap because the deterministic versioned workflow engine and
real approval task model are not implemented.

The next core vertical slice is:

> Versioned request catalog + draft -> deterministic workflow instance -> manager approval task.

Do not expand autonomous AI behavior before this core slice is correct.
