# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-06  
**Current delivery:** PR #14 - authorized request attachments (Phase 8)  
**Implementation branch:** `feat/request-attachments`

This is the canonical living tracker. Product/architecture requirements remain in
`docs/project/`; historical delivery snapshots remain in `docs/history/`. Passing
CI is evidence for tested behavior, not a production-security, performance or
regulatory certification.

## Milestones

| Milestone | Verified state |
|---|---|
| M1 secure API foundation | Merged; auth/session/RBAC prototype and server-side permissions |
| Phase 3 role-aware frontend | Merged in PR #8 |
| M2 structured catalog/drafts | Merged in PR #9/#10 |
| M3 sequential approvals | Merged in PR #11 |
| M4 timeline/comments/audit | Merged in PR #12 |
| M5 service fulfillment | Merged in PR #13 at `bbc26aa` |
| **Phase 8 authorized attachments** | **Implemented in PR #14; final CI/PostgreSQL/Docker+MinIO verification required before merge** |
| M6 async communication | Not implemented; Redis infrastructure only |
| M7 AI intake | Later phase; legacy triage is not M7 |
| M8 policy RAG | Later phase; lexical prototype is not M8 |

## Delivered in Phase 8

- Added `request_attachments` metadata with explicit PENDING/READY/QUARANTINED/DELETED
  state and requester-visible/internal visibility.
- File bytes stay in MinIO/S3-compatible storage; PostgreSQL stores only governed
  metadata and object references.
- Upload reservation requires authenticated request scope and a supported MIME type,
  normalized safe filename and configured size limit.
- Browser uploads directly with a short-lived presigned POST. The S3 policy binds
  content type and maximum length to the reserved file rather than relying only on
  client-side checks.
- Upload completion locks the metadata row and verifies stored object size/content type
  using server-side S3 HEAD before marking the attachment READY.
- Client-provided checksum claims are not treated as verified integrity metadata;
  trusted server/worker hashing is deferred.
- Every download request is re-authorized before issuing a short-lived presigned GET.
- Structured drafts remain owner-only; submitted request access reuses governed
  requester/approval/manager/admin/auditor scope and adds active routed service-team
  scope for fulfillment files.
- INTERNAL attachments are hidden from the requester and limited to service-team,
  ADMIN/AUDITOR read scope; internal upload is limited to service staff/admin.
- Attachment readiness is audited and appears as a safe request timeline event without
  copying filenames or file contents into audit metadata.
- Request detail now supports direct upload/list/download for requester-visible files.
- MinIO receives a health gate in Compose and separate API-internal/browser-public S3
  endpoints so generated URLs work across the Docker/host boundary.

## Database and storage

Phase 8 revision: `h9d3f6c8e045`, following M5 `g8c2e5b7d934`.

The migration adds `request_attachments`, indexes and lifecycle/visibility checks.
Downgrade refuses when READY/QUARANTINED metadata exists because binary objects may
still live in external object storage.

Local object-storage defaults:

```text
API -> MinIO: http://minio:9000
Browser -> MinIO: http://localhost:9000
Bucket: centralops
Presign expiry: 300 seconds
Application max attachment size: 10 MiB
```

## Primary Phase 8 files

- Domain model: `backend/app/models/attachments.py`
- Schemas: `backend/app/schemas/attachments.py`
- Authorization/lifecycle: `backend/app/services/attachments.py`
- S3 adapter: `backend/app/services/storage.py`
- API: `backend/app/api/routes/attachments.py`
- Migration: `backend/alembic/versions/h9d3f6c8e045_add_request_attachments.py`
- Backend tests: `backend/tests/test_attachments.py`
- Frontend API/UI: `lib/attachment-api.ts`, `components/attachments/request-attachments.tsx`
- Browser gate: `scripts/m8_browser_smoke.py`
- Reviewer/run guide: `docs/M8_REQUEST_ATTACHMENTS.md`

## Verification gates

PR #14 stays draft until the final branch HEAD passes all of these:

1. Ruff + clean SQLite migration + full backend regressions.
2. TypeScript + ESLint + production frontend build + executable frontend regressions.
3. Clean PostgreSQL migration plus existing M3/M4/M5 concurrency/integrity gates.
4. Production Docker Compose with PostgreSQL/Redis/MinIO plus real Chromium regression
   through M2/M3/M4/M5 and a Phase 8 upload -> completion -> list -> authorized download
   whose downloaded bytes match the uploaded synthetic fixture.

No completion/merge claim is made until these HEAD-specific gates succeed.

## Explicit limits

Phase 8 does **not** provide malware scanning, antivirus certification, retention/legal
hold, object versioning, trusted server-computed SHA-256, large multipart upload,
preview conversion, backup validation or production S3 policy review. These boundaries
are intentional and documented rather than implied.

Existing auth hardening items also remain: secure-cookie transport, immediate access
JWT revocation, rate limiting, dependency remediation, TLS/backups and broader
failure/load/security review.

## Next

After Phase 8 is verified and merged, implement **Phase 9 / M6 asynchronous
communication**: Redis-backed worker, in-app notifications, email adapter and retry
behavior that cannot repeat core business actions.

Do not jump to AI intake/RAG before this governed standard request path remains
reliable through file handling and asynchronous communication.
