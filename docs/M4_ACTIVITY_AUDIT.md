# M4 - Request timeline, discussions and audit

## Scope

The M3 submitted-request detail now includes public discussion, permission-scoped
internal notes and an append-only activity timeline. ADMIN and AUDITOR accounts
also have a separate Audit log workspace. These features use the existing request
and audit aggregates; a second request store or redundant audit_logs table is not
introduced. Approval decisions remain under M3's exact-assignee policy.

M4 does not fulfill, notify or approve on behalf of a user. Posting a comment on an
approved/rejected request does not reopen it. Approved still means fulfillment
has not started. Attachments remain explicitly unavailable.

## Run after PR #12 merge

Run from the repository root with a clean working tree and Docker Desktop running.
Back up persistent development data before changing the schema.

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

Expected migration head for this release: **f7b1d4a6c823**. Use the API container
when checking Alembic so that the check targets the real Compose PostgreSQL data.
Do not delete database volumes or rerun old code-patching scripts.

There is no M4 seed to overwrite discussions or inject fake comments. An existing
M3 submitted request is sufficient. A fresh local installation can run:

```powershell
docker compose exec api python -m app.db.seed_catalog
docker compose exec api python -m app.db.seed_workflows
```

Then follow [the M3 guide](M3_WORKFLOW_APPROVALS.md) to submit a request.

## Local demonstration

| Account | Password (local demo only) | M4 task |
|---|---|---|
| employee@centralops.demo | Employee123! | Open own Submitted requests, post a Public comment |
| manager.finance@centralops.demo | Manager123! | Open a request actually assigned to this manager; read public discussion and add an Internal note |
| other.employee@centralops.demo | Employee123! | Verify that the first employee's request is not accessible |
| auditor@centralops.demo | Auditor123! | Read submitted activity/internal notes without a posting form; inspect Audit log |
| admin@centralops.demo | Admin123! | Inspect filtered system audit metadata |

Open **Submitted requests**, select a request, and scroll below the submitted
attempts. Public discussion is the default audience. Posting an Internal note
requires an explicit audience switch and confirmation. Public means visible to
people authorized for this request, not public internet access.

Save a public message, reload the page, and reopen the request to verify persistence.
Switch accounts using Sign out. A note recorded internally by the assigned reviewer
must not appear in the requester's discussion, timeline, or internal-note controls.
The auditor sees notes but cannot post. Audit log filters accept an event type
(such as internal_note_added) and the numeric request ID, not its DRF reference.

Comments are plain text: HTML is displayed rather than executed. Maximum length
is 5,000 characters; blank/control-character payloads are rejected. Comments
cannot be edited or deleted in this release: correct a mistake with a new comment.
Do not paste credentials or sensitive personal data. Unsent text is not a saved
comment; save before switching requests or leaving the workspace.

## Permission boundary

All reads first use the M3 submitted-request authorization policy. An unknown,
out-of-scope, legacy or never-submitted draft request returns 404.

| Caller for an already visible submitted request | Public read | Public write | Internal read | Internal write |
|---|---|---|---|---|
| Requester (not auditor-only) | Yes | Yes | No | No |
| Actual current/past assignee still holding APPROVER/ADMIN | Yes | Yes | Yes, unless requester | Yes, unless requester |
| Direct manager who is not an actual task assignee | Yes | Yes | No | No |
| ADMIN | Yes | Yes | Yes, unless requester | Yes, unless requester |
| AUDITOR without another scoped writing role | Yes | No | Yes, unless requester | No |

The requester exclusion wins for internal content, including a requester who also
has ADMIN. AUDITOR grants broad read access, not a broader write scope when combined
with an unrelated MANAGER/APPROVER role. Posting still needs ownership, actual
eligible assignment, direct management or ADMIN. An unrelated ordinary employee
or unassigned prototype approver cannot gain access by guessing a numeric ID.

Internal permissions are checked in SQL filtering before pagination and again
before posting. Hidden notes do not leak through the public timeline or cursor
counts. Public/private lists are fetched separately. UI role checks do not replace
backend authorization. Service-agent team access will be added with fulfillment,
not guessed from a global SERVICE_AGENT string.

## API

All paths require access-token authentication and start with /api/v1.

| Method and path | Behavior |
|---|---|
| GET /activity/requests/{id}/permissions | Server-computed comment/internal access |
| GET /activity/requests/{id}/timeline | Authorized domain events, newest ID first |
| GET /activity/requests/{id}/comments | Explicit visibility=REQUESTER_VISIBLE or INTERNAL |
| POST /activity/requests/{id}/comments | Append a comment and its audit/domain event atomically |
| GET /audit/events | ADMIN/AUDITOR only; viewing is itself audited |

List endpoints support limit (1-100, default 30) and before_id; responses contain
items and next_before_id. No edit/delete endpoints are exposed. Audit filtering
supports event_type and numeric request_id. Payload example:

```json
{
  "body": "The cost center has been confirmed.",
  "visibility": "REQUESTER_VISIBLE",
  "client_token": "f8f911df-752c-4ebd-a9ed-8a5a7db1884d"
}
```

Generate a fresh UUID for each new message. An exact same-key retry returns the
same comment (200 instead of the original 201). Reusing that key with different
content/audience returns 409. Keys are scoped to request and author. The browser
keeps the key on a failed retry but replaces it when content changes. Requester,
actor, timestamp and lifecycle state cannot be overposted.

## Events, transactions and audit coverage

The event stream records submission, workflow start, step assignment, approval,
rejection, changes requested, final approval and comments. The comment body lives
only in the authorized comment table; timeline/audit hold identifiers, not a
second copy. Private revision drafts remain private, as in M3.

A shared request-row lock serializes concurrent comment retries in PostgreSQL;
a unique (request, author, token) constraint is an additional guard. Comment,
audit and domain event commit together. An injected event failure is tested to
roll back the comment and audit. Workflow transition events participate in the
existing M3 transaction; failed decisions cannot leave a successful-looking event.

The existing audit_events table gains resource/correlation identifiers. New
safe audit records cover login/refresh/logout outcomes, catalog version changes,
workflow configuration/transitions, discussion writes and audit-list reads.
ORM UserRole insert/delete paths (including seed data) record grant/revoke IDs;
authenticated actor context is used when present, otherwise the actor is system.
This does not introduce a role-administration API or capture arbitrary raw SQL
changes made outside the application. Rejected schema-level requests are not a
complete security-attempt logging system.

Metadata is allowlisted; passwords, access/refresh tokens, form values and comment
bodies are not copied into new records or audit responses. Existing legacy audit
JSON is filtered on reads, not destructively rewritten. This is not retroactive
redaction of the underlying historical database. Client-controlled request IDs
are accepted into audit correlation only when they parse as UUIDs. Actor IDs are
stable; displayed names come from the current user record.

## Migration and append-only guarantees

Revision f7b1d4a6c823 follows e6a0c3f5b712. It adds request_events and
request_comments, enriches audit_events, and backfills recognized existing M3
transition audits. Original recorded times and source-audit IDs are retained.
Imported records are labeled backfilled. Unknown/malformed events and private
draft-edit events are not invented or published. Repeating upgrade does not replay
history. Existing request, form and approval records remain intact.

ORM mutation guards and database triggers reject UPDATE/DELETE on these three
history tables; PostgreSQL also rejects TRUNCATE. Downgrade refuses when it would
lose history. This is an application/database guard, not a cryptographically
signed, WORM or tamper-proof audit against a database owner who can remove triggers,
alter schema or restore a backup. Retention, legal erasure/redaction, archival,
log volume management and independent audit storage require a later policy and
implementation. Failed logins and privileged reads can grow audit volume; current
prototype auth does not yet have production rate limits.

## Verification and remaining work

Backend tests cover role combinations, owner isolation, hidden-note cursors,
strict input, idempotency, rollback, auth metadata, publication/role audit and
legacy redaction. Migration tests upgrade populated M3 SQLite data, check original
rows/timestamps, repeat upgrade, enforce raw-SQL history guards and refuse unsafe
rollback. Clean PostgreSQL migration and independent-connection comment/decision
races run separately in CI; ordinary API fixtures still use SQLite.

Frontend tests execute actual API helpers and the comment/timeline renderer,
including HTML escaping. Chromium tests use production Docker images/PostgreSQL
for public persistence, internal-note isolation, switching accounts, read-only
auditor UX and the filtered audit page, while preserving all M2/M3 flows. Browser
artifacts are screenshots of synthetic data, not credential-bearing network traces.

See PROJECT_PROGRESS.md and PR #12 for exact tested commit/run IDs. No test result
here certifies production security, scale, regulatory compliance or real-model
quality. M4 leaves fulfillment, attachments, notifications, retention and evaluated
AI/RAG to later milestones. Next: Phase 7 / M5, authorized service fulfillment.
