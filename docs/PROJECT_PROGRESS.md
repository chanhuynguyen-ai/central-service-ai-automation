# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-07  
**Current delivery:** PR #18 - permission-aware pgvector policy RAG (M8)  
**Implementation branch:** `feat/policy-rag`

This is the canonical living tracker. Product/architecture requirements remain in
`docs/project/`; historical delivery snapshots remain in `docs/history/`. Passing CI
is evidence for the tested behavior, not a production-security, performance or
regulatory certification.

## Milestones

| Milestone | Verified state |
|---|---|
| M1 secure API foundation | Merged; auth/session/RBAC prototype and server-side permissions |
| Phase 3 role-aware frontend | Merged in PR #8 |
| M2 structured catalog/drafts | Merged in PR #9/#10 |
| M3 sequential approvals | Merged in PR #11 |
| M4 timeline/comments/audit | Merged in PR #12 |
| M5 service fulfillment | Merged in PR #13 |
| Phase 8 authorized attachments | Merged in PR #14 |
| M6 async communication | Merged in PR #15 |
| M7 AI intake | Merged in PR #16 |
| **M8 policy RAG** | **Implemented in PR #18; final exact-head verification pending** |

## Delivered in M8

- PostgreSQL `pgvector` extension and vector-backed policy chunks.
- Versioned policy documents with publication status, effective dates, checksums and source metadata.
- Access scopes `ALL`, `DEPARTMENT` and `ROLE`.
- Permission/effective-date filtering occurs before vector retrieval and before any chunk is supplied to an LLM.
- Deterministic hash embeddings for repeatable local/CI behavior.
- Ollama and OpenAI-compatible embedding adapters with deterministic fallback.
- Grounded policy answer endpoint with structured citations and explicit insufficient-evidence behavior.
- ADMIN-only policy ingestion and ADMIN/AUDITOR policy listing.
- Policy indexing audit event.
- Demo policy seed covering public, Finance-only and Auditor-only material.
- SQLite-compatible migration path plus a real PostgreSQL pgvector verification probe.
- Dedicated `/knowledge` UI showing grounded answers, evidence cards, retrieval score, section/source metadata and insufficient-evidence warnings.
- Browser smoke path seeds policy content and verifies the employee knowledge UI against the permission-aware RAG endpoint.

## Runtime/API surface

New endpoints:

- `POST /api/v1/ai/knowledge/documents` — ADMIN
- `GET /api/v1/ai/knowledge/documents` — ADMIN/AUDITOR
- `POST /api/v1/ai/knowledge/ask` — authenticated users

Migration:

- `j1f5e8a0b267` — permission-aware policy RAG storage; down revision `i0e4g7d9f156`.

Primary files:

- `backend/app/models/knowledge.py`
- `backend/app/schemas/knowledge.py`
- `backend/app/services/knowledge.py`
- `backend/app/api/routes/knowledge.py`
- `backend/app/db/seed_policies.py`
- `backend/app/db/verify_policy_rag.py`
- `backend/tests/test_policy_rag.py`
- `backend/alembic/versions/j1f5e8a0b267_add_policy_rag.py`
- `app/knowledge/page.tsx`
- `lib/api.ts`
- `scripts/m8_policy_rag_browser_smoke.py`

## Verification status

PR #18 initially exposed real implementation/test defects and they were corrected rather than bypassed:

- Ruff import/`zip(strict=...)` violations in the new RAG code.
- Two test login aliases that did not match the existing seeded fixture names.
- The first knowledge-page implementation triggered the strict React `set-state-in-effect` lint rule.

The latest branch must still pass exact-head verification before merge:

- Ruff + clean SQLite migration + full backend pytest/coverage.
- Frontend typecheck + ESLint + production build + frontend tests.
- Clean PostgreSQL migration plus existing concurrency/integrity probes.
- pgvector extension/storage/distance verification.
- Production Docker/Chromium regression through M2-M8.

Do not mark M8 verified or merge solely because an earlier checkpoint passed.

## RAG governance boundaries

Policy RAG is evidence support, not policy authority. AI still cannot:

- authorize users or broaden document access,
- bypass publication/effective-date filters,
- choose approval authority,
- change deterministic workflow routing,
- publish policies autonomously,
- make approval or fulfillment decisions.

When accessible evidence does not meet the grounding threshold, the assistant must return an explicit insufficient-evidence response rather than fabricate a policy answer.

## Existing hardening backlog

Secure-cookie refresh transport, immediate access-token revocation/rate limiting,
dependency remediation, TLS/backups, retention/redaction, malware scanning, production
embedding/model quality evaluation and broader security/load testing remain later work.

## Next

After PR #18 is final-green and merged, implement **Phase 12 / Admin configuration**:
request-type version editor, ordered workflow-step editor, role/service-team administration
and policy publish/retire management while preserving immutable published history.
