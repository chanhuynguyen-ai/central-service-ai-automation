# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-05  
**Current delivery:** PR #13 - governed service fulfillment (M5)  
**Implementation branch:** `feat/service-fulfillment`

This is the canonical living tracker. Product/architecture requirements remain in
`docs/project/`; historical delivery snapshots remain in `docs/history/`. Passing
CI is evidence for the tested behavior, not a production-security, performance or
regulatory certification.

## Milestones

| Milestone | Verified state |
|---|---|
| M1 secure API foundation | Merged; auth/session/RBAC prototype and server-side permissions |
| Phase 3 role-aware frontend | Merged in PR #8 |
| M2 structured catalog/drafts | Merged in PR #9/#10 |
| M3 sequential approvals | Merged in PR #11 |
| M4 timeline/comments/audit | Merged in PR #12 at `6e95a28` |
| **M5 service fulfillment** | **Implemented and verified on PR #13 checkpoint `05c264b`; awaiting PR delivery cleanup/merge** |
| M6 async communication | Not implemented; Redis infrastructure only |
| M7 AI intake | Later phase; legacy triage is not M7 |
| M8 policy RAG | Later phase; lexical prototype is not M8 |

## Delivered in M5

- Final human approval creates exactly one `ServiceWorkItem` in the same business
  transaction; a missing deterministic owner service team fails safely instead of
  leaving an approved orphan.
- Owner team comes from the published request type snapshot, with a pinned TEAM_LEAD
  resolver fallback. Later configuration edits cannot reroute historical submissions.
- Work lifecycle: `QUEUED -> ASSIGNED -> IN_PROGRESS -> WAITING_REQUESTER ->
  IN_PROGRESS -> RESOLVED -> CLOSED`.
- Request aggregate remains distinct from approval: queued/assigned remain approved,
  active service work becomes `in_progress`, resolution becomes `resolved`, and only
  close makes the governed request `completed`.
- Team-scoped server authorization: SERVICE_AGENT/SERVICE_LEAD require exact team
  membership/leadership; ADMIN is cross-team. APPROVER alone cannot manage service work.
- Agents can self-claim; team leads/admin may assign an eligible member through the
  action API. Post-assignment transitions require the assignee or lead/admin.
- Compare-and-swap versioning plus row locking prevents stale/double actions.
  PostgreSQL CI races independent claims and verifies one winner/one 409.
- Service lifecycle audit/domain events are safe, append to the M4 timeline and do
  not copy resolution text into audit metadata.
- New authenticated `/service-queue` UI supports Team queue, Unassigned, Assigned to
  me, status filtering, claim/start/wait/resume/resolve/close and resolution summary.
- Requester-visible timeline now shows queue, assignment, start, wait, resume,
  resolution and closure.

## Verification checkpoint

Application checkpoint: `05c264ba88ce8087865c930013d84bb1b3ffabb5`.

| Gate | Evidence |
|---|---|
| CI backend + frontend | **#65 / 33971368204 SUCCESS** - Ruff, clean SQLite migration, **134 backend tests**, **83% total statement coverage**, TypeScript, ESLint, production build and frontend tests |
| PostgreSQL workflow gate | **#38 / 33971368207 SUCCESS** - clean PostgreSQL migration, M3 workflow races, M4 activity guards, M5 final queueing and concurrent claim probe |
| Production Docker + Chromium | **#41 / 33971368246 SUCCESS** - M2/M3/M4 regressions plus M5 queued -> claim -> start -> wait -> resume -> resolve -> close and requester completed timeline |

Normal API fixtures use SQLite for speed. Dedicated CI probes use PostgreSQL with
independent connections for the concurrency behavior that SQLite cannot prove.
Browser smoke uses disposable PostgreSQL and production Docker images with synthetic
demo data. No load benchmark or external AI/provider quality claim is made.

## Database and migration

M5 revision: `g8c2e5b7d934`, following M4 `f7b1d4a6c823`.

The migration adds `service_work_items`, indexes and a unique request-to-work-item
constraint. It backfills already-approved requests only when the pinned workflow
snapshot provides a deterministic active service team. Downgrade refuses to discard
progressed/assigned work. Back up persistent development data before schema changes;
do not use volume deletion as a migration or rollback method.

## Primary M5 files

- Domain model: `backend/app/models/fulfillment.py`
- Schemas: `backend/app/schemas/fulfillment.py`
- Service/authorization/state machine: `backend/app/services/fulfillment.py`
- API: `backend/app/api/routes/fulfillment.py`
- Final-approval integration: `backend/app/api/routes/workflows.py`
- Migration: `backend/alembic/versions/g8c2e5b7d934_add_service_fulfillment.py`
- PostgreSQL race probe: `backend/app/db/verify_fulfillment_concurrency.py`
- Backend tests: `backend/tests/test_fulfillment.py`, `test_fulfillment_api.py`
- Frontend: `app/service-queue/page.tsx`, `components/fulfillment/service-queue.tsx`, `lib/fulfillment-api.ts`
- Browser gate: `scripts/m5_browser_smoke.py`
- Run/reviewer guide: `docs/M5_SERVICE_FULFILLMENT.md`

## Explicit limits

The queue does not claim an SLA-at-risk calculation yet. The roadmap has a dedicated
Phase 13 for business-calendar SLA and escalation rules; M5 reserves `due_at` rather
than inventing a misleading SLA policy. The recruiter/demo UI focuses on agent
self-claim; lead-to-agent assignment exists in the server-side action API, while a
staff directory/picker belongs in later operations/admin UX.

M5 does not add attachments, notification delivery, AI intake or pgvector RAG.
Existing prototype auth still uses browser session storage/JSON refresh transport;
secure-cookie transport, immediate access-JWT revocation, rate limiting, dependency
remediation, TLS/backups, broader load/failure/security review and real Microsoft
tenant validation remain before shared production use.

## Next

**Phase 8 - Attachments:** authorized MinIO/S3-compatible object storage, presigned
upload completion and server-authorized short-lived download URLs. Malware scanning
remains a later security hook. Do not jump to AI before the governed standard request
path remains reliable through file handling and asynchronous communication.

## Run

After PR #13 is merged, pull `main`, rebuild Compose, check Alembic in the API
container and use [M5_SERVICE_FULFILLMENT.md](M5_SERVICE_FULFILLMENT.md). Existing
M2/M3/M4 guides remain valid for catalog, approvals and activity/audit behavior.
