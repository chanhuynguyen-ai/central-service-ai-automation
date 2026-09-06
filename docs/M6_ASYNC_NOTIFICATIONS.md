# M6 - Async notifications

**Phase:** 9 / M6  
**Branch:** `feat/async-notifications`  
**Verified application checkpoint:** `69cd80bda4b9a555dadb321db90b1aafb7fe830c`

M6 adds durable in-app notifications and asynchronous development email delivery to
the governed CentralOps lifecycle. Notification delivery is deliberately separated
from the request, approval and fulfillment transactions: business actions persist a
notification intent in PostgreSQL, and a Redis-backed Dramatiq worker delivers email
after commit.

## Delivered behavior

Lifecycle intents are created for:

- approval task assigned -> assigned approver,
- request rejected -> requester,
- changes requested -> requester,
- final approval -> requester,
- service work assigned -> assignee,
- service resolution -> requester.

Each event produces an `IN_APP` and `EMAIL` row with a unique `(event_key, channel)`
constraint. Replaying notification enqueue logic therefore returns the existing row
instead of creating a second notification. This protects notification history; it
does not re-run the business transition.

## In-app API and UI

Authenticated endpoints:

```text
GET  /api/v1/notifications
POST /api/v1/notifications/{notification_id}/read
POST /api/v1/notifications/read-all
```

The API is scoped to the authenticated recipient. Another user receives 404 when
trying to mark somebody else's notification as read. The workspace bell shows unread
count, polls every 30 seconds, lists notification text, and supports individual/all
read state.

## Email worker

Docker Compose adds:

- Redis as the Dramatiq broker,
- a dedicated `worker` container,
- Mailpit as a local SMTP catcher (`localhost:1025`) and review UI (`localhost:8025`).

The worker starts only after the API is healthy, which means Alembic migrations have
finished. A worker-specific healthcheck verifies the Dramatiq process instead of
reusing the API `/ready` healthcheck.

A small scanner periodically reads due `PENDING`/`FAILED` email rows from PostgreSQL
and publishes their IDs to Redis. The worker locks a notification row, sends email,
and records `SENT`, `FAILED` or `DEAD`. Failed email attempts use persisted backoff
and stop at `NOTIFICATION_MAX_ATTEMPTS`.

## Transaction boundary

Notification intent is written in the same database transaction as the domain event.
No SMTP or Redis call occurs inside the approval/fulfillment transaction. Therefore a
Mailpit/SMTP/Redis outage cannot make the HTTP business action retry itself.

The worker is intentionally at-least-once around external SMTP delivery. A rare crash
after SMTP accepts a message but before the database records `SENT` can produce a
duplicate email on retry. The business action and in-app record still remain exactly
one because they are protected by database state and event/channel uniqueness. A
production provider with delivery-idempotency support would be the next hardening
step for stronger email semantics.

## Database

Migration head:

```text
h9d3f6c8e045 -> i0e4g7d9f156
```

`notifications` stores recipient, optional request correlation, event key, kind,
channel, subject/body, delivery state, attempts/backoff, sent/read timestamps and a
bounded last error. Downgrade refuses when notification history exists.

## Verification

On checkpoint `69cd80b...`:

- **CI #90 / 34011134494: SUCCESS** — Ruff, clean SQLite migration, **144 backend
  tests**, **81% total statement coverage**, frontend TypeScript, ESLint, production
  build and executable frontend tests.
- **PostgreSQL #63 / 34011134498: SUCCESS** — clean PostgreSQL migration and retained
  M3/M4/M5 concurrency/integrity regression gates.
- **Browser #66 / 34011134496: SUCCESS** — production Docker Compose and Chromium
  through M2-M5, Phase 8 attachments and M6. The M6 step confirms an asynchronous
  email reached Mailpit and the employee notification center is readable/markable.

The initial M6 browser attempt exposed two startup issues and both were corrected:
the worker originally scanned before the notification migration existed, then it
inherited the API HTTP healthcheck. Compose now gates worker startup on API health
and overrides the worker healthcheck for Dramatiq.

## Local run

```powershell
git switch main
git pull --ff-only origin main
docker compose up -d --build --wait --wait-timeout 180
docker compose exec api alembic current
Start-Process "http://localhost:3000"
Start-Process "http://localhost:8025"
```

After generating an approval/change/resolution event, the bell shows the in-app item
and Mailpit receives the corresponding development email. Stop without deleting data:

```powershell
docker compose down
```

## Explicit boundaries

M6 does not claim a production email provider, push/mobile notifications, Teams or
Slack delivery, WebSocket/SSE realtime updates, notification preference management,
delivery analytics, or exactly-once external SMTP delivery. Mailpit is development
infrastructure only. Security/load/failure testing beyond the recorded gates remains
future hardening.

## Next

Phase 10 / M7 is the next vertical slice: schema-aware AI intake that classifies the
published request type, extracts editable values, asks for deterministic missing
required fields, and always requires human review before saving/submitting. AI must
not become the source of truth for authorization or approval routing.