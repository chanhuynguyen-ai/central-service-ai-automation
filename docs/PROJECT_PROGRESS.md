# CentralOps AI - Project Progress Tracker

**Updated:** 2026-09-06  
**Current delivery:** PR #15 - asynchronous in-app/email notifications (M6)  
**Implementation branch:** `feat/async-notifications`

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
| **M6 async communication** | **Implemented in PR #15; final application checkpoint verified green** |
| M7 AI intake | Next after PR #15 merge; legacy triage is not M7 |
| M8 policy RAG | Later; lexical prototype is not M8 |

## Delivered in M6

- Durable PostgreSQL notification intents written inside approval/fulfillment
  transactions; no SMTP/Redis network call occurs inside core business transitions.
- Paired in-app and email channels with unique event/channel idempotency keys.
- Lifecycle notifications for approval assignment, rejection, request changes, final
  approval, service assignment and resolution.
- Recipient-scoped in-app list/read/read-all API and workspace bell with unread count.
- Redis-backed Dramatiq worker plus a durable scanner for PENDING/FAILED email rows.
- Persisted retry attempts/backoff and terminal DEAD state without replaying the
  request/approval/fulfillment action.
- Mailpit development SMTP catcher and browser-verifiable email delivery.
- Worker starts after the API migration/readiness gate and has its own Dramatiq
  process healthcheck rather than inheriting the API HTTP healthcheck.

## Database and runtime

M6 revision: `i0e4g7d9f156`, following Phase 8 `h9d3f6c8e045`.

Main runtime services now include PostgreSQL, Redis, MinIO, API, notification worker,
Mailpit and web. Mailpit is local-development infrastructure only.

Primary files:

- `backend/app/models/notifications.py`
- `backend/app/schemas/notifications.py`
- `backend/app/services/notifications.py`
- `backend/app/api/routes/notifications.py`
- `backend/app/notification_tasks.py`
- `backend/app/db/enqueue_pending_notifications.py`
- `backend/alembic/versions/i0e4g7d9f156_add_notifications.py`
- `lib/notification-api.ts`
- `components/notifications/notification-center.tsx`
- `scripts/m6_browser_smoke.py`
- `docs/M6_ASYNC_NOTIFICATIONS.md`

## Verification checkpoint

Verified application HEAD before documentation-only updates:
`69cd80bda4b9a555dadb321db90b1aafb7fe830c`.

| Gate | Evidence |
|---|---|
| CI backend + frontend | **#90 / 34011134494 SUCCESS**: **144 backend tests**, **81% coverage**, Ruff, clean SQLite migration, TypeScript, ESLint, production build and frontend tests |
| PostgreSQL regressions | **#63 / 34011134498 SUCCESS**: clean migration and existing workflow/activity/fulfillment concurrency/integrity probes |
| Docker/Chromium M2-M6 | **#66 / 34011134496 SUCCESS**: production Compose, M2-M5 + Phase 8 regressions, asynchronous Mailpit email and in-app notification UI |

The first browser attempts exposed startup sequencing and inherited-healthcheck defects;
those failures were used to harden Compose. The successful checkpoint includes the
fixes, not the earlier failing configuration.

Documentation commits after the application checkpoint do not change runtime code;
PR #15 must still be green on its final HEAD before merge.

## Delivery semantics and limits

Core business actions are not retried by the notification worker. Notification record
creation is database-idempotent by event/channel. External SMTP remains at-least-once:
a crash after SMTP acceptance but before recording SENT could duplicate an email on a
later retry. That limitation is explicit rather than presented as exactly-once email.

M6 does not include production SMTP credentials/provider validation, push/mobile,
Teams/Slack, SSE/WebSocket realtime delivery, per-user preference controls, delivery
analytics, or production load/failure certification.

Existing hardening backlog also remains: secure-cookie refresh transport, stronger
access-token revocation/rate limiting, dependency remediation, TLS/backups,
retention/redaction and broader security/load testing.

## Next

After PR #15 is final-green and merged, implement **Phase 10 / M7 AI Intake**:
classify against the published catalog, extract schema-bound editable values, compute
missing required fields deterministically, ask clarifying questions, expose confidence
and always require the employee to review/confirm. AI must not authorize, route final
approval authority, or bypass the standard request path.

Policy pgvector RAG remains Phase 11 after AI intake, not a parallel shortcut.