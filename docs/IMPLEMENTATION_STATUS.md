# Implementation Status

**Updated:** 2026-09-06 - M6 asynchronous communication implementation.

The source-of-truth design remains in `docs/project/`. This map separates verified
portfolio functionality from production readiness. Exact checkpoints are recorded in
[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).

| Area | Current implementation | Boundary / next work |
|---|---|---|
| Phases 0-1 | Docker Compose, FastAPI, SQLAlchemy/Alembic, health/readiness and demo organization | Staging, TLS, backups and production observability remain |
| Phase 2 / M1 | Argon2, access JWT, rotating hashed refresh sessions, logout, `/me`, normalized roles | Secure-cookie transport, immediate access-token revocation, rate limiting and scoped role administration remain |
| Phase 3 | Authenticated workspace and role-aware navigation | Incremental UX/component extraction remains |
| Phase 4 / M2 | Published catalog, typed versioned forms, private drafts, deterministic validation and revision conflicts | Advanced conditional form rules remain |
| Phase 5 / M3 | Sequential ALL workflows, deterministic resolvers, atomic submit, exact-assignee inbox, approve/reject/request-changes and immutable attempts | No ANY/conditional routing/delegation; unavailable assignees fail safely |
| Phase 6 / M4 | Append-only timeline, scoped public/internal comments, privileged audit workspace and database mutation guards | Retention/redaction/WORM storage and DB-owner tamper resistance remain |
| Phase 7 / M5 | Exactly-one fulfillment work item after final approval, team queue, assignment/start/wait/resume/resolve/close and aggregate/timeline/audit propagation | SLA-at-risk semantics deferred to Phase 13; richer staffing UX remains |
| Phase 8 | Request attachment metadata + MinIO/S3 bytes, bounded presigned upload, authorized short-lived download, visibility and completion verification | Malware scanning, trusted checksum, retention/deletion and multipart files remain |
| **Phase 9 / M6** | **PostgreSQL notification intent, recipient-scoped in-app notifications, Redis/Dramatiq email worker, Mailpit dev adapter, persisted retry/backoff and browser notification center** | Production email provider/idempotency, push/Teams/Slack, realtime SSE/WebSocket and preferences remain |
| Phase 10 / M7 | Legacy triage adapters/mock provider only | Schema-aware catalog classification/extraction/clarification UI and held-out evaluation are next |
| Phase 11 / M8 | Legacy lexical retrieval/citations only | Ingestion, embeddings, pgvector, permission-aware RAG and evaluation |
| Phase 12 | Backend catalog/workflow version publishing APIs | Full admin configuration/user-role-policy UI |
| Phase 13 | Fixed prototype workflow deadline only | Business calendar, SLA-at-risk definition, scheduled checks and escalation |
| Phase 14 | Legacy summary/feed and illustrative charts | Governed approval/fulfillment analytics and real BI evidence |
| Phases 15-16 | CI, migrations, PostgreSQL races and Docker/Chromium smoke | Dependency remediation, failure/load/security review and deployment hardening |

## Current governed path

```text
Employee
  -> published catalog + typed private draft
  -> optional authorized attachments
  -> deterministic sequential human approval
  -> exactly one service work item
  -> authorized service fulfillment
  -> requester-visible timeline/audit
  -> durable in-app notification intent
  -> asynchronous email delivery/retry
```

M6 keeps network delivery outside the business transaction. Approval/fulfillment code
writes a notification intent atomically with its domain update; a separate worker later
delivers email. Therefore delivery failure cannot cause the worker to re-run a human
approval or service state transition.

Notification creation is database-idempotent by event/channel. External SMTP remains
at-least-once around the narrow acceptance-before-SENT-record window, so exact-once
email is not claimed. See [M6_ASYNC_NOTIFICATIONS.md](M6_ASYNC_NOTIFICATIONS.md).

Next vertical slice after M6: **Phase 10 / M7 schema-aware AI intake**. Classification
and extraction must map to the published catalog/schema, remain editable, compute
missing required fields deterministically and require employee confirmation. Policy
RAG remains Phase 11 after that standard intake path is evaluated.