# Phase 8 - Authorized request attachments

## Scope

Phase 8 adds governed request file handling without storing binary content in PostgreSQL.
PostgreSQL stores attachment metadata and lifecycle state; MinIO/S3-compatible object
storage holds file bytes. Every upload reservation and download URL is authorized by
the FastAPI backend.

The browser never receives long-lived object-storage credentials. Uploads use a
short-lived presigned POST policy and downloads use short-lived presigned GET URLs.

## Lifecycle

```text
Authorized request actor
  -> reserve attachment metadata (PENDING)
  -> receive short-lived presigned POST
  -> browser uploads directly to MinIO/S3
  -> API verifies object size + content type
  -> attachment becomes READY
  -> authorized reader requests download
  -> API re-checks request + attachment scope
  -> short-lived presigned GET
```

`QUARANTINED` and `DELETED` states are reserved for later security/retention work.
This milestone does not claim malware scanning.

## Storage boundary

- Binary file bytes live only in S3-compatible storage.
- PostgreSQL stores object key, original filename, MIME type, expected size, uploader,
  visibility, lifecycle timestamps and storage ETag.
- Object keys are generated server-side and do not contain user filenames.
- Client-provided SHA-256 values are not trusted as verified integrity metadata;
  `sha256` remains null until a trusted server/worker calculation is introduced.

## Upload security

The API validates:

- authenticated request scope,
- supported MIME type,
- maximum configured size,
- internal-file permission,
- normalized safe filename.

The presigned POST policy also enforces a server-defined content-length range and
content type at object storage. Completion then checks `HEAD` metadata and requires
the stored object size and content type to match the reservation before setting READY.

Local default maximum: **10 MiB**.

Allowed local demo types:

- PDF
- DOCX
- XLSX
- JPEG
- PNG
- plain text

These are an application allowlist, not proof that the file content is safe. Malware
scanning belongs to a later hardening hook before production use.

## Authorization

### Requester-visible files

An actor must first be authorized for the structured request. That includes the
requester, assigned approval actors/managers covered by the existing workflow scope,
ADMIN/AUDITOR read scope, and active service-team staff for a request that has entered
fulfillment.

### Internal files

- The requester never receives internal attachments, even if another role is present.
- ADMIN and AUDITOR can read internal files under their privileged read scope.
- Active SERVICE_AGENT/SERVICE_LEAD users can read internal files only for work routed
  to their active service team.
- Internal uploads are limited to ADMIN or authorized service-team staff.

Every download action goes back through the API; object storage URLs themselves are
short lived and are not treated as authorization state.

## API

All endpoints require authentication and use `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/requests/{request_id}/attachments` | List attachment metadata visible to caller |
| POST | `/requests/{request_id}/attachments/presign` | Reserve metadata + get bounded presigned POST |
| POST | `/requests/{request_id}/attachments/{attachment_id}/complete` | Verify stored object and mark READY |
| POST | `/requests/{request_id}/attachments/{attachment_id}/download` | Re-authorize and issue short-lived GET URL |

The server does not accept an object key, uploader identity, lifecycle status or audit
actor from the client.

## Database migration

Revision: `h9d3f6c8e045`

Previous revision: `g8c2e5b7d934` (M5 service fulfillment).

The migration creates `request_attachments` and supporting indexes. Downgrade refuses
to remove the table if READY/QUARANTINED rows exist because object bytes may still
exist outside PostgreSQL.

## Local Docker configuration

MinIO is part of the existing Compose topology. Phase 8 connects the API to it using
separate endpoints:

```text
S3_ENDPOINT_URL=http://minio:9000          # API container -> MinIO
S3_PUBLIC_ENDPOINT_URL=http://localhost:9000 # browser -> MinIO
```

The split is required because a URL signed for the Docker hostname is not useful to a
host browser, while the API container should not depend on host networking.

From Windows PowerShell after the PR is merged:

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

Expected Alembic head: `h9d3f6c8e045`.

## Verification target

Before merge, the branch must pass:

- Ruff
- clean SQLite migration
- full backend regressions including attachment authorization/integrity tests
- TypeScript
- ESLint
- production frontend build
- executable frontend regression tests
- PostgreSQL workflow/concurrency regression gate
- production Docker + Chromium M2/M3/M4/M5 regressions
- Chromium attachment upload to real MinIO, completion, listing and authorized download
  with downloaded bytes matching the uploaded fixture

Passing these gates demonstrates the tested functional boundary only. It is not a
production security certification, malware-safety guarantee, load benchmark or backup
validation.

## Deferred

- malware scanning/quarantine worker
- file deletion/retention and legal hold
- object versioning and lifecycle policies
- server-computed SHA-256
- multipart large-file uploads
- image/document preview
- asynchronous notifications

Next roadmap phase after Phase 8: **Phase 9 - background worker and notifications**.
