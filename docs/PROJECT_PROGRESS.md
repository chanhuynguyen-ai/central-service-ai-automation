# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-06  
**Current delivery:** PR #16 - catalog-grounded AI-assisted request intake (M7)  
**Implementation branch:** `feat/ai-intake`

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
| **M7 AI intake** | **Implemented in PR #16; final verification pending on current HEAD** |
| M8 policy RAG | Next only after M7 is final-green and merged |

## Delivered in M7

- Free-text intake classification constrained to active, published request types.
- Confidence plus alternative request-type suggestions for human review.
- Schema-bound extraction that only accepts fields from the selected published form.
- Pydantic validation of external model output with deterministic fallback behavior.
- Extracted values are revalidated by the same deterministic form validator used by
  normal drafts; invalid or unsupported values never bypass the request schema.
- Missing required fields are computed from the published form schema, not by an LLM.
- Clarification prompts are generated deterministically from those missing fields.
- Every AI suggestion is advisory: even high-confidence classification requires human
  confirmation, remains editable and is not saved or submitted automatically.
- Human selection of an alternative request type is authoritative for extraction; the
  model cannot silently switch the selected request type.
- Existing Ollama/OpenAI-compatible adapters remain available while CI and the local
  demo use a deterministic `mock` fallback.
- A 30-case evaluation corpus covers laptop replacement, software access and expense
  reimbursement. CI tracks top-1, top-2, expected-field extraction and missing-field
  correctness thresholds.
- Chromium smoke coverage exercises AI suggestion -> explicit review -> normal editable
  draft -> explicit save without autonomous submission.

## Runtime/API surface

New endpoints:

- `POST /api/v1/ai/intake/classify`
- `POST /api/v1/ai/intake/draft`

M7 adds no database migration. It reuses immutable published request-type versions and
existing automation-run telemetry.

Primary files:

- `backend/app/schemas/ai_intake.py`
- `backend/app/services/ai_intake.py`
- `backend/app/api/routes/ai_intake.py`
- `backend/tests/test_ai_intake.py`
- `backend/tests/test_ai_intake_eval.py`
- `backend/evals/ai_intake_cases.json`
- `lib/ai-intake-api.ts`
- `components/catalog/ai-intake-card.tsx`
- `components/catalog/catalog-workspace.tsx`
- `scripts/m7_browser_smoke.py`

## Verification status

Earlier PR #16 runs exposed two real defects: high-confidence suggestions did not
always require explicit confirmation, and the deterministic fallback did not populate
a narrative `reason` field from a clearly stated request. Both were corrected rather
than weakening the tests.

Current final verification must be green on the latest PR #16 HEAD before merge:

- Ruff + clean SQLite migration + full backend pytest/coverage.
- Frontend typecheck + ESLint + production build + frontend tests.
- Clean PostgreSQL migrations plus existing concurrency/integrity probes.
- Production Docker/Chromium regression through M2-M7.
- 30-case AI intake evaluation quality gates.

Do not mark M7 verified or merge solely because an older checkpoint passed.

## AI boundaries

AI can classify, extract, suggest and explain. It still cannot:

- authorize a user,
- choose final approval authority,
- bypass deterministic routing,
- publish a request type,
- persist a draft without an explicit user save,
- submit a request without the normal human action,
- make the final approval decision.

The deterministic form schema, authorization service and workflow engine remain the
sources of truth.

## Existing hardening backlog

Secure-cookie refresh transport, immediate access-token revocation/rate limiting,
dependency remediation, TLS/backups, retention/redaction, malware scanning and broader
security/load testing remain later hardening work.

## Next

After PR #16 is final-green and merged, implement **Phase 11 / M8 Policy RAG**:
pgvector-backed policy chunks, permission/effective-date filtering before model context,
grounded answers with citations and explicit insufficient-evidence behavior.

Do not begin RAG by bypassing access scope or treating the model as policy authority.
