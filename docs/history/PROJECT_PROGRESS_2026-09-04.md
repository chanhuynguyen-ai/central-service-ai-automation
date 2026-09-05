# CentralOps AI — Project Progress Tracker

> Living status document for **Central Service AI Automation – Employee Request & Approval System**.
>
> Update rule: this file should be updated whenever a verified feature, fix, migration, test gate, PR merge, or architecture milestone is completed.

**Last updated:** 2026-09-04 — Role-aware frontend completion and verification

**Repository:** `chanhuynguyen-ai/central-service-ai-automation`

**Current development branch:** `feat/role-aware-frontend`

**Current verified remote branch HEAD:** `cb2a208 feat(frontend): add role-aware authenticated workspace`

**Current verified local work after that commit:** honest live-data loading/error states, dynamic navigation counts, role-scoped operational metrics, UTF-8 role display fix, CI test correction, and documentation refresh

---

## 1. Executive status

CentralOps AI has moved beyond the original prototype stage and now has a working local/containerized baseline with a FastAPI backend, PostgreSQL, Redis, MinIO, a frontend that builds and serves successfully, Alembic migrations, authentication hardening, basic request approval logic, AI triage validation, data-quality tooling, and automated backend tests.

The project is currently completing **Phase 3 — authenticated, role-aware frontend shell**. Organization/RBAC, centralized request permissions, refresh-token rotation, logout/revocation, and normalized roles are merged into `main`. The current branch connects that identity contract to session restoration, automatic refresh, role-aware navigation, real request loading, and role-scoped metrics.

The next product phase is **Phase 4 — versioned request catalog and draft requests**. Deterministic workflow runtime, fulfillment work items, notifications, attachments, and production-grade RAG remain incomplete and must follow the documented build order.

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
- ✅ Foundation, Docker, Organization/RBAC, centralized permissions, and auth-session PRs are merged into `main`.
- 🔵 `feat/role-aware-frontend` is the active feature branch and is based directly on current `main`.

### Runtime and infrastructure

- ✅ Docker Compose baseline runs locally.
- ✅ PostgreSQL container works and reports healthy.
- ✅ Redis container works and reports healthy.
- ✅ MinIO container starts successfully.
- ✅ FastAPI container starts successfully.
- ✅ Frontend container starts successfully.
- ✅ Frontend returns HTTP 200 on port 3000.
- ✅ API `/health` behavior is covered by the backend test suite.
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
- ✅ Centralized permission helpers read normalized role assignments with a documented legacy compatibility fallback.
- ✅ Refresh-token rotation and hashed server-side session records are implemented.
- ✅ Logout revokes the server-side refresh session.
- 🟡 The browser currently receives refresh tokens in JSON and stores them in `sessionStorage`; production hardening should move them to HttpOnly/Secure/SameSite cookies.

### Testing and code quality

- ✅ Backend test environment standardized with `uv` + Python 3.12.
- ✅ Backend test suite reaches **36 passing tests** on the current branch.
- ✅ Backend coverage reaches **90%**.
- ✅ `app/db/seed.py` reached **100%** coverage in the latest reported run.
- ✅ `app/services/organization.py` is covered at **80%** in the latest reported run.
- ✅ Ruff import/style violations were fixed and later reported as passing.
- ✅ Frontend TypeScript, ESLint, production build, and **6 contract/product tests** pass locally.
- 🟡 GitHub Actions verification is pending until the current branch is pushed and a PR is opened.

### Frontend and Docker build

- ✅ Alpine frontend build now installs required `bash` and GNU `coreutils`.
- ✅ Vite/Vinext production build succeeds locally.
- ✅ Auth/login page is served by the production frontend container.
- ✅ Authored Vite plugin moved outside ignored generated `build/` output.
- ✅ Session restoration, refresh rotation, logout, and normalized user-role display are wired to the real API.
- ✅ Navigation and operational analytics are role-aware; server authorization remains authoritative.
- ✅ When an API-backed build cannot load live data, the UI shows an explicit retryable error instead of stale demo records.
- ✅ Interactive demo mode remains available when `NEXT_PUBLIC_API_URL` is intentionally absent.
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
- ✅ Organization and centralized permission work is committed and merged into `main`.

---

## 4. Roadmap status

| Phase | Scope | Status | Current assessment |
|---|---|---:|---|
| 0 | Repository + Docker infrastructure | ✅ Done | Repository, CI, Docker Compose, PostgreSQL, Redis, and MinIO baseline are integrated |
| 1 | FastAPI + DB + Alembic + identity seed | ✅ Done | Health/readiness, SQLAlchemy/Alembic, organization seed, and PostgreSQL runtime path exist |
| 2 | Authentication + sessions + RBAC | ✅ MVP done | Argon2, access tokens, hashed rotating refresh sessions, logout, normalized roles, manager scope, and centralized policies are implemented; production cookie transport remains hardening work |
| 3 | Frontend shell + real login + role-aware nav | 🔵 In progress | Implementation and local quality gates pass on `feat/role-aware-frontend`; PR/CI integration remains |
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

## 6. Active workstream — `feat/role-aware-frontend`

### Completed in this branch

- ✅ Added authenticated session restoration against `/auth/me`.
- ✅ Added automatic refresh rotation and logout/revocation integration.
- ✅ Exposed normalized roles in the frontend user contract.
- ✅ Added role-aware navigation and role-scoped operational views.
- ✅ Removed stale demo data from API-backed error states and added retry UX.
- ✅ Added dynamic request/approval navigation counts and connection-state feedback.
- ✅ Preserved the no-API interactive reviewer demo.
- ✅ Current remote branch HEAD before the completion commit: `cb2a208 feat(frontend): add role-aware authenticated workspace`.

### Verification state

- ✅ Backend Ruff: PASS.
- ✅ Backend tests: **36 passed**.
- ✅ Backend coverage: **90%**.
- ✅ Frontend TypeScript: PASS.
- ✅ Frontend ESLint: PASS.
- ✅ Frontend production build: PASS.
- ✅ Frontend contract/product tests: **6 passed**.
- ✅ API-configured production build and local production smoke checks pass for `/health`, `/ready`, frontend bootstrap, manager roles, refresh rotation, logout, and revoked-token rejection.
- 🟡 Docker smoke testing could not run in the current execution environment because the Docker CLI is unavailable; commit/push and GitHub Actions PR verification remain.

### Next vertical slice

**Versioned request catalog foundation (`feat/request-catalog`)**

Planned behavior:

- Add stable `request_types` identities and immutable `request_type_versions`.
- Add an Alembic migration and demo catalog seed data.
- Expose read APIs for active published request types.
- Preserve submitted request history by referencing a specific request-type version.
- Add publication/version-preservation tests before building the dynamic form renderer.

### Acceptance checks before starting request catalog

- [x] Backend Ruff passes.
- [x] Backend tests pass — 36 passed, 90% coverage.
- [x] Frontend typecheck, lint, build, and tests pass — 6 passed.
- [x] API-configured production build passes.
- [x] Local production `/health`, `/ready`, frontend bootstrap, login/roles, refresh rotation, logout, and revocation smoke checks pass.
- [ ] Docker Compose smoke test passes in a Docker-enabled environment.
- [ ] Completion commit is pushed and GitHub Actions passes in the PR.

---

## 7. Next branches after Phase 3

1. `feat/request-catalog` — stable request-type identity + immutable versioning.
2. `feat/dynamic-request-forms` — form schema renderer + owned drafts.
3. `feat/workflow-engine` — deterministic workflow definitions/instances/resolvers/tasks.
4. `feat/approval-inbox` — true assigned approval tasks and actions.
5. `feat/audit-timeline` — user-facing request events + privileged audit log.
6. `feat/service-fulfillment` — queue, assignment, work-item lifecycle.
7. `feat/attachments-minio` — authorized upload/download flow.
8. `feat/notifications-worker` — Redis-backed worker, retry, notifications.
9. `feat/ai-intake-evaluation` — extraction, clarification, missing-field logic, eval set.
10. `feat/policy-rag` — pgvector, permission-aware retrieval, citations.

---

## 8. Known technical debt / follow-up work

- Add branch protection / required CI checks to `main` later.
- Run frontend dependency audit on a dedicated branch; do not use `npm audit fix --force` without review.
- Move refresh-token transport from JSON/`sessionStorage` to HttpOnly/Secure/SameSite cookies before production deployment.
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
| 2026-09-04 | `main` | Merged centralized permissions (PR #6) and rotating auth sessions/logout (PR #7) | Main HEAD `03dbcbe`; backend regression suite passes | ✅ |
| 2026-09-04 | `feat/role-aware-frontend` | Added real session lifecycle, normalized role-aware navigation/metrics, live-data error handling, and corrected frontend CI contract | Ruff PASS; 36 backend tests at 90%; typecheck/lint/build PASS; 6 frontend tests PASS; API-configured build and local production smoke PASS | 🔵 |

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
