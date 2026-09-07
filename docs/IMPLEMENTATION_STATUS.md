# Implementation Status

**Updated:** 2026-09-07 - M8 permission-aware policy RAG implementation.

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
| Phase 9 / M6 | PostgreSQL notification intent, recipient-scoped in-app notifications, Redis/Dramatiq email worker, Mailpit dev adapter, persisted retry/backoff and browser notification center | Production email provider/idempotency, push/Teams/Slack, realtime SSE/WebSocket and preferences remain |
| Phase 10 / M7 | Published-catalog classification, schema-bound extraction, deterministic missing-field/clarification flow, editable AI draft UX and 30-case evaluation corpus; merged in PR #16 | Production provider quality/cost/redaction evaluation remains |
| **Phase 11 / M8** | **Versioned policy documents, pgvector chunks, pre-retrieval permission/effective-date filtering, grounded citations, insufficient-evidence handling and dedicated Knowledge UI in PR #18** | Exact-head CI/PostgreSQL/Chromium verification is required before merge; production embedding/model evaluation remains |
| Phase 12 | Backend catalog/workflow version publishing APIs already exist in part | Full admin configuration UI, role/service-team management, and policy publish/retire management |
| Phase 13 | Fixed prototype workflow deadline only | Business calendar, SLA-at-risk definition, scheduled checks and escalation |
| Phase 14 | Legacy summary/feed and illustrative charts | Governed approval/fulfillment analytics and real BI evidence |
| Phases 15-16 | CI, migrations, PostgreSQL races and Docker/Chromium smoke | Dependency remediation, failure/load/security review and deployment hardening |

## Current governed path

```text
Employee
  -> published catalog or advisory AI intake
  -> explicit review + typed private draft
  -> optional authorized attachments
  -> deterministic sequential human approval
  -> exactly one service work item
  -> authorized service fulfillment
  -> requester-visible timeline/audit
  -> durable in-app notification intent
  -> asynchronous email delivery/retry

Policy question
  -> authenticated user
  -> published/effective/access-scope filter
  -> pgvector similarity retrieval
  -> grounded answer + evidence citations
  -> explicit insufficient-evidence result when support is weak
```

M7 does not create an autonomous path around the product. AI classification is limited
to active published services, extracted values are revalidated by the normal form
validator, missing fields come from the immutable published schema, and every suggestion
requires employee review before persistence. Authorization and approval routing remain
server-side deterministic decisions.

M8 applies the same governance principle to policy lookup. Document status, effective
dates and access scope are enforced before candidate chunks can enter model context.
The model cannot broaden access or turn retrieved text into approval authority. The UI
keeps citations visually distinct from generated answers and shows an explicit warning
when accessible evidence is insufficient.

The deterministic local/mock path is used for CI and repeatable demos. External Ollama
or OpenAI-compatible providers still require separate real-model quality, privacy,
latency, embedding and cost evaluation before any production claim.

Next vertical slice after PR #18 is final-green and merged: **Phase 12 / Admin
configuration**. Start with structured request-type/workflow/policy management; keep
published versions immutable and do not build a drag-drop BPMN canvas for the MVP.
