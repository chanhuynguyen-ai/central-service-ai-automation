# Implementation Status

**Updated:** 2026-09-05 - M5 service fulfillment implementation.

The source-of-truth design remains in `docs/project/`. This map separates verified
portfolio functionality from production readiness. Exact delivery checkpoints are
recorded in [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).

| Area | Current implementation | Boundary / next work |
|---|---|---|
| Phases 0-1 | Docker Compose, FastAPI, SQLAlchemy/Alembic, health/readiness, demo organization | Staging, TLS, backups and production observability remain |
| Phase 2 / M1 | Argon2, access JWT, hashed rotating refresh sessions, logout, `/me`, normalized roles | Secure-cookie transport, immediate access-token revocation, rate limiting and scoped role administration remain |
| Phase 3 | Authenticated workspace and role-aware navigation | Incremental UX/component extraction remains |
| Phase 4 / M2 | Published catalog, versioned typed forms, private drafts, deterministic validation and revision conflicts | Attachments and advanced conditional form rules remain |
| Phase 5 / M3 | Sequential ALL workflows, USER/MANAGER/ROLE/TEAM_LEAD resolvers, atomic submit, exact-assignee inbox, approve/reject/request changes and immutable attempts | No ANY/conditional routing/delegation; unavailable assignees fail safely |
| Phase 6 / M4 | Append-only timeline, scoped public/internal comments, privileged audit workspace and database mutation guards | Retention/redaction/WORM storage and DB-owner tamper resistance remain |
| **Phase 7 / M5** | **Exactly-once work item after final approval, team queue, self-claim/assignment API, start/wait/resume/resolve/close, aggregate/timeline/audit propagation** | SLA-at-risk semantics deferred to Phase 13; richer lead assignment/staffing UI remains |
| Phase 8 | MinIO infrastructure only | Authorized presigned upload/download and file lifecycle |
| Phase 9 / M6 | Redis infrastructure only | Worker, asynchronous notifications and delivery retries |
| Phase 10 / M7 | Legacy triage adapters/mock provider only | Structured classifier/extraction/clarification UI and held-out evaluation |
| Phase 11 / M8 | Legacy lexical retrieval/citations only | Ingestion, embeddings, pgvector, permission-aware RAG and evaluation |
| Phase 12 | Backend catalog/workflow version publishing APIs | Full admin configuration/user-role-policy UI |
| Phase 13 | Fixed prototype workflow deadline only | Business calendar, SLA-at-risk definition, scheduled checks and escalation |
| Phase 14 | Legacy summary/feed and illustrative charts | Governed approval/fulfillment analytics and real BI evidence |
| Phases 15-16 | CI, migrations, PostgreSQL races and Docker/Chromium smoke | Dependency remediation, failure/load/security review and deployment hardening |

## Current governed path

```text
Employee
  -> published catalog + typed private draft
  -> deterministic sequential human approval
  -> exactly one service work item
  -> authorized team queue / assignment
  -> start / wait / resume / resolve / close
  -> requester-visible status + timeline
  -> audit history
```

The application checkpoint `05c264b` passed CI #65, PostgreSQL #38 and browser
#41. Backend suite: **134 passed**, **83% total statement coverage**. See the progress
tracker and PR #13 for exact run IDs. This verification does not certify production
security, scale or regulatory compliance.

M5 keeps approval and fulfillment separate: final approval queues operational work;
it does not silently mark the request completed. The service queue is authorized by
server-side service-team membership/leadership and optimistic work-item versions.

Next vertical slice: **Phase 8 authorized attachments with MinIO/S3-compatible
storage and short-lived presigned URLs**. AI intake/RAG remain after the reliable
standard workflow path.

For M5 API, permissions, migration and demo instructions, see
[M5_SERVICE_FULFILLMENT.md](M5_SERVICE_FULFILLMENT.md).
