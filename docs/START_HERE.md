# Start Here - CentralOps AI

This repository is being developed in two parallel tracks:

- **Core engineering track:** build the reliable employee request -> approval -> fulfillment platform.
- **AI & Automation internship track:** produce verifiable Power Platform, data, testing/UAT,
  documentation, monitoring, and AI POC evidence without weakening the core architecture.

## What the current starter hardening changed

1. Preserved the eight project source-of-truth documents under `docs/project/`.
2. Added an explicit roadmap audit in `docs/IMPLEMENTATION_STATUS.md`.
3. Added a DKSH job-description evidence matrix in `docs/JD_ALIGNMENT_DKSH.md`.
4. Added Alembic and a baseline migration instead of relying on runtime table creation.
5. Added `/ready`, request correlation IDs, and JSON access logging.
6. Added Redis and MinIO to the local Docker topology for later worker/file phases.
7. Added structured validation for LLM triage output and hardened two authorization rules.
8. Added a repeatable CSV data-cleaning/quality report exercise for the automation-internship track.
9. Added stakeholder, meeting-note, and UAT execution templates.

## Run locally on Windows PowerShell

From the repository root:

```powershell
cd backend
uv lock
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Open a second PowerShell window:

```powershell
cd <repository-root>
npm ci
$env:NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
npm run dev
```

Or use Docker Desktop:

```powershell
docker compose up --build
```

Verify:

```text
http://localhost:8000/health
http://localhost:8000/ready
http://localhost:8000/docs
http://localhost:3000
```

## Run the data-quality exercise

```powershell
python scripts/clean_service_requests.py
```

Review:

```text
data/generated/service_requests_clean.csv
data/generated/data_quality_report.json
```

## Next implementation sprint - M1 backfill: organization and RBAC

The prototype currently stores `department` and `role` as strings on the user. Before building
manager-based workflow routing, normalize the identity/organization model.

Create branch:

```text
feat/organization-rbac
```

Implement in this order:

1. `departments` table.
2. `roles` and `user_roles` tables.
3. `service_teams` and membership table.
4. `users.manager_id` and department foreign key.
5. Seed employee -> direct manager -> IT lead/service agent/admin relationships.
6. Central permission functions instead of scattered role-string checks.
7. Refresh/logout session model or explicitly defer it with tests/documented limitation.
8. Alembic migration and API tests.

Acceptance criteria:

- Deactivated user cannot log in.
- Employee can read only authorized requests.
- User cannot approve their own request.
- Manager relation can be resolved deterministically from the database.
- Service team membership can be resolved deterministically from the database.
- A clean database can be created only through `alembic upgrade head`.

## Following sprints

1. **Request catalog + dynamic drafts** - versioned request types and JSON form schema.
2. **Workflow engine** - workflow definitions/versions/instances, steps, manager resolver, approval tasks.
3. **Audit + fulfillment** - timeline, comments, service queue, resolve/close.
4. **Worker + notifications + attachments** - Redis jobs, email/in-app notifications, MinIO presigned files.
5. **AI intake evaluation** - classify/extract/missing fields with a 30-100 utterance evaluation set.
6. **Policy RAG** - document ingestion, chunks, pgvector/hybrid retrieval, source-level permissions.
7. **Power Platform evidence** - real Canvas App, Power Automate run, Power BI dashboard when a tenant is available.
8. **Production hardening** - SSO/OIDC, rate limits, OpenTelemetry, deployment, backup/restore, security tests.

Do not add autonomous approval. AI may assist intake, retrieval, summarization, and recommendations;
workflow routing, authorization, and approval decisions remain deterministic/human-owned.
