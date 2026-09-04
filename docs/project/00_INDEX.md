# Central Service AI Automation — Documentation Index

**Project:** Central Service AI Automation – Employee Request & Approval System  
**Purpose:** Internal enterprise service portal that centralizes employee requests, automates approval workflows, and uses AI to reduce manual triage, routing, clarification, and policy lookup.

## Document set

1. [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) — Project purpose, capabilities, scope, business value, architecture at a glance, and long-term direction.
2. [`02_PRODUCT_SPECIFICATION.md`](02_PRODUCT_SPECIFICATION.md) — Product concept, user personas, feature set, MVP scope, user stories, business rules, success metrics, and future product direction.
3. [`03_TECHNICAL_ARCHITECTURE.md`](03_TECHNICAL_ARCHITECTURE.md) — Technical decisions, frontend/backend stack, AI architecture, APIs, security, deployment, observability, testing, and architecture trade-offs.
4. [`04_APPLICATION_FLOW.md`](04_APPLICATION_FLOW.md) — Detailed end-to-end application flow, state transitions, approval logic, exception flows, and Mermaid diagrams.
5. [`05_UI_UX_GUIDE.md`](05_UI_UX_GUIDE.md) — Visual system, color palette, typography, layout, components, interaction patterns, page specifications, responsive design, and accessibility.
6. [`06_BACKEND_DATABASE_AUTH.md`](06_BACKEND_DATABASE_AUTH.md) — Backend folder structure, modules, data model, database schema, authentication/authorization, relationships, storage, audit logs, and API boundaries.
7. [`07_IMPLEMENTATION_PLAN.md`](07_IMPLEMENTATION_PLAN.md) — Recommended build order from repository setup to production deployment, milestones, acceptance criteria, tests, demo checklist, and optional extensions.

## Recommended repository layout

```text
central-service-ai/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI backend
├── services/
│   ├── worker/              # Background jobs
│   └── ai/                  # Optional isolated AI service later
├── packages/
│   ├── ui/                  # Shared UI components/design tokens
│   ├── contracts/           # API/OpenAPI-generated types
│   └── config/              # Shared lint/format configuration
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── terraform/           # Optional production IaC
├── docs/
│   └── ...this document set
├── scripts/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Suggested MVP demo scenario

A strong recruiter/demo flow is:

> Employee logs in → describes “I need a new laptop because my current device is failing” in natural language → AI detects **IT Equipment Request**, extracts urgency and justification, asks for one missing field → employee reviews and submits → system resolves the approval chain from department and request type → manager approves → IT agent receives the task → employee sees live status/history → task is completed → all transitions appear in audit log and analytics.

This scenario demonstrates **product thinking, backend design, workflow automation, AI integration, database modeling, RBAC, realtime notifications, and production-oriented engineering** in one project.
