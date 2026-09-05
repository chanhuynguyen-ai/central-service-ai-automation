# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-05  
**Current branch:** `feat/catalog-draft-workspace`  
**Current PR:** #10 - catalog-driven forms and private versioned drafts (M2)

This file is the canonical living tracker. The earlier long-form status and its
historical evidence are preserved in [the 2026-09-04 snapshot](history/PROJECT_PROGRESS_2026-09-04.md).
Only verified outcomes are marked passed. A pushed feature is not automatically
merged, and a green compiler is not a browser test.

## Verified baseline

- PR #8 role-aware frontend merged as `0b4bac0`.
- PR #9 catalog foundation passed CI run 21 and merged as `6838184`.
- M1 prototype API/auth foundation and Phase 3 authenticated shell are implemented.
- Catalog identity/version lifecycle is merged; M2 completion is in PR #10.

## M2 implementation in PR #10

- Catalog-driven editor and My drafts workspace, with live API data only.
- Structured drafts extend the existing `service_requests` aggregate.
- Drafts pin their form version; retired versions remain available to their owner.
- Missing fields may be saved; invalid supplied data cannot. Completion validation
  and missing-field detection are deterministic, not model-generated.
- Currency is a decimal string; false and zero remain valid supplied values.
- Owner-only read/write, extra-field rejection and atomic revision compare-and-swap.
- Drafts do not start an SLA, invoke AI, send notifications or create approvals.
- Private drafts are excluded from legacy APIs, integration feeds, analytics and AI context.
- Catalog publication locking and one-published-version index protect configuration.
- Explicit idempotent demo catalog seed adds laptop, software and reimbursement examples.
- Migration `d5f9b2e4a601` follows `c4e8a1d2f730`; downgrade refuses data loss.
- Renderer behavior tests and real Chromium/PostgreSQL smoke added to CI.

## Verification checkpoint

- 31 pure form-validator tests passed in the execution environment.
- CI run 24: backend Ruff, clean SQLite migration and full backend suite passed.
- CI run 25 / head `5268c343`: backend passed and frontend typecheck passed.
- Browser/PostgreSQL run `33942389146`: production Docker stack, migrations,
  real Chromium save/reopen/reload/logout and cross-account draft isolation passed.
- Screenshots from that run were downloaded and visually inspected.
- Frontend lint found a ref naming rule and a test-module variable rule. This
  follow-up fixes both; final renderer/test suite and current-head CI remain to verify.
- Real PostgreSQL concurrent-save smoke has been added and is not yet verified.
- PR #10 remains draft until all current-head gates pass. It has not been merged.

## Known boundaries

- Catalog draft submission, deterministic approval tasks and real inbox actions
  are Phase 5, not implemented by M2. The old New request dialog is a prototype.
- Attachment upload remains explicitly disabled until Phase 8.
- Nonempty advanced validation_schema rules fail completeness checks explicitly.
- UI field pickers expose authenticated active IDs/names only (maximum 500).
- This is not a production-security certification: refresh tokens are still JSON/
  sessionStorage, logout revokes refresh sessions rather than existing JWTs, and
  broader authentication hardening remains on the roadmap.
- LLM provider is `mock` in CI/demo. No real-provider or RAG evaluation is claimed.

## Next build target

Finish current-head PR #10 gates and merge M2, then a dedicated Phase 5 branch:
versioned sequential workflow definitions, deterministic approver resolution,
atomic draft submission and assigned approval decisions. Do not route approvals
through an LLM.

## Run and review

See [M2 catalog and draft guide](M2_CATALOG_DRAFTS.md) for startup, seed, API,
validation and acceptance details. Preserve development volumes when updating.
