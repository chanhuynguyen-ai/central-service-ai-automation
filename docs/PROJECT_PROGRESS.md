# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-05
**Current delivery:** PR #12 - request activity, discussions and audit (M4)
**Implementation branch:** `feat/request-timeline-audit`

This is the canonical living tracker. Original requirements remain in
`docs/project/`; earlier status snapshots are preserved in `docs/history/`.
PR #12 records its exact final tested HEAD and merge state. Passing a feature gate
is not a production-security or regulatory-compliance certification.

## Milestones

| Milestone | Verified state |
|---|---|
| M1 secure API foundation | Auth/session/RBAC prototype merged; production transport/rate-limit hardening remains |
| Phase 3 role-aware frontend | Merged in PR #8 |
| M2 private structured drafts | PR #9/#10 merged; browser/PostgreSQL regression gates retained |
| M3 sequential assigned approvals | PR #11 merged at f9ef76f; user reports local stack checks passed |
| M4 activity/comments/audit | Implemented in PR #12; verified gates below, final merge state in PR |
| M5 fulfillment | Next; Approved still records fulfillment as not_queued |
| M6 async communication | Worker/notification delivery not implemented |
| M7/M8 AI intake and RAG | Later phases; legacy triage/lexical retrieval are not these milestones |

## Delivered in M4

- Separate append-only domain events and comment records over the existing
  service request; enriched existing audit_events rather than a duplicate audit store.
- Public discussion and restricted internal notes with server-side authorization,
  owner exclusion for internal content even for an ADMIN requester, and read-only
  auditor behavior. Mixed roles do not promote auditor read scope into write scope.
- Authorization filtering precedes keyset pagination. No internal bodies/events
  are sent to the requester. Never-submitted drafts and legacy requests stay outside
  the activity endpoints; M3 submitted snapshots remain unchanged.
- Idempotent comment keys, shared request-row locks and unique constraints.
  Comment, audit and domain event are atomic; failed writes cannot leave ghost events.
- Transactional workflow events, safe auth/catalog/workflow audit metadata and
  ORM role-assignment audit. Privileged audit reads are themselves recorded.
- Database and ORM history-mutation guards. PostgreSQL UPDATE/DELETE/TRUNCATE
  and SQLite UPDATE/DELETE protection are explicitly tested.
- Recognized prior M3 audits are imported with original times/source IDs and a
  visible backfill label. No invented history or copied private draft content.
- Request detail includes discussion, timeline, audience warnings, explicit internal
  confirmation, read-only permissions, HTML-safe plain text and cursor loading.
- ADMIN/AUDITOR Audit log workspace with filters, metadata-only rows and request
  correlation IDs. Attachments remain an honest unavailable placeholder.

## Verification checkpoints

On `7fb78671d1f5074867f183d59f8178d94b49c5cf`:

| Gate | Recorded evidence |
|---|---|
| CI backend + frontend | #36 / 33967447121 SUCCESS: 123 backend tests, 85% total coverage; TypeScript, ESLint, build and executable frontend tests |
| Chromium/Docker M2-M4 | #12 / 33967447127 SUCCESS: public persistence, escaped HTML, internal body/event isolation, account switch and auditor UI |
| PostgreSQL M4 gate | #9 / 33967447118 SUCCESS: clean migration, M3 races, idempotent comment and DB append-only probes |

Screenshots from the full M4 browser run were downloaded and visually inspected.
The final hardening adds two focused tests for mixed-role writing scope and
catalog/workflow configuration audit. These two tests passed locally. All gates
must pass again on that final HEAD; PR #12 is authoritative for the final run IDs.

Normal API fixtures use SQLite. Separate CI probes exercise real PostgreSQL row
locks, concurrent writes and database triggers. CI uses mock AI, no production
services or user database. No load-test or real-provider accuracy claim is made.

## Database and migration

Latest revision: `f7b1d4a6c823`, following M3 `e6a0c3f5b712`.
Existing requests/drafts/decisions are preserved. Back up persistent data first.
Downgrade refuses loss of events/comments/enriched audit. Do not use volume deletion
or an older application branch as a rollback plan after this migration.

## Files and review guide

- Models/schemas: `backend/app/models/activity.py`, `schemas/activity.py`, existing model exports/envelope.
- Policy/transactions: `backend/app/services/activity.py`, `services/audit.py`, M3 workflow audit adapter.
- API: `backend/app/api/routes/activity.py`, `audit.py`; auth/catalog hooks and actor context.
- Migration: `backend/alembic/versions/f7b1d4a6c823_add_request_activity.py`.
- Tests: `backend/tests/test_activity.py`, `test_activity_migration.py`, `tests/activity.test.mjs`.
- PostgreSQL probe: `backend/app/db/verify_activity.py`.
- UI/client: `components/activity/`, `lib/activity-api.ts`, workflow-detail and sidebar integration.
- Browser gate: `scripts/m4_browser_smoke.py`; existing CI pipelines extended, not replaced.

## Limits that remain explicit

Append-only triggers are not tamper-proof against a database owner. Retention,
redaction/erasure, archival, log growth and externally secured audit storage remain.
Legacy stored audit JSON is filtered at read time, not retroactively purged.
Raw SQL role changes outside the ORM are not claimed as application-audited.
Unsent comment text is not persistent; save before navigating away.

Existing prototype auth uses refresh JSON/sessionStorage; logout does not revoke
already-issued access JWTs. Rate limits, secure cookies, TLS/backups, dependency
audit remediation, full deployment/load/security review remain necessary before
shared production use. Real Microsoft-tenant integrations are not yet verified.
No fulfillment, attachments, asynchronous delivery or evaluated AI/RAG is claimed.

## Next

Phase 7 / M5: service work item created exactly once after final approval, scoped
team queue, assignment, start/wait/resolve/close and propagation into this timeline.
No approval should be silently converted to completed fulfillment.

## Run

Read [M4 activity/audit guide](M4_ACTIVITY_AUDIT.md), [M3 workflow guide](M3_WORKFLOW_APPROVALS.md)
and [M2 catalog guide](M2_CATALOG_DRAFTS.md). Pull merged main, rebuild Compose,
check Alembic in the API container, then open an existing submitted request.
No M4 seed or local patch ZIP is needed.
