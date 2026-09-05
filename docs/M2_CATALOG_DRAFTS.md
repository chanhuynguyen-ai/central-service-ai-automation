# M2 - Catalog, dynamic forms and private drafts

## Scope and user flow

Sign in -> **Service catalog** -> **Start draft** -> complete some/all fields ->
**Save draft** -> **My drafts** -> **Continue editing**.

Drafts are real `service_requests` records with `status = draft`; no second
parallel request store is introduced. Each draft pins `request_type_version_id`.
Publishing a new catalog version does not rewrite existing draft data or form
configuration. Old versions remain readable by the draft owner.

Saving an incomplete draft is allowed. Invalid supplied values are not. The save
response includes deterministic `validation.errors` and `missing_fields`; these
are also available through the validate endpoint. This same validation contract
is intended for the later AI intake assistant. No model is called for validation.

**This slice does not submit a catalog draft for approval.** Submission and the
real approval-task inbox belong to Phase 5. The earlier simple New request dialog
remains available as a legacy prototype; it is not the new versioned workflow.

## API contract

All paths have the `/api/v1` prefix and require a valid access token.

| Method/path | Contract |
|---|---|
| GET `/catalog/request-types` | Active published catalog only |
| POST `/requests/drafts` | `request_type_version_id`, optional title/description/form_data; returns 201 |
| GET `/requests/drafts` | Owner-only list, limit/offset pagination |
| GET `/requests/drafts/{id}` | Owner-only draft plus pinned schema and validation |
| PUT `/requests/drafts/{id}` | Full replacement of title/description/form_data plus expected revision |
| POST `/requests/drafts/{id}/validate` | Completeness check of saved data; no state transition |
| GET `/requests/drafts/lookups` | Active user/department IDs and names, at most 500 each |

A PUT must send the previously returned `revision`. A stale editor receives 409
and must reload, rather than silently overwriting another editor. The UI keeps
unsaved input visible after a conflict and offers an explicit reload action.
Other users, including administrators, receive 404 when opening/editing a draft
that they do not own. Requester, status and pinned version cannot be overposted.

## Data and privacy

- `form_data` is stored as JSON; `draft_revision` supports atomic SQL compare-and-swap.
- Draft `submitted_at` and `due_at` are null. No SLA clock, approval, AI call or
  notification is started by a save.
- Drafts are excluded from legacy request list/detail/status/decision APIs,
  operational analytics, Power Platform feeds and policy-assistant request context.
- Draft-created/updated audit records contain only version/revision identifiers,
  never the supplied field values.
- Published and retired form versions are immutable through the API.
- One published version per request type is also protected by a partial unique
  index. PostgreSQL publication/version writes lock the parent request type.

## Field support and intentional limits

The renderer and backend support text, textarea, finite number, decimal-string
currency, date, date range, boolean, select, multi-select, active user/department
pickers and HTTP(S) URLs. Zero and false are valid supplied values.

Amounts are decimal **strings**, not JSON floating-point numbers. The generic
currency input supports up to 12 integral digits and 2 decimal places; request-
specific monetary policies and calculations are not implemented in this slice.

Attachment controls are visibly unavailable until authorized storage is added in
Phase 8. Arbitrary attachment IDs/URLs are rejected, not trusted. A nonempty
advanced `validation_schema` fails completeness validation explicitly; only the
documented typed form contract is implemented. Do not configure unsupported
validation rules and assume they are being enforced.

## Start the demo on Windows

Run from the repository root with a clean working tree. After this PR is merged:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
docker compose up -d --build --wait
docker compose exec api alembic current
docker compose exec api python -m app.db.seed_catalog
Start-Process "http://localhost:3000"
```

The explicit catalog seed creates three example published services: laptop
replacement, software access, expense reimbursement. It skips existing service
codes and never overwrites their versions. It requires the existing demo identity
seed (the application's demo startup already provides it).

Use `employee@centralops.demo` / `Employee123!` only on the local demo stack.
Open Service catalog, start a laptop draft, save it incomplete, finish its fields,
then reopen it under My drafts. Sign out and use a different demo employee to
verify that the draft is private.

**Do not delete database volumes.** Docker commands above migrate the actual
PostgreSQL container. A local `uv run alembic upgrade head` may instead target a
separate SQLite database, depending on local configuration.

## Migration and rollback

New revision: `d5f9b2e4a601`, parent `c4e8a1d2f730`.
It adds version/form/revision columns, makes submission/SLA timestamps nullable,
widens the category field to match catalog categories, and adds the publication
uniqueness index. Existing submitted requests are left intact.

Downgrade intentionally refuses when structured records or incompatible data
exist. Export/migrate them first; never erase employee drafts merely to make an
old branch start. Back up persistent development data before schema operations.

## Verification

- Validator unit tests cover types, required/partial semantics, false/zero,
  decimal precision, dates, ranges, unknown keys and unsupported fields.
- API tests cover ownership, overposting, stale revision conflicts, schema
  pinning, legacy-surface privacy, empty catalog and idempotent seeding.
- Frontend tests execute the actual renderer and input conversion handlers.
- CI now executes frontend tests after building, not just typecheck/lint/build.
- Browser smoke runs Chromium against production Docker images and PostgreSQL,
  saves/reopens a real draft, reloads the session, changes accounts and checks
  ownership. It retains screenshots only, not token-bearing network traces.
- PostgreSQL concurrency smoke uses two independent connections and asserts one
  successful save, one conflict and one committed update audit event.

The browser/concurrency scripts are **CI/demo-only** and require an explicit
`CENTRALOPS_E2E=1` opt-in. They write demo records; do not run them on production.
