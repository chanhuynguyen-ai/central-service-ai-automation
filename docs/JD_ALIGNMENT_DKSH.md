# DKSH AI & Automation Intern - Project Alignment

This document maps CentralOps AI to the internship job description supplied with the project.
It separates repository evidence from work that still needs real Microsoft-tenant or stakeholder evidence.

## Positioning

CentralOps AI should serve two goals in parallel:

1. **Interview proof for an AI & Automation internship:** demonstrate Power Platform awareness,
   data handling, testing/UAT, documentation, process automation, monitoring, and AI POC skills.
2. **Long-term AI Engineer portfolio value:** demonstrate a reliable backend, deterministic workflow
   engine, LLM/RAG engineering, evaluation, security, observability, and production-oriented deployment.

The project should never become a shallow collection of screenshots. The FastAPI/PostgreSQL core
remains the source of truth; Power Platform is an additional enterprise channel.

## JD coverage matrix

| JD responsibility / requirement | Current evidence | Status | Next evidence to build |
| --- | --- | --- | --- |
| Power Apps | Canvas App formulas + custom connector contract | PARTIAL | Import into a real/dev tenant and capture tested form + request-detail flow |
| Power Automate | Approval flow specification + secured decision endpoint | PARTIAL | Build/import flow, run approval, capture run history and failure branch |
| Power BI | Analytics feed + DAX model guide | PARTIAL | Build report/dashboard against live API feed and capture screenshots/video |
| Copilot Studio | Architecture is compatible with an API-backed assistant | MISSING | Optional later: small Copilot Studio POC calling policy/request APIs |
| Data collection/retrieval | SQLAlchemy/PostgreSQL API and analytics feed | PARTIAL | Add explicit ingestion/data-quality pipeline with validation report |
| Data cleansing/basic analysis | Synthetic CSV + service KPIs | PARTIAL | Add repeatable cleaning script/notebook and before/after data quality metrics |
| SQL/data management | Relational persistence and aggregate queries | PARTIAL | Strengthen schema, migrations, indexed queries, explain query choices in interview |
| Excel familiarity | Not demonstrated in source | MISSING | Optional export/import or reconciliation exercise; do not force Excel into core architecture |
| Solution testing | Backend tests, frontend checks, CI | DONE for POC | Add workflow/concurrency/security tests as core engine is built |
| UAT | Prepared UAT plan | PARTIAL | Execute with a real tester and store signed result/evidence if available |
| Project documentation | Architecture, security, reviewer guide, source-of-truth docs | DONE | Keep implementation status honest and current |
| Process flows | Mermaid architecture/lifecycle + Power Automate spec | DONE for POC | Add BPM/process map for final workflow engine |
| Training materials | User guide exists | PARTIAL | Add short operator/admin quick-start and Power Platform setup walkthrough |
| Stakeholder requirements | No real meeting evidence | CANNOT VERIFY | Use requirements + meeting-note templates during a real mock/reviewer session |
| AI / GenAI POC | Provider abstraction, triage, grounded assistant | PARTIAL | Add structured extraction, eval dataset, RAG ingestion, safety/evaluation report |
| AI Agents | No agentic execution by design | MISSING / optional | Later add a constrained tool-using service copilot; keep approval human-owned |
| Automation monitoring | AutomationRun + KPI endpoint/dashboard | PARTIAL | Record failures/retries, queue metrics, latency percentiles, improvement actions |
| Process improvement | Metrics exist but no closed-loop improvement record | PARTIAL | Add a small improvement case study using baseline -> change -> measured outcome |

## Interview-safe claims today

Use claims such as:

- Built a FastAPI/React POC for employee service-request automation with human approval controls.
- Implemented LLM-assisted triage with deterministic fallback and policy-grounded responses.
- Prepared a Power Platform custom connector, Power Apps formulas, Power Automate flow specification,
  and a Power BI analytics feed/model.
- Wrote automated tests, CI checks, documentation, a UAT plan, and responsible-AI guidance.

Do **not** claim the Power Platform solution has been deployed in a Microsoft tenant until it has
actually been imported and tested there. Do **not** claim to have led business UAT or stakeholder
meetings unless that happened.

## Dual-track execution plan

### Track A - Core product / AI Engineer depth

1. Versioned request types and dynamic forms.
2. Deterministic workflow engine and manager resolver.
3. Approval task model, audit timeline, service fulfillment.
4. Worker/notifications/attachments.
5. Structured AI intake + evaluation.
6. Policy ingestion + pgvector/hybrid retrieval + offline evaluation.
7. Observability, security hardening, deployment.

### Track B - DKSH interview evidence

Run in parallel without blocking Track A:

1. Import and test the custom connector in Power Platform when a tenant is available.
2. Build a small Canvas App that submits and reads requests.
3. Build a human approval flow in Power Automate and document run history.
4. Build a Power BI dashboard over the analytics feed.
5. Execute the UAT plan with a reviewer and record findings/action items.
6. Add a small data-cleaning exercise and a measurable process-improvement case study.

Track B should consume the same backend APIs; it should not duplicate business rules in Power Apps
or Power Automate.
