# M5 - Service fulfillment

## Scope

M5 completes the standard governed lifecycle after human approval. A final approval
creates exactly one service work item for the snapshotted owner service team. Service
agents then claim or receive work, start it, optionally wait for the requester,
resume, resolve with an outcome, and close the request.

Approval and fulfillment remain separate lifecycles. `approved` means the human
approval chain is complete. `queued` means operational work exists but has not yet
started. Only `CLOSED` fulfillment marks the request aggregate `completed`.

M5 does not implement attachments, asynchronous notifications, business-calendar
SLA escalation, AI intake or policy RAG.

## Run after PR #13 merge

From a clean repository root with Docker Desktop running:

```powershell
Set-Location "C:\AI_project\central-service-ai-automation"
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
docker compose up -d --build --wait --wait-timeout 180
docker compose exec api alembic current
Invoke-RestMethod "http://localhost:8000/health"
Invoke-RestMethod "http://localhost:8000/ready"
Start-Process "http://localhost:3000"
```

Expected migration head: **g8c2e5b7d934**. It follows M4 `f7b1d4a6c823`.
The migration creates `service_work_items` and backfills older finally-approved
requests only when an owner service team is deterministically recoverable from the
pinned workflow snapshot. Existing request, approval, activity and audit history is
retained. Do not delete persistent volumes as an upgrade strategy.

For a fresh demo database:

```powershell
docker compose exec api python -m app.db.seed_catalog
docker compose exec api python -m app.db.seed_workflows
```

Create and fully approve a laptop replacement through the M3 flow. Final approval
will queue service work automatically in the same business transaction.

## Demo accounts

| Role | Email | Local-only password | M5 capability |
|---|---|---|---|
| Requester | employee@centralops.demo | Employee123! | Observe request status and timeline |
| Service agent | service.agent@centralops.demo | ServiceAgent123! | Team queue, self-claim, perform assigned work |
| Service lead | service.lead@centralops.demo | ServiceLead123! | Team queue, service-team oversight and assignment API |
| Administrator | admin@centralops.demo | Admin123! | Cross-team service queue administration |
| Prototype approver | approver@centralops.demo | Approver123! | No fulfillment access from APPROVER alone |

After signing into the main workspace, service staff can open:

`http://localhost:3000/service-queue`

The dedicated page reuses the authenticated browser session. Backend authorization,
not the page role check, is authoritative.

## Fulfillment lifecycle

```text
Final approval
  -> QUEUED
  -> ASSIGNED
  -> IN_PROGRESS
  -> WAITING_REQUESTER (optional)
  -> IN_PROGRESS (resume)
  -> RESOLVED
  -> CLOSED
```

Request aggregate propagation:

| Work status | Request status | fulfillment_state |
|---|---|---|
| QUEUED | approved | queued |
| ASSIGNED | approved | assigned |
| IN_PROGRESS | in_progress | in_progress |
| WAITING_REQUESTER | in_progress | waiting_requester |
| RESOLVED | resolved | resolved |
| CLOSED | completed | closed |

A resolution summary is required before `resolve`. Closing is allowed only after
resolution. Posting a comment or adding an approval does not directly complete a
service work item.

## Authorization

Server-side rules are team scoped:

- `SERVICE_AGENT` or `SERVICE_LEAD` must belong to the exact service team, unless
  the user is an `ADMIN`.
- An agent can self-claim an unassigned item.
- A service lead or administrator can assign another active, eligible member of the
  same team through the API.
- After assignment, operational state changes are restricted to the assignee or the
  team lead/administrator.
- `APPROVER` alone does not grant service queue access.
- Requesters cannot mutate service work by guessing a numeric ID.
- Every action includes the current work-item `version`; stale actions return 409.

The UI currently focuses on the recruiter/demo path of an agent self-claiming work.
Lead-to-agent explicit assignment is available through the governed backend action
API; a richer staffing picker is intentionally left for a later admin/operations UX
slice rather than introducing an unscoped user directory.

## API

All paths require authentication and start with `/api/v1`.

| Method and path | Behavior |
|---|---|
| GET `/fulfillment/work-items?scope=team` | Authorized team queue |
| GET `/fulfillment/work-items?scope=unassigned` | Unassigned queued work |
| GET `/fulfillment/work-items?scope=mine` | Work assigned to caller |
| POST `/fulfillment/work-items/{id}/actions` | assign/start/wait/resume/resolve/close |

Example self-claim payload:

```json
{
  "action": "assign",
  "version": 1
}
```

Example resolution payload:

```json
{
  "action": "resolve",
  "version": 5,
  "note": "Replacement laptop configured and handed to the requester."
}
```

The server does not accept client-provided lifecycle status, requester identity or
audit actor. Team-lead assignment may additionally provide `assignee_user_id`, which
is checked against the active service team.

## Transactions, concurrency and history

Final approval and initial work-item creation share the same transaction. If the
owner service team cannot be resolved safely, the final approval returns a conflict
rather than persisting an approved request with no operational owner.

`request_id` is unique in `service_work_items`. Work actions lock the item and apply
an optimistic version predicate. PostgreSQL CI opens independent connections to
race two claims of the same queued item; exactly one succeeds and the other returns
409. The test also verifies one work item and one assignment audit event.

Every lifecycle transition records safe audit metadata and a requester-visible domain
event without copying the resolution body into audit metadata. The request timeline
labels queue, assignment, start, requester wait, resume, resolution and closure.

## Verified checkpoint

Application checkpoint: `05c264ba88ce8087865c930013d84bb1b3ffabb5`.

- CI #65 / `33971368204`: SUCCESS. Ruff, clean SQLite migration, **134 backend tests**,
  **83% total statement coverage**, TypeScript, ESLint, production build and frontend tests.
- PostgreSQL #38 / `33971368207`: SUCCESS. Clean PostgreSQL migration, M3 races,
  M4 append-only/idempotency gates, and M5 final-queue/concurrent-claim verification.
- Browser/PostgreSQL #41 / `33971368246`: SUCCESS. Production Docker + Chromium
  through M2/M3/M4 regressions and M5 queued -> claim -> start -> wait -> resume ->
  resolve -> close, followed by requester-visible completed status/timeline.

These are functional and concurrency checks on synthetic CI data, not a load test,
production-security certification, SLA guarantee or external-service validation.

## Deferred items

The Phase 7 design mentions an SLA-at-risk queue. M5 deliberately does not invent a
business-calendar SLA definition: the project roadmap has a dedicated Phase 13 for
SLA/escalation semantics. `due_at` is reserved on the work item, but no misleading
SLA-at-risk filter is exposed until that policy exists.

Next roadmap phase: **Phase 8 - authorized attachments with MinIO/S3-compatible
storage and short-lived presigned URLs**.
