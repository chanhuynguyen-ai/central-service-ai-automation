# Implementation Status

**Updated:** 2026-09-06 - Phase 8 authorized request attachments implementation.

The source-of-truth design remains in `docs/project/`. This map separates verified
portfolio functionality from production readiness. Exact delivery checkpoints are
recorded in [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).

| Area | Current implementation | Boundary / next work |
|---|---|---|
| Phases 0-1 | Docker Compose, FastAPI, SQLAlchemy/Alembic, health/readiness, demo organization | Staging, TLS, backups and production observability remain |
| Phase 2 / M1 | Argon2, access JWT, hashed rotating refresh sessions, logout, `/me`, normalized roles | Secure-cookie transport, immediate access-token revocation, rate limiting and scoped role administration remain |
| Phase 3 | Authenticated workspace and role-aware navigation | Incremental UX/component extraction remains |
| Phase 4 / M2 | Published catalog, versioned typed forms, private drafts, deterministic validation and revision conflicts | Advanced conditional form rules remain |
| Phase 5 / M3 | Sequential ALL workflows, USER/MANAGER/ROLE/TEAM_LEAD resolvers, atomic submit, exact-assignee inbox, approve/reject/request changes and immutable attempts | No ANY/conditional routing/delegation; unavailable assignees fail safely |
| Phase 6 / M4 | Append-only timeline, scoped public/internal comments, privileged audit workspace and database mutation guards | Retention/redaction/WORM storage and DB-owner tamper resistance remain |
| Phase 7 / M5 | Exactly-once work item after final approval, team queue, self-claim/assignment API, start/wait/resume/resolve/close, aggregate/timeline/audit propagation | SLA-at-risk semantics deferred to Phase 13; richer lead assignment/staffing UI remains |
| **Phase 8** | **Request attachment metadata + MinIO/S3 bytes, bounded presigned POST, server-authorized short-lived GET, completion verification, requester/internal visibility, audit/timeline and request-detail upload/download UI** | Malware scanning/quarantine worker, retention/deletion, trusted checksum calculation and large multipart files remain |
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
  -> optional authorized request attachments
  -> deterministic sequential human approval
  -> exactly one service work item
  -> authorized team queue / assignment
  -> start / wait / resume / resolve / close
  -> requester-visible status + timeline
  -> audit history
```

Phase 8 keeps file bytes outside PostgreSQL and does not expose long-lived object
storage credentials to the browser. The backend authorizes the request before upload
reservation and again before every download URL. The upload policy is bounded by the
reserved file size and MIME type; completion verifies object metadata before READY.

This milestone deliberately does not claim malware safety. `QUARANTINED` is reserved
for a later scanning worker and `sha256` is not populated from an untrusted client
claim. See [M8_REQUEST_ATTACHMENTS.md](M8_REQUEST_ATTACHMENTS.md) for exact API,
storage and security boundaries.

Next vertical slice after Phase 8: **Phase 9 / M6 background worker and asynchronous
notifications with retry behavior**. AI intake/RAG remain after the reliable standard
workflow path.
