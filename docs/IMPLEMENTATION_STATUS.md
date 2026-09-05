# Implementation Status

**Updated:** 2026-09-05 - M3 workflow implementation.

The source-of-truth design remains in `docs/project/`. This map distinguishes a
working portfolio slice from production readiness. For exact verification runs
and merge checkpoints use [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md). The previous
pre-M3 audit is retained in [history](history/IMPLEMENTATION_STATUS_pre_M3.md).

| Area | Current implementation | Boundary / next work |
|---|---|---|
| Phases 0-1 | Docker Compose, FastAPI, SQLAlchemy/Alembic, health/readiness, demo organization | Staging, TLS, backups and production observability remain |
| Phase 2 / M1 | Argon2, access JWT, hashed rotating refresh sessions, logout, /me, normalized roles | Cookie transport, immediate access-token revocation, rate limiting and scoped role administration remain |
| Phase 3 | Real authenticated workspace, role-aware navigation, explicit loading/error states | Incremental component extraction; fuller session race hardening |
| Phase 4 / M2 | Published catalog, versioned typed forms, private drafts, deterministic validation, revision conflicts | Attachments and advanced conditional/validation rules are explicitly unsupported |
| Phase 5 / M3 | Sequential ALL workflows, USER/MANAGER/ROLE/TEAM_LEAD resolvers, atomic submit, exact-assignee inbox, approve/reject/request changes, retained attempts | No ANY/conditional routing/delegation; unavailable assignees fail safely for administrator attention |
| Phase 6 / M4 | Workflow attempt/decision history and transactional audit events exist | Full domain-event timeline, comments/internal-note visibility and audit UI are next |
| Phase 7 / M5 | Final approval explicitly records fulfillment as not_queued | Service work item, queue, assignment, wait/resolve/close are not implemented |
| Phase 8 | MinIO infrastructure only; attachment input unavailable | Authorized upload/download and file lifecycle |
| Phase 9 / M6 | Redis infrastructure only | Worker, asynchronous notifications and delivery retries |
| Phase 10 / M7 | Legacy triage adapters/mock provider; deterministic schema validator usable by later intake | Structured classifier/extraction/clarification UI and held-out evaluation set |
| Phase 11 / M8 | Legacy lexical article retrieval and backend citations | Document ingestion, embeddings, pgvector, permission-aware retrieval and evaluation |
| Phase 12 | Backend catalog/workflow version publication APIs | Full admin configuration, user/role and policy editors |
| Phase 13 | Fixed elapsed-hour approval deadline per workflow version | Business calendar, scheduled SLA checks and escalation |
| Phase 14 | Explicitly separate legacy summary/feed and illustrative charts | Real structured approval/fulfillment trends and Power BI tenant evidence |
| Phases 15-16 | Regression tests, migration gates, PostgreSQL races, Chromium Docker smoke | Dependency remediation, load/failure tests, deployment/security review |

## Interpretation

A passing migration does not prove browser UX, and a green CI does not certify
production security. M2 and M3 use real persistence and human decisions; they do
not claim completed fulfillment or measured AI model quality. The legacy simple
request and integration endpoints cannot bypass the new structured workflow.

The immediate next vertical slice is **Phase 6: full request timeline, comments
and protected internal notes**, then the Phase 7 fulfillment work item/queue.
The documented AI phases remain after a reliable standard request path.
