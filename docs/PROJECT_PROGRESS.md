# CentralOps AI — Project Progress Tracker

> Living status document for **Central Service AI Automation – Employee Request & Approval System**.
>
> Update rule: this file should be updated whenever a verified feature, fix, migration, test gate, PR merge, or architecture milestone is completed.

**Last updated:** 2026-09-04 — Organization seed/resolver verification update  
**Repository:** `chanhuynguyen-ai/central-service-ai-automation`  
**Current development branch:** `feat/organization-rbac`  
**Current verified remote branch HEAD:** `35fd0f7 feat(db): add organization and RBAC foundation`
**Current verified local work after that commit:** organization seed + manager hierarchy + direct-manager resolver + organization tests (23 tests PASS locally; commit/push not yet confirmed)

---

## 1. Executive status

CentralOps AI has moved beyond the original prototype stage and now has a working local/containerized baseline with a FastAPI backend, PostgreSQL, Redis, MinIO, a frontend that builds and serves successfully, Alembic migrations, authentication hardening, basic request approval logic, AI triage validation, data-quality tooling, and automated backend tests.

The project is currently in the **Organization + RBAC foundation** workstream. The normalized organization schema is committed on `feat/organization-rbac`; realistic organization seed data, manager hierarchy, and the direct-manager resolver are now implemented and locally verified, but their commit/push is not yet confirmed. Centralized permission policies, refresh/logout sessions, versioned request catalog, deterministic workflow runtime, fulfillment work items, notifications, attachments, and production-grade RAG are still incomplete.

A key Git status issue remains: feature/fix work exists on branches, while the remote `main` branch has not yet been updated with those branches. Merge the foundation and Docker build branches before treating `main` as the current baseline.

---

## 2. Status legend

| Status | Meaning |
|---|---|
| ✅ Done | Implemented and verified with available evidence |
| 🟡 Partial | Useful implementation exists but roadmap acceptance criteria are not complete |
| 🔵 In progress | Current active workstream |
| ⬜ Missing | Not implemented yet |
| ⚠️ Needs merge | Implemented on a branch but not yet integrated into `main` |

---

## 3. Verified achievements

### Repository and development workflow

- ✅ Git repository initialized and connected to GitHub.
- ✅ Professional feature/fix branch workflow adopted.
- ✅ Conventional Commit naming is being used.
- ✅ Project documentation set added under `docs/project/`.
- ✅ DKSH alignment and implementation-status documentation added.
- ⚠️ `chore/foundation-hardening` is still separate from remote `main`.
- ⚠️ `fix/docker-web-build-alpine` is still separate from remote `main`.
- 🔵 `feat/organization-rbac` is the active feature branch.

### Runtime and infrastructure

- ✅ Docker Compose baseline runs locally.
- ✅ PostgreSQL container works and reports healthy.
- ✅ Redis container works and reports healthy.
- ✅ MinIO container starts successfully.
- ✅ FastAPI container starts successfully.
- ✅ Frontend container starts successfully.
- ✅ Frontend returns HTTP 200 on port 3000.
- 🟡 API `/health` returned a transient connection-closed error immediately after API rebuild while the container still showed `health: starting`; rerun after startup before marking PASS.
- ✅ API `/ready` returned `ready` with database connectivity after the rebuild.

### Backend foundation

- ✅ FastAPI application foundation exists.
- ✅ SQLAlchemy ORM foundation exists.
- ✅ Alembic baseline migration exists.
- ✅ API startup applies Alembic migration.
- ✅ Structured logging added.
- ✅ Correlation/request ID middleware added.
- ✅ PostgreSQL runtime path verified locally.
- ✅ SQLite test path remains available for fast backend tests.

### Authentication and security hardening

- ✅ Password hashing uses Argon2 through `pwdlib`.
- ✅ JWT access-token login exists.
- ✅ `/auth/me` exists.
- ✅ Deactivated users are rejected at login.
- ✅ Employee request visibility is scoped to owned requests in current API logic.
- ✅ Self-approval is blocked.
- ✅ Power Platform approval endpoint also blocks self-approval.
- 🟡 Current authorization still partly depends on legacy single-string `user.role`.
- ⬜ Refresh-token rotation/session table not implemented yet.
- ⬜ Logout/revocation flow not implemented yet.

### Testing and code quality

- ✅ Backend test environment standardized with `uv` + Python 3.12.
- ✅ Backend test suite now reaches **23 passing tests** after Organization seed/resolver work.
- ✅ Backend coverage now reaches **89%**.
- ✅ `app/db/seed.py` reached **100%** coverage in the latest reported run.
- ✅ `app/services/organization.py` is covered at **80%** in the latest reported run.
- ✅ Ruff import/style violations were fixed and later reported as passing.
- 🟡 No GitHub Actions PR run was found for the latest Organization/RBAC commit; current verification is primarily local/user-reported.

### Frontend and Docker build

- ✅ Alpine frontend build now installs required `bash` and GNU `coreutils`.
- ✅ Vite/Vinext production build succeeds locally.
- ✅ Auth/login page is served by the production frontend container.
- ✅ Authored Vite plugin moved outside ignored generated `build/` output.
- 🟡 Current frontend dependency audit still reports npm vulnerabilities and requires a dedicated dependency-audit branch.

### AI and data quality

- ✅ AI triage exists for category, priority, summary, confidence, and model/provider metadata.
- ✅ Structured triage output is validated with Pydantic.
- ✅ Deterministic fallback path exists.
- ✅ Policy assistant returns grounded citations in current prototype path.
- ✅ Data-quality cleaner/report pipeline exists for service-request sample data.
- 🟡 Current retrieval is not yet production pgvector/hybrid RAG.
- ⬜ AI intake extraction/missing-field evaluation workflow is not complete.

### Organization + RBAC

- ✅ `departments` model/table foundation added.
- ✅ `roles` model/table foundation added.
- ✅ `user_roles` many-to-many foundation added.
- ✅ `service_teams` foundation added.
- ✅ `service_team_members` foundation added.
- ✅ `users.department_id` added while preserving legacy `department` compatibility.
- ✅ `users.manager_id` added while preserving existing API compatibility.
- ✅ Alembic migration `7d9b2f3a4c11` added with legacy department/role backfill logic.
- ✅ Realistic organization seed data implemented locally and verified by tests.
- ✅ Direct manager relationships implemented locally and verified by tests.
- ✅ Direct manager resolver implemented locally and verified by tests.
- 🟡 These Organization #07.2 changes are not yet confirmed committed/pushed to GitHub.
- ⬜ Centralized domain permission helpers are not complete yet.

---

## 4. Roadmap status

| Phase | Scope | Status | Current assessment |
|---|---|---:|---|
| 0 | Repository + Docker infrastructure | 🟡 Partial / ⚠️ merge | Runtime works; branch integration into `main` still pending |
| 1 | FastAPI + DB + Alembic + identity seed | 🟡 Partial | Core foundation works; normalized identity seed + organization hierarchy now verify locally; branch integration still pending |
| 2 | Authentication + sessions + RBAC | 🔵 In progress | Login/security works; normalized RBAC schema + org hierarchy/resolver verify locally; centralized permissions and refresh/logout remain |
| 3 | Frontend shell + real login + role-aware nav | 🟡 Partial | Frontend and login exist; complete role-aware UX not fully verified |
| 4 | Request catalog + versioned dynamic forms + drafts | ⬜ Missing | Next major product phase after RBAC/auth foundation |
| 5 | Deterministic workflow + approval tasks | 🟡 Partial | Prototype approve/reject exists, but no true workflow definition/runtime/task model |
| 6 | Timeline + comments + internal notes + audit | 🟡 Partial | Audit events exist; full timeline/comments/internal-note model missing |
| 7 | Fulfillment queue/work items | 🟡 Partial | Generic status updates exist; service work-item queue missing |
| 8 | Attachments + MinIO authorization | ⬜ Missing | MinIO infra exists but application attachment flow is missing |
| 9 | Redis worker + notifications | ⬜ Missing | Redis infra exists; worker/notifications/retry flow missing |
| 10 | AI intake classifier/extractor + evaluation | 🟡 Partial | Triage prototype exists; structured intake/evaluation incomplete |
| 11 | pgvector policy RAG | 🟡 Partial | Prototype retrieval/citations exist; pgvector and permission filtering missing |
| 12 | Admin configuration/version publishing | ⬜ Missing | Not implemented |
| 13 | SLA + escalation | 🟡 Partial | Basic due/SLA concepts exist; full SLA engine/escalation missing |
| 14 | Analytics | 🟡 Partial | Basic management metrics exist; broader product analytics incomplete |
| 15 | Security/testing/failure hardening | 🟡 Partial | Good early test/security baseline; concurrency/session/failure gates incomplete |
| 16 | Deployment + observability | 🟡 Partial | Docker/logging exist; production deployment/OTel/monitoring incomplete |

---

## 5. Current architecture deviations / deliberate compatibility decisions

1. **Integer IDs remain in the live schema.** The long-term design document recommends UUIDs, but the current prototype uses integer IDs throughout users, requests, approvals, and audit data. The Organization/RBAC slice intentionally keeps integer IDs to avoid a large unrelated breaking migration.
2. **Legacy `users.department` and `users.role` remain temporarily.** Normalized `department_id` and `user_roles` are being introduced using an expand/backfill/migrate/contract strategy so current API/frontend behavior does not break.
3. **Approval and fulfillment are not yet separated internally.** The current request model still uses a prototype aggregate `status`. This must be corrected when the proper request/workflow model is built.
4. **Prototype AI exists before the full workflow core is complete.** New AI work should remain secondary until Request → Approval → Fulfillment → Audit is reliable.

---

## 6. Active workstream — `feat/organization-rbac`

### Completed in this branch

- ✅ Added normalized organization/RBAC SQLAlchemy models.
- ✅ Added Alembic migration for organization/RBAC tables.
- ✅ Added legacy department and role backfill logic.
- ✅ Kept legacy fields for API compatibility.
- ✅ Current branch HEAD: `35fd0f7 feat(db): add organization and RBAC foundation`.

### Organization seed + manager hierarchy + resolver — current state

Verified locally from user-provided output:

- ✅ Organization-aware seed implementation is exercised by the test suite.
- ✅ Direct-manager resolver is exercised by the test suite.
- ✅ Backend tests: **23 passed**.
- ✅ Coverage: **89%**.
- ✅ Docker API image rebuilt successfully.
- ✅ `/ready`: PASS with database `ok`.
- 🟡 `/health`: rerun required because the first request landed while the API container still reported `health: starting`.
- 🟡 Ruff for this exact final local state has not yet been re-reported in the latest output.
- 🟡 PostgreSQL manual queries for manager/roles/service-team relationships have not yet been reported.
- 🟡 Commit/push for seed/resolver/tests is not yet confirmed.

### Next vertical slice

**Centralized RBAC permission policies**

Planned behavior:

- Add normalized-role helpers that read `user_roles` rather than trusting only legacy `user.role`.
- Add explicit request permission functions such as `can_view_request` and `can_decide_approval`.
- Keep server-side authorization as the source of truth.
- Preserve legacy API response compatibility while routing new authorization through centralized helpers.
- Add role/permission tests, including Auditor read-only behavior and self-approval protection.

### Acceptance checks before starting permission refactor

- [x] Backend tests pass — 23 passed.
- [x] Coverage is at least baseline level — 89%.
- [x] Docker API rebuild succeeds.
- [x] `/ready` passes.
- [ ] `/health` passes after container startup settles.
- [ ] Ruff passes on final local state.
- [ ] Manual PostgreSQL organization queries verify manager/role/team rows.
- [ ] Organization #07.2 changes are committed and pushed.

---

## 7. Next branches after Organization/RBAC

1. `feat/auth-refresh-sessions` — refresh rotation, logout, session revocation.
2. `feat/request-catalog` — stable request-type identity + versioning.
3. `feat/dynamic-request-forms` — form schema renderer + drafts.
4. `feat/workflow-engine` — deterministic workflow definitions/instances/resolvers/tasks.
5. `feat/approval-inbox` — true assigned approval tasks and actions.
6. `feat/audit-timeline` — user-facing request events + privileged audit log.
7. `feat/service-fulfillment` — queue, assignment, work-item lifecycle.
8. `feat/attachments-minio` — authorized upload/download flow.
9. `feat/notifications-worker` — Redis-backed worker, retry, notifications.
10. `feat/ai-intake-evaluation` — extraction, clarification, missing-field logic, eval set.
11. `feat/policy-rag` — pgvector, permission-aware retrieval, citations.

---

## 8. Known technical debt / follow-up work

- Merge the completed foundation and Docker build branches into `main` before calling the repository baseline current.
- Add branch protection / required CI checks to `main` later.
- Run frontend dependency audit on a dedicated branch; do not use `npm audit fix --force` without review.
- Add `.gitattributes`/line-ending policy in a dedicated repository hygiene branch if needed.
- Add refresh-token sessions and logout before declaring M1 fully complete.
- Replace prototype single `status` request lifecycle with separate approval and fulfillment state when implementing the proper request/workflow model.
- Move from lexical/prototype retrieval to pgvector/hybrid permission-aware RAG only after core workflow is stable.

---

## 9. Progress log

| Date | Branch | Change | Verification | Result |
|---|---|---|---|---|
| 2026-09-04 | `chore/foundation-hardening` | Alembic/runtime/logging/security/AI validation/data quality/docs foundation | Local Docker + backend tests reported | ✅ |
| 2026-09-04 | `fix/docker-web-build-alpine` | Added Bash/Coreutils and moved Vite plugin source outside ignored generated build directory | Frontend production Docker build + HTTP 200 reported | ✅ |
| 2026-09-04 | `feat/organization-rbac` | Added organization/RBAC models and migration with legacy backfill | Commit `35fd0f7` verified on GitHub | ✅ |
| 2026-09-04 | `feat/organization-rbac` | Added realistic organization seed, manager hierarchy, direct-manager resolver, and organization tests | 23 tests PASS, 89% coverage, Docker API rebuild PASS, `/ready` PASS; `/health` rerun + Ruff + commit/push still pending | 🔵 |

---

## 10. Update template

Use this block whenever a new change is completed:

```markdown
### YYYY-MM-DD — <branch>

**Goal:**  
<what this change was intended to achieve>

**Completed:**
- ...

**Files changed:**
- ...

**Database migration:**
- Yes/No
- Revision: ...

**Verification:**
- pytest: PASS / FAIL / NOT VERIFIED
- ruff: PASS / FAIL / NOT VERIFIED
- frontend build: PASS / FAIL / NOT VERIFIED
- Docker health: PASS / FAIL / NOT VERIFIED

**Commit(s):**
- `<sha> <message>`

**Remaining:**
- ...

**Next branch / next slice:**
- ...
```

---

## 11. Definition of project success

The project should ultimately demonstrate a reliable enterprise workflow product first:

`Employee Request → Deterministic Approval → Service Fulfillment → Audit/Timeline`

Then AI should accelerate the flow through classification, extraction, clarification, policy retrieval, and summaries without becoming the authority for access control, approval routing, policy enforcement, or final approval decisions.
