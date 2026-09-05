# M3 - Sequential workflows and assigned approval tasks

## What this slice does

The catalog path now continues from a saved structured draft to a real approval
workflow. Submission, decision history and the assigned inbox use the same
`service_requests` aggregate introduced in M2, not a second request store.

Employee -> Service catalog -> Save draft -> Submit for approval -> assigned
manager -> assigned service lead -> Approved.

A reviewer can instead Reject or Request changes. Rejection is terminal. Requested
changes return the request to the owner's editor; resubmission creates a new
attempt and restarts the **whole** chain. Previous submitted values and decisions
remain visible as history. These demo rules are not a claim about DKSH policy.

**Approved is not Completed.** Final approval records `approval_state=approved`
and `fulfillment_state=not_queued`. Service work-item creation, assignment,
resolution and closure belong to Phase 7. No fake fulfillment is performed here.

## Run the local Docker demo

Use a clean working tree in the repository root. After PR #11 is merged:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
docker compose up -d --build --wait --wait-timeout 180
docker compose exec api alembic current
docker compose exec api python -m app.db.seed_catalog
docker compose exec api python -m app.db.seed_workflows
Start-Process "http://localhost:3000"
```

Expected migration head: `e6a0c3f5b712`. Run migration checks in the API container
to target the actual PostgreSQL database; local `uv run alembic` may use SQLite.
The new seed skips existing workflow definitions, including customized ones.
It does not overwrite routing or publish a new version on every application start.

| Demo role | Email | Local-only password |
|---|---|---|
| Requester | employee@centralops.demo | Employee123! |
| Direct manager | manager.finance@centralops.demo | Manager123! |
| Second reviewer | service.lead@centralops.demo | ServiceLead123! |
| Unassigned approver | approver@centralops.demo | Approver123! |
| Administrator | admin@centralops.demo | Admin123! |
| Read-only auditor | auditor@centralops.demo | Auditor123! |

1. Employee chooses Laptop replacement, fills title, business context, reason,
   device and cost center, then saves. Submit is disabled until the saved draft is
   complete and the editor has no unsaved changes. Submission requires confirmation.
2. Under Submitted requests, inspect the active first step. Only the manager's
   task exists initially; the second step has not yet been activated.
3. Sign out; log in as the Finance Manager. Open Approvals, select the request,
   choose Approve and record the decision. It remains pending for the service lead.
4. Sign out; log in as the service lead, approve the newly assigned task. Status
   becomes Approved; the screen explicitly says fulfillment has not started.
5. Employee opens Submitted requests to inspect the full recorded chain.

For the revision path, choose Request changes with a reason at step 3. Employee
opens My drafts, edits and saves, then resubmits. Both Attempt 1 (changes requested)
and Attempt 2 are retained. The old task cannot be reused. Refresh workflow fetches
current state; there is no WebSocket/push delivery in this slice.

The generic approver account has no task in this demo merely because it has the
APPROVER role. Administrator access also does not grant an unassigned decision.

## API contract

All paths below have prefix `/api/v1/workflows` and require authentication.

| Method and path | Access / behavior |
|---|---|
| GET, POST `/definitions` | ADMIN; one default definition per catalog request type |
| PATCH `/definitions/{id}` | ADMIN; explicit `is_active` boolean |
| GET, POST `/definitions/{id}/versions` | ADMIN; create monotonically numbered draft versions |
| PUT `/definitions/{id}/versions/{number}` | ADMIN; replace a DRAFT configuration only |
| POST `/definitions/{id}/versions/{number}/publish` | ADMIN; publish and retire prior current version |
| GET `/requests` | Submitted request summaries in caller's allowed scope; limit/offset |
| GET `/requests/{id}` | Submitted values, attempts, steps, tasks and decisions |
| POST `/requests/{id}/submit` | Owner; body `{"revision": 3}`; no client-selected approver |
| GET `/approval-tasks?status=pending` | Only tasks assigned to the caller |
| GET `/approval-tasks?status=history` | Caller-specific decided/cancelled task history |
| POST `/approval-tasks/{id}/decisions` | Exact active assignee; `version`, `decision`, `comment` |

Example decision payload:

```json
{"version": 1, "decision": "request_changes", "comment": "Please specify the approved cost center."}
```

Allowed decisions: `approve`, `reject`, `request_changes`. A nonblank reason is
required for the latter two. Requester/self approval is forbidden, even for an
administrator. Stale revisions, repeated submission and duplicate decisions return
409. Wrong assignee returns 403; out-of-scope reads return 404. Input models reject
extra fields and unsupported resolver/mode/condition configuration.

## Supported workflow configuration

- Sequential ordered steps, at most 10, each using `ALL` approval mode.
- USER: one configured active eligible user.
- MANAGER: the requester's direct manager.
- ROLE: users holding a normalized role in the requester's department.
- TEAM_LEAD: a configured active service-team lead, or the catalog owning team.
- Assignees must be active and hold APPROVER or ADMIN. A manager role alone is not
  an approval grant. Resolvers refuse self-approval and empty/invalid results.
- All step assignees are resolved and snapshotted at submission. Later organization
  changes do not silently reroute in-flight work. Eligibility is rechecked on action
  and activation. Up to 50 assignees per step are supported.
- One published version per definition is enforced by a partial unique index.
  Definition-row locks serialize publication and version-number allocation.

ANY mode, conditions, amount-based routing, delegation, reassignment, graphical
workflow editing and automatic escalation are deliberately not implemented.
Unsupported input fails explicitly instead of being accepted and ignored.

## Transactions, snapshots and privacy

Submission locks the request, checks ownership and saved revision, validates the
pinned form, locks/selects the active published workflow and resolves every step.
Only then does it change state and create the instance, runtime steps, first tasks
and audit events. They commit together. No AI or notification call is in this
transaction. An unresolved/self approver returns 409 with **no** partial submission.
This first implementation leaves the draft available; it does not implement the
later administrator exception queue described in the broader application flow.

Each attempt snapshots form schema/data, title, description, requester display,
workflow configuration and resolved identities. Published/retired definitions are
immutable through the API. Runtime instances use UNIQUE(request_id, attempt),
not the initially proposed single instance per request, to retain resubmission
history. A partial unique index permits only one pending attempt per request.

Decisions lock the shared request row before refreshing task/step/instance state.
Task-version compare-and-swap and a unique decision-per-task constraint prevent
replay. The shared lock also serializes two *different* tasks in an ALL step so
completion is not lost or performed twice. Audit and next-step activation are in
that same transaction. If a future snapshotted approver is no longer eligible,
the current decision rolls back and returns an administrator-attention message;
there is no unsafe fallback approval or silent reassignment.

Rejection/request-changes closes the current attempt and cancels other pending
work. Editing while changes are requested remains owner-only. Reviewers see the
last **submitted snapshot**, not unsent edits. A new attempt uses the currently
published workflow, explicitly restarting the entire chain.

Submitted visibility is limited to the requester, their direct manager with
MANAGER role, actual current/past task assignees, ADMIN and AUDITOR. ADMIN/AUDITOR
read visibility is not an authority to decide an unassigned task. Audit records
contain identifiers/actions, not copied form values; submitted snapshots and
comments are available only through authorized workflow reads.

## Compatibility boundary

Legacy `/requests`, simple decisions/status updates, the Power Platform feed and
policy-assistant request-context path now accept only requests without a catalog
version. They cannot read or mutate the structured workflow through a weaker
legacy role check. Legacy metrics are labeled separately in the UI; they do not
pretend to count structured approvals. The stable DRF reference is retained after
submission; changing its display prefix is not needed for the lifecycle.

The old New request dialog remains explicitly labeled as a legacy prototype.
Use Service catalog / Submitted requests / Approvals for this governed flow.

## Migration and data safety

`e6a0c3f5b712` follows `d5f9b2e4a601`, adds seven workflow/task/decision tables and
approval/fulfillment/attempt fields. Existing M2 drafts and prototype requests are
not submitted or rewritten by the migration. Back up development data before
upgrading. Downgrade refuses once workflow definitions exist, rather than deleting
approval history. Do not use `docker compose down -v` on persistent user data.

## Verification and limits

See the canonical PROJECT_PROGRESS.md and PR #11 for current-head evidence.
The suite covers sequencing, ownership, assigned decisions, validation rollback,
self/deactivated reviewers, version preservation, requested changes, immutable
history and legacy-bypass guards. Frontend tests execute the typed API contract.

PostgreSQL CI probes use independent connections for duplicate submission,
duplicate intermediate/final decisions and two different ALL-assignee decisions.
Browser CI exercises actual production Docker images, PostgreSQL and Chromium
across employee, generic approver, manager and service-lead sessions. Test scripts
require CENTRALOPS_E2E=1 and a disposable environment; never run concurrency probes
against production. Browser artifacts contain demo screenshots, not token traces.

This is not a production-security certification or a load benchmark. Secure
cookie transport, broader session hardening, full domain timeline/comments,
fulfillment, authorized attachments, asynchronous notifications and real-provider
AI/RAG evaluation remain distinct roadmap work.
