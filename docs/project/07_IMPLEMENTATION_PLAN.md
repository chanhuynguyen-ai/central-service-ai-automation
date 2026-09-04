# Implementation Plan — Recommended Build Order

## 1. Goal of this plan

Build the application in vertical slices so that every stage leaves the repository in a runnable state.

The most important rule:

> **Do not build the AI layer first. Build a correct request/approval system, then add AI as an accelerator.**

---

# Phase 0 — Project foundation

## Step 0.1 — Create repository structure

```text
central-service-ai/
├── apps/web
├── apps/api
├── docs
├── infrastructure
├── scripts
├── docker-compose.yml
├── .env.example
├── README.md
└── .github/workflows
```

### Deliverables

- Git repository initialized.
- `main` protected later.
- `.gitignore`.
- `README.md` with architecture diagram and startup instructions.
- `.env.example`.

### Acceptance criteria

A new developer can clone the repo and understand where frontend/backend infrastructure belong.

---

## Step 0.2 — Docker Compose infrastructure

Add:

- PostgreSQL.
- Redis.
- MinIO.

Optional DB GUI for development only.

### Acceptance criteria

```text
docker compose up -d
```

starts infrastructure and health checks pass.

---

# Phase 1 — Backend foundation

## Step 1.1 — Bootstrap FastAPI

Implement:

- app factory/main entrypoint,
- configuration loader,
- database session,
- `/health`,
- `/ready`,
- central exception handling,
- request/correlation id,
- structured logging.

### Acceptance criteria

`GET /health` returns success and API can connect to DB.

---

## Step 1.2 — SQLAlchemy + Alembic

Create first migrations for:

- users,
- roles,
- user_roles,
- departments,
- service_teams.

Add seed script.

### Acceptance criteria

```text
alembic upgrade head
```

works from a clean database.

---

# Phase 2 — Authentication and authorization

## Step 2.1 — Local authentication

Build:

- password hashing,
- login,
- logout,
- refresh/session handling,
- `/auth/me`.

### Step 2.2 — RBAC

Implement role constants and centralized permission helpers.

Seed roles:

- EMPLOYEE,
- APPROVER,
- MANAGER,
- SERVICE_AGENT,
- SERVICE_LEAD,
- ADMIN,
- AUDITOR.

### Tests

- invalid password rejected,
- deactivated user rejected,
- refresh rotation works,
- unauthorized role receives 403.

### Milestone

**M1: Secure API foundation**

---

# Phase 3 — Frontend shell

## Step 3.1 — Bootstrap Next.js/TypeScript

Add:

- Tailwind,
- shadcn/ui,
- API client,
- query provider,
- authentication state,
- protected routes.

## Step 3.2 — Application shell

Create:

- sidebar,
- top bar,
- breadcrumbs,
- notification placeholder,
- profile menu.

## Step 3.3 — Login page

Connect to real backend.

### Acceptance criteria

Different demo users log in and see role-aware navigation.

---

# Phase 4 — Request catalog and dynamic forms

## Step 4.1 — Request type/version schema

Backend tables:

- request_types,
- request_type_versions.

Admin API can create/update/publish a request type version.

## Step 4.2 — Dynamic form schema

Define an internal JSON schema contract.

Example:

```json
{
  "sections": [
    {
      "title": "Request details",
      "fields": [
        {
          "key": "reason",
          "type": "textarea",
          "label": "Reason",
          "required": true
        }
      ]
    }
  ]
}
```

## Step 4.3 — Frontend form renderer

Build components for supported field types.

## Step 4.4 — Draft request

Create:

- request row in DRAFT state,
- save draft,
- edit draft,
- form validation.

### Tests

- invalid required field blocked,
- request type version preserved,
- employee cannot edit another employee’s draft.

### Milestone

**M2: Employee can create a structured request draft**

---

# Phase 5 — Workflow and approvals

This is the most important engineering phase.

## Step 5.1 — Workflow definitions

Create:

- workflow_definitions,
- workflow_versions,
- workflow_step_definitions.

For first implementation, support sequential workflow only.

## Step 5.2 — Approver resolvers

Implement in this order:

1. Explicit named user.
2. Requester direct manager.
3. Role in requester department.
4. Service team lead.

## Step 5.3 — Runtime workflow tables

Create:

- workflow_instances,
- workflow_step_instances,
- approval_tasks,
- approval_decisions.

## Step 5.4 — Submit use case

Implement one transaction that:

- validates draft,
- freezes request version,
- selects workflow,
- creates workflow instance,
- activates first step,
- creates approval tasks,
- writes events.

## Step 5.5 — Approval actions

Implement:

- approve,
- reject,
- request changes.

## Step 5.6 — Approval inbox UI

- list pending tasks,
- request preview,
- detail page/panel,
- decision actions.

### Critical tests

- employee cannot approve own task without explicit policy.
- wrong user cannot approve task.
- duplicate approval returns conflict.
- final step transitions request to approved.
- reject terminates workflow.

### Milestone

**M3: Complete request → manager approval lifecycle**

At this point, record a first demo. This is already a valuable project.

---

# Phase 6 — Request timeline, comments, and audit

## Step 6.1 — Request events

Implement append-only domain events for timeline.

## Step 6.2 — Comments

Add:

- requester-visible comments,
- internal service notes.

## Step 6.3 — Audit log

Audit:

- auth events,
- approval actions,
- workflow configuration changes,
- request type publication,
- role changes.

## Step 6.4 — Request detail UI

Build the polished full page:

- request fields,
- approval progress,
- comments,
- attachments placeholder,
- timeline.

### Milestone

**M4: Traceable, auditable workflow system**

---

# Phase 7 — Service fulfillment

## Step 7.1 — Service work item

When final approval succeeds, create a service work item.

## Step 7.2 — Service queue

Build:

- unassigned,
- assigned to me,
- SLA at risk filters.

## Step 7.3 — Work actions

- assign,
- start,
- wait for requester,
- resolve,
- close.

### Tests

- only authorized service team members can manage work item,
- requester sees only permitted internal/external information,
- resolution updates request aggregate state.

### Milestone

**M5: End-to-end request → approval → fulfillment**

---

# Phase 8 — Attachments

## Step 8.1 — Object storage integration

Implement MinIO locally.

## Step 8.2 — Presigned uploads

Build secure upload completion flow.

## Step 8.3 — Download authorization

Every download request checks access before issuing a short-lived URL.

### Later security hook

Add malware scanning before marking file READY.

---

# Phase 9 — Notifications

## Step 9.1 — Background worker

Connect Redis + Celery/Dramatiq.

## Step 9.2 — In-app notifications

Create DB notifications and unread badge.

## Step 9.3 — Email adapter

Use a dev SMTP catcher locally and a real provider only in deployed environment.

Notification triggers:

- assigned approval,
- rejected,
- changes requested,
- final approval,
- service assignment,
- resolution.

## Step 9.4 — Retry behavior

Failed delivery should retry without repeating the business action.

### Milestone

**M6: Event-driven user communication**

---

# Phase 10 — AI intake assistant

Only start this after the standard form path is reliable.

## Step 10.1 — AI provider interface

Create provider-agnostic interface.

## Step 10.2 — Request classifier

Input:

- user text,
- allowed request-type names/descriptions.

Output:

- request type code,
- confidence,
- alternatives.

## Step 10.3 — Structured extraction

Load selected request form schema and extract known values.

## Step 10.4 — Missing field detector

This should mostly be deterministic after extraction:

```text
required schema fields - valid extracted/user fields = missing fields
```

Do not ask the LLM to decide what is required if the schema already defines it.

## Step 10.5 — AI request drafting UI

Experience:

```text
natural language -> suggestion -> extracted form -> clarification -> review
```

## Step 10.6 — Evaluation set

Create 30–100 test utterances across request types and track:

- classification accuracy,
- top-2 accuracy,
- extraction correctness,
- missing-field correctness.

### Milestone

**M7: AI meaningfully reduces request-entry effort**

---

# Phase 11 — Policy RAG

## Step 11.1 — pgvector

Enable extension and create policy document/chunk models.

## Step 11.2 — Document ingestion worker

Pipeline:

```text
upload -> extract -> chunk -> embed -> store
```

## Step 11.3 — Retrieval API

Filter by:

- policy status,
- department/access scope,
- effective date.

Then perform vector similarity search.

## Step 11.4 — Grounded answer endpoint

Return:

```json
{
  "answer": "...",
  "sources": [
    {"document": "IT Access Policy", "section": "4.2"}
  ],
  "insufficient_evidence": false
}
```

## Step 11.5 — Knowledge UI

Show source links and warning when evidence is insufficient.

### Milestone

**M8: Policy-grounded internal AI assistant**

---

# Phase 12 — Admin configuration

## Step 12.1 — Request type editor

Create/publish versions.

## Step 12.2 — Workflow step editor

Start with ordered cards/forms, not drag-drop canvas.

## Step 12.3 — Role/user admin

Manage app roles and service-team membership.

## Step 12.4 — Policy document admin

Upload, publish, retire.

### Important

Publishing creates a new immutable version. Existing requests continue using previous versions.

---

# Phase 13 — SLA and escalation

## Step 13.1 — Due-time calculation

Store snapshot due times.

## Step 13.2 — Scheduled checker

Hourly or more appropriate scheduled worker checks deadlines.

## Step 13.3 — Escalation

Examples:

- notify approver at 80% of target,
- notify manager/service lead after breach,
- optional delegated fallback later.

---

# Phase 14 — Analytics

## Step 14.1 — Operational queries

Start with direct PostgreSQL aggregate queries.

Metrics:

- request counts,
- pending approvals,
- average approval duration,
- average resolution duration,
- SLA compliance.

## Step 14.2 — Dashboard

Use cards + separate charts.

Avoid building a data warehouse until real data volume requires it.

---

# Phase 15 — Hardening

## Step 15.1 — Security review

Checklist:

- [ ] No plaintext passwords/tokens.
- [ ] Auth cookies secure in production.
- [ ] Rate limit login.
- [ ] CORS restricted.
- [ ] Attachment permissions enforced.
- [ ] Internal comments protected.
- [ ] AI inputs scrubbed/logged according to policy.
- [ ] Admin actions audited.
- [ ] No secret committed to Git.

## Step 15.2 — Test coverage

Prioritize domain-critical tests, not meaningless percentage targets.

## Step 15.3 — E2E tests

At minimum:

1. Employee submits request.
2. Manager approves.
3. IT approves.
4. Agent fulfills.
5. Employee sees completion.

## Step 15.4 — Load and failure tests

Test:

- repeated approval clicks,
- queue/email failure,
- AI provider unavailable,
- database restart recovery,
- large attachment rejection.

---

# Phase 16 — Deployment

## Development

```text
Docker Compose
```

## Simple portfolio deployment

Possible topology:

```text
Reverse proxy
├── Next.js web
├── FastAPI api
└── Worker

Managed/self-hosted:
├── PostgreSQL
├── Redis
└── S3-compatible storage
```

Use HTTPS and secrets management.

## Production-oriented enhancements

- managed database,
- backup/restore testing,
- centralized logs,
- OpenTelemetry,
- error monitoring,
- CI/CD environments,
- database migration release procedure.

---

# Phase 17 — Git and commit strategy

Use small feature commits.

Example branch sequence:

```text
feat/project-foundation
feat/auth-rbac
feat/request-catalog
feat/dynamic-forms
feat/workflow-engine
feat/approval-inbox
feat/request-timeline
feat/service-desk
feat/notifications
feat/ai-intake
feat/policy-rag
feat/admin-console
feat/analytics
chore/deployment
```

Example commits:

```text
feat(auth): add local session authentication and role loading
feat(requests): add versioned request type schema
feat(workflow): instantiate manager approval on request submission
feat(approvals): prevent duplicate approval decisions
feat(ai): extract structured request fields from natural language
```

---

# Phase 18 — Recommended build milestones

| Milestone | Result | Portfolio value |
|---|---|---|
| M1 | Secure backend/auth | Backend fundamentals |
| M2 | Dynamic request creation | Product + schema design |
| M3 | Approval workflow | Core system-design differentiator |
| M4 | Audit/timeline | Enterprise readiness |
| M5 | Service fulfillment | True end-to-end workflow |
| M6 | Async notifications | Background processing |
| M7 | AI intake | Applied LLM integration |
| M8 | Policy RAG | Retrieval/AI architecture |
| M9 | Admin + analytics | Product completeness |
| M10 | Deployment + observability | Production engineering |

---

# Phase 19 — What to implement first this week

If starting from zero, use this exact order:

### Build 1

1. Repo.
2. Docker Compose PostgreSQL/Redis.
3. FastAPI health.
4. SQLAlchemy/Alembic.
5. User/department/role seed.

### Build 2

6. Login.
7. `/auth/me`.
8. Next.js login.
9. App shell.

### Build 3

10. Request type models.
11. One hard-seeded request type first.
12. Dynamic form renderer.
13. Draft request API.

### Build 4

14. Workflow tables.
15. Manager resolver.
16. Submit transaction.
17. Approval inbox.
18. Approve/reject.

### Build 5

19. Request detail timeline.
20. Service work item.
21. Service queue.
22. Resolve/close.

Only after Build 5:

23. AI classification/extraction.
24. Notifications.
25. RAG.
26. Admin editor.
27. Analytics.

This order minimizes the risk of having an impressive AI demo attached to an unreliable workflow backend.

---

# Phase 20 — Final recruiter/demo checklist

Before presenting the project:

- [ ] `docker compose up` starts the stack.
- [ ] README contains architecture diagram.
- [ ] Demo accounts are documented safely.
- [ ] Seed data works.
- [ ] API has OpenAPI docs.
- [ ] Screenshot/GIF of request flow included.
- [ ] AI can be disabled and core app still works.
- [ ] Approval permissions are demonstrated.
- [ ] Audit timeline is visible.
- [ ] At least one automated test proves workflow behavior.
- [ ] CI badge is green.
- [ ] `.env` is not committed.
- [ ] LICENSE included if you intend the repository to be open source.
- [ ] Roadmap and known limitations are honest.

## Best final demo narrative

Do not demo ten unrelated features. Demo one coherent story:

> “An employee explains a problem in natural language. AI creates a structured request. The system validates it, deterministically routes the correct multi-step approval, records each decision, creates an operational service task, tracks SLA and history, and closes the request. The same platform is configurable for HR, Finance, Facilities, and IT.”

That narrative communicates both engineering depth and practical product value.
