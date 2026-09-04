# Product Specification

## 1. Product name

**Central Service AI Automation**  
Subtitle: **Employee Request & Approval System**

---

## 2. Product vision

Create a single intelligent internal-service portal where employees can ask for what they need in plain language, the system converts that intent into a structured request, routes it through the right approval process, and transparently tracks fulfillment from submission to closure.

The core idea is not “an AI chatbot for employees.” The core idea is **a reliable workflow product with AI embedded where AI reduces friction**.

---

## 3. Product objectives

### Primary objectives

- Reduce request submission friction.
- Reduce manual triage and routing.
- Reduce approval turnaround time.
- Increase visibility into request status.
- Ensure approvals follow policy.
- Create an auditable source of truth.

### Secondary objectives

- Reduce repetitive policy questions.
- Identify bottlenecks.
- Improve service-team workload visibility.
- Provide reusable workflow infrastructure for multiple departments.

---

## 4. Personas

### 4.1 Employee — “Requester”

Needs to submit a request quickly and know what happens next.

**Pain points:**
- does not know which form to use,
- does not know required information,
- does not know who should approve,
- repeatedly asks for status.

**Key screens:** Home, New Request, My Requests, Request Detail, AI Assistant.

### 4.2 Manager — “Approver”

Needs enough context to make a quick but responsible decision.

**Pain points:**
- approval requests buried in email,
- unclear business justification,
- no easy way to see pending workload,
- difficult to trace older decisions.

**Key screens:** Approval Inbox, Request Detail, Team Requests.

### 4.3 Service Agent

Needs an actionable queue after approvals are complete.

**Pain points:**
- incomplete request details,
- unclear priority,
- tasks assigned informally,
- SLA not visible.

**Key screens:** Service Queue, Assigned to Me, Request Detail.

### 4.4 Administrator

Needs to configure the system without changing application code for every policy adjustment.

**Key screens:** Request Types, Form Builder, Workflow Configuration, Users/Roles, Policy Knowledge, Audit, Integrations.

---

## 5. Product information architecture

```text
Home / Dashboard
├── New Request
│   ├── Ask AI
│   └── Browse Request Catalog
├── My Requests
│   ├── Draft
│   ├── Pending Approval
│   ├── In Progress
│   ├── Waiting for Me
│   └── Completed
├── Approvals
│   ├── Pending
│   └── History
├── Service Desk
│   ├── Queue
│   ├── Assigned to Me
│   └── SLA At Risk
├── Knowledge / Policies
├── Analytics
└── Admin
    ├── Request Types
    ├── Form Schemas
    ├── Workflows
    ├── Users & Roles
    ├── Departments
    ├── Notifications
    ├── Policy Documents
    └── Audit Logs
```

Navigation items are role-aware. Employees should not see admin/service-management functions they cannot use.

---

## 6. Feature specification

## 6.1 Authentication and user profile

**Capabilities**
- Sign in/sign out.
- “My profile” with name, department, manager, role, email.
- Session expiration and refresh.
- Admin can deactivate a user.
- Production option for SSO.

**Business rules**
- Deactivated users cannot create new sessions.
- Historical requests remain associated with deactivated users.
- Authorization is enforced server-side, not only hidden in UI.

---

## 6.2 Dashboard

### Employee dashboard widgets

- **Create request** primary CTA.
- Open requests count.
- Requests waiting for employee input.
- Recently updated requests.
- Common request types.
- AI assistant entry point.

### Approver dashboard additions

- Pending approvals.
- Overdue approvals.
- Requests needing clarification.

### Service lead additions

- Unassigned queue.
- SLA at risk.
- Workload by agent.

---

## 6.3 Request catalog

Each request type includes:

- title,
- description,
- category,
- icon,
- owning service team,
- expected response time,
- dynamic form schema,
- attachment rules,
- workflow definition,
- policy links,
- active/inactive status.

**Example request types**

| Category | Request type | Example fields |
|---|---|---|
| IT | Laptop request | device type, reason, urgency, cost center |
| IT | Software access | application, access level, business justification |
| HR | Employment letter | letter type, language, purpose |
| Finance | Reimbursement | amount, currency, expense date, receipt |
| Facilities | Maintenance | location, issue, urgency, photo |
| Security | Building access | location, duration, reason |

---

## 6.4 Dynamic forms

The frontend should render forms from JSON form schemas instead of hard-coding every request type.

Supported field types for MVP:

- text,
- textarea,
- number,
- currency,
- date,
- date range,
- boolean,
- select,
- multi-select,
- user picker,
- department picker,
- attachment,
- URL.

Later:

- table/repeater fields,
- computed fields,
- conditional branches,
- API-backed lookup fields.

---

## 6.5 AI-assisted request creation

### User experience

1. User types: “My laptop keeps shutting down and I need a replacement for client work.”
2. AI classifies the request as **IT → Laptop/Hardware Request**.
3. AI extracts:
   - reason = device instability,
   - business impact = client work,
   - likely urgency = high.
4. Required fields are checked against the form schema.
5. AI asks only for missing fields, for example desired device or cost center.
6. The user sees a structured preview.
7. User explicitly confirms submission.

### AI constraints

- AI must not invent employee data.
- AI must not silently submit a request.
- Extracted values should be editable.
- Low-confidence classification should show alternatives.
- Policy-sensitive answers should cite the internal policy source inside the application.
- Approval authority remains deterministic and policy-driven.

---

## 6.6 Request lifecycle

Recommended high-level states:

```text
DRAFT
SUBMITTED
PENDING_APPROVAL
CHANGES_REQUESTED
REJECTED
APPROVED
QUEUED
IN_PROGRESS
WAITING_FOR_REQUESTER
RESOLVED
CLOSED
CANCELLED
```

Not every request type must use every state.

### Important distinction

- **Approval state** represents governance decision.
- **Fulfillment state** represents operational work.

Do not collapse these into one ambiguous “status” field internally. The API can expose a user-friendly aggregate status, but the database should retain enough detail to distinguish them.

---

## 6.7 Approval inbox

Each approval card/row should show:

- requester,
- request type,
- request title,
- submission date,
- amount/critical field if relevant,
- current SLA/age,
- AI summary,
- prior approvals.

Actions:

- Approve.
- Reject.
- Request changes.
- Open full request.
- Add decision comment.

High-impact decisions should require a reason or confirmation.

---

## 6.8 Workflow configuration

An approval workflow contains:

- trigger conditions,
- ordered workflow steps,
- approver resolver,
- approval mode,
- escalation configuration.

### Approver resolver examples

- requester’s direct manager,
- manager’s manager,
- department head,
- users with role `FINANCE_APPROVER`,
- named person,
- owning service lead,
- resolver based on amount threshold.

### Example

**Laptop Request**

```text
If estimated_cost < 1,000 USD:
    Step 1: Direct Manager
    Step 2: IT Service Lead

If estimated_cost >= 1,000 USD:
    Step 1: Direct Manager
    Step 2: Department Head
    Step 3: Finance Approver
    Step 4: IT Service Lead
```

The actual workflow selected for a request is snapshotted at submission so later policy changes do not rewrite history.

---

## 6.9 Request detail page

Recommended sections:

1. Header: request ID, title, status, priority.
2. Requester information.
3. Submitted form values.
4. Approval progress stepper.
5. Fulfillment information.
6. SLA/due date.
7. Attachments.
8. Comments.
9. Activity timeline.
10. Related policies.
11. AI summary card.

Sensitive/internal service notes are separated from employee-visible comments.

---

## 6.10 Notifications

Notification events:

- Request submitted.
- Approval assigned.
- Request approved.
- Request rejected.
- Changes requested.
- Employee replied.
- Agent assigned.
- Work started.
- SLA warning.
- Resolution posted.
- Request closed.

Notification preferences can be added later; MVP can use sensible defaults.

---

## 6.11 Knowledge and policy assistant

Admin uploads internal policy documents.

System flow:

1. File uploaded.
2. Text extracted.
3. Split into chunks.
4. Embeddings generated.
5. Chunks stored with metadata.
6. User asks a question.
7. Relevant chunks retrieved.
8. LLM generates answer constrained by retrieved content.
9. UI displays source document references.

The assistant should explicitly say when the knowledge base does not contain enough information.

---

## 6.12 Analytics

### Operational metrics

- total requests,
- active requests,
- average first-response time,
- average approval time,
- average resolution time,
- SLA compliance,
- overdue requests,
- backlog size.

### Breakdown dimensions

- request type,
- service team,
- department,
- approver,
- time period,
- priority.

### AI metrics

- AI classification acceptance rate,
- clarification rate,
- AI-assisted vs manual request completion time,
- policy assistant “no answer” rate,
- fallback/manual correction rate.

---

## 7. Important product rules

1. A user cannot approve their own request unless a request type explicitly allows it.
2. Final approval is valid only when all required workflow conditions are satisfied.
3. Workflow steps are immutable after a decision; corrections are represented as new events/actions.
4. Request cancellation rules depend on lifecycle state.
5. AI output never bypasses permission checks.
6. Attachments inherit request visibility and access controls.
7. Internal notes are not exposed to requesters.
8. Every sensitive status/assignment/approval change generates an audit event.
9. Deleted users should normally be soft-deactivated rather than physically removed.
10. Submitted request data should be snapshotted to preserve historical meaning.

---

## 8. MVP user stories

### Employee

- As an employee, I can create a request from a catalog.
- As an employee, I can describe a need to AI and receive a structured draft.
- As an employee, I can upload supporting documents.
- As an employee, I can see who currently needs to act.
- As an employee, I can answer clarification requests.
- As an employee, I can view completed requests.

### Approver

- As an approver, I can see all requests waiting for my decision.
- As an approver, I can see a concise summary and full details.
- As an approver, I can approve, reject, or request changes.
- As an approver, I can see my previous decisions.

### Service agent

- As an agent, I can see approved requests in my service queue.
- As an agent, I can assign a request to myself.
- As an agent, I can update operational status.
- As an agent, I can add internal notes.
- As an agent, I can mark work resolved.

### Admin

- As an admin, I can create a request type.
- As an admin, I can define required fields.
- As an admin, I can configure an approval workflow.
- As an admin, I can manage roles.
- As an admin, I can upload policy documents.
- As an admin, I can inspect audit records.

---

## 9. MVP acceptance criteria

A release qualifies as MVP when:

- At least three request types can be configured.
- At least one request type uses a two-step workflow.
- Manager-based approver resolution works.
- Employee, approver, service agent, and admin roles are enforced.
- Full request lifecycle works end-to-end.
- AI can produce a draft from natural language.
- AI can identify at least one missing required field.
- Every approval/status change appears in history.
- Basic email/in-app notification works.
- Application can run using Docker Compose.
- Seed/demo data is included.
- Core backend tests run in CI.

---

## 10. Success metrics

For a real deployment, track:

| Goal | Example metric |
|---|---|
| Faster intake | Median time to submit a valid request |
| Better completeness | % requests returned due to missing information |
| Faster approvals | Median approval duration |
| Better SLA | % resolved within target |
| Reduced support overhead | Repeated policy questions per month |
| AI usefulness | % AI-generated drafts submitted with minor/no edits |
| Better transparency | Status inquiry messages per request |

---

## 11. Out of scope for initial MVP

Do not build these first:

- Full BPMN engine.
- Multi-tenant SaaS billing.
- Native mobile application.
- Voice assistant.
- Autonomous approval decisions.
- Large enterprise integration marketplace.
- Complex payroll/financial accounting.
- Heavy event-streaming architecture.

They distract from the strongest first version.

---

## 12. Product roadmap

### V1 — Workflow MVP
Employee requests, manager approval, service fulfillment, audit trail.

### V1.1 — AI intake
Natural-language request drafting, extraction, clarification.

### V1.2 — Policy RAG
Internal policy question answering with source references.

### V1.3 — Workflow power features
Parallel approvals, delegation, escalation, conditions, thresholds.

### V1.4 — Operations analytics
SLA, bottleneck, workload, trends.

### V2 — Enterprise integrations
SSO, Teams/Slack, HRIS, ticketing, procurement systems.

### V3 — Workflow platform
Visual form/workflow builder and reusable automation templates.
