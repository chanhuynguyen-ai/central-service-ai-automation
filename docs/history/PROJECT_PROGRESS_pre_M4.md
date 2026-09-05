# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-05  
**Current delivery:** PR #11 - sequential workflow and assigned approvals (M3)  
**Implementation branch:** `feat/sequential-workflow-approvals`

This is the canonical living tracker. Original project specifications are in
`docs/project/`; prior status snapshots are preserved in `docs/history/`.
A feature is not production-ready merely because tests are green. PR #11 records
its exact final merge state and current-head CI evidence.

## Milestones

| Milestone | State / evidence |
|---|---|
| M1 secure API foundation | Prototype foundation implemented; auth/roles/session PRs merged |
| Phase 3 authenticated frontend | Merged in PR #8 |
| M2 structured private drafts | PR #9 catalog and PR #10 form/draft workspace merged; real browser/PostgreSQL gates passed |
| M3 deterministic assigned approvals | Implemented and verified in PR #11; evidence below |
| M4 full timeline/comments/audit UI | Next vertical slice; current attempts/decision history is not the full phase |
| M5 fulfillment | Not implemented; approved requests explicitly remain not_queued |
| M6 async communication | Worker/notification delivery not implemented |
| M7/M8 AI intake and policy RAG | Later phases; legacy AI prototype is not equivalent to these milestones |

## Delivered in M3

- Seven definition/version/step/attempt/task/decision tables. One default workflow
  per catalog type, one published version, ordered ALL steps only.
- Four deterministic resolvers: explicit user, requester manager, normalized role
  in requester department, and service-team lead. No LLM routing authority.
- Atomic saved-draft submission: ownership, revision, form validation, active
  published workflow, all approvers, immutable submitted snapshot, first tasks
  and audit records commit together. Invalid routing leaves the draft intact.
- Exact-assignee decisions and pending/history inbox. Unassigned administrators
  cannot decide; wrong/self/deactivated actors and stale decisions are rejected.
- Rejection is terminal. Request changes requires a reason; private edits are
  owner-only, and resubmission starts a new attempt with the whole chain restarted.
  Earlier submitted values, configurations and decisions remain available.
- Request-row locking plus task/request compare-and-swap and unique constraints
  protect duplicate actions and concurrent different tasks in an ALL step.
- Final approval is separate from fulfillment. No fake work item or notification.
- Legacy API/status/integration/AI-context surfaces cannot bypass the structured
  workflow. Legacy metrics are labeled separately rather than presented as M3 KPIs.
- Real frontend submit confirmation, saved-complete guard, assigned decision form,
  authorized submission detail and visible attempt history.
- Explicit idempotent demo workflow seed: Manager -> Central Service Lead. These
  are synthetic routing rules, not claimed employer policies.

## Database

Latest revision: `e6a0c3f5b712` after M2's `d5f9b2e4a601`.
Existing prototype requests and saved drafts are preserved. Downgrade refuses
when workflow definitions exist. Back up persistent development data before
schema changes; never delete volumes just to make an old branch run.

## Verification

The backend suite on the M3 code has **107 passing tests and 85% total coverage**
(CI run 30, `33947511678`). This replaces the older 36-test/90% baseline; it is a
larger suite and denominator, not a claim that all new paths are covered.
Local execution also passed 107 tests. PostgreSQL workflow run 3 (`33947511680`)
passed clean migrations and independent-connection concurrency probes.

The browser gate initially exposed an inaccessible exact label on the approval
selector. Commit `10f7011` separates the labels from their controls rather than
weakening the browser test. On that head all three workflows are **SUCCESS**:

| Gate | Verified run |
|---|---|
| CI / backend + frontend | #31, `33947838899` |
| Clean PostgreSQL migration + workflow concurrency | #4, `33947838796` |
| Production Docker + real Chromium M2/M3 flow | #7, `33947838771` |

The Chromium script covers employee submit, generic approver empty inbox, manager
request-changes, private revision/resubmit, manager approval, service-lead final
approval and both preserved snapshots. The first browser failure was corrected,
not ignored. Artifacts are synthetic screenshots, not token-bearing traces.
PR #11 records the final current-head checks and merge commit separately.

PostgreSQL probes cover duplicate submit, duplicate intermediate/final decision,
and two different same-step ALL task IDs deciding simultaneously. The normal
pytest client uses SQLite; these separate probes verify actual PostgreSQL locks.
Neither is a production load benchmark.

## Files and review guide

- Models, schemas, service and router: `backend/app/{models,schemas,services,api/routes}/workflows.py`.
- Migration: `backend/alembic/versions/e6a0c3f5b712_add_sequential_workflow.py`.
- Seeds/probes: `backend/app/db/seed_workflows.py`, `verify_workflow_concurrency.py`.
- Tests: `backend/tests/test_workflows.py`, `tests/workflow-api.test.mjs`, `scripts/m3_browser_smoke.py`.
- UI/client: `components/workflows/workflow-workspace.tsx`, `lib/workflow-api.ts`; catalog/workspace integration updated.
- Legacy privacy/bypass guards: requests, analytics, integrations, assistant routes.
- CI: workflow-postgres and browser-smoke workflows; existing CI retained.

## Deliberate limits / risks

No ANY/conditional approval, delegation, automatic reassignment, exception queue,
background delivery, full fulfillment or file uploads. An unavailable resolved
reviewer fails safely for administrator attention. Public admin configuration UI
and richer SLA behavior are still pending.

Authentication remains a prototype: refresh tokens travel in JSON/sessionStorage;
logout revokes refresh sessions, not already-issued access JWTs. Rate limits,
secure cookies, broader session hardening and dependency audit remediation remain.
The existing dependency-install audit reported vulnerabilities; no blanket
production-safety claim or force-upgrade was made during this workflow change.
CI uses the mock LLM provider. No real-model accuracy, latency or pgvector RAG
quality is claimed.

## Next

After verified PR #11 merge, continue **Phase 6 / M4: request events timeline,
requester comments, protected internal notes and audited access**, on a new branch.
Then add Phase 7 service fulfillment. Do not route business decisions through AI.

## Run

Read [M3 workflow demo and API guide](M3_WORKFLOW_APPROVALS.md) and
[M2 catalog/draft guide](M2_CATALOG_DRAFTS.md). Pull the merged main, build Compose,
check Alembic in the API container, run catalog/workflow seeds, and demo using
employee, direct manager and service-lead accounts. No manual code patches needed.
