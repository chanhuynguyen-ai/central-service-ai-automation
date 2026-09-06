# M6 - Async notifications

Implementation branch: `feat/async-notifications`.

Phase 9 will add a durable notification intent in PostgreSQL, asynchronous Redis-backed worker delivery, in-app notification read state, a development email adapter, and retry behavior that cannot repeat the underlying request/approval/fulfillment business action.

This document is intentionally a delivery placeholder until the implementation and CI gates are complete. Do not treat M6 as verified before the branch tests, PostgreSQL worker checks, and browser smoke are green.
