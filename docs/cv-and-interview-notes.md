# CV and interview notes

Use these statements only after running the project and being able to explain each design.

## CV-ready project entry

**CentralOps AI - Employee Request & Approval Automation**  
*AI/LLM & Automation Engineer | 2026*

- Built a full-stack service automation platform using Python, FastAPI, React,
  PostgreSQL, Docker, and role-based JWT authentication.
- Implemented LLM-assisted request classification, priority recommendation, summarization,
  provider routing, latency monitoring, and deterministic fallback for reliable offline demos.
- Developed a grounded policy assistant with retrieval citations and human-in-the-loop
  approval controls; validated authorization, workflow, AI, and Power Platform paths with tests.
- Exposed secured custom-connector endpoints for Power Apps and Power Automate and an
  analytics feed for Power BI, with process documentation and a prepared UAT plan.

## Honest interview framing

- Say `prepared a UAT plan`, not `led UAT`, unless real business users execute it.
- Say `Power Platform integration specification and custom connector`, not `deployed an
  enterprise Power Platform solution`, unless it is imported and tested in a tenant.
- Say `synthetic operational dataset`, not `company data`.
- Say `deterministic fallback`, not `LLM`, when demonstrating mock mode.
- Discuss the production hardening checklist before a reviewer has to ask.

## Likely questions

**Why human approval?**  
The model handles triage and retrieval, where recommendations are reviewable. Approval is an
accountability decision and remains with an authorized person.

**Why support several providers?**  
It separates business logic from model hosting, supports local-data constraints, and keeps the
demo usable without paid credentials.

**Why lexical retrieval instead of embeddings?**  
The starter knowledge base is small. A transparent baseline makes citations deterministic and
testable. Hybrid retrieval and reranking are documented as the next scale step.

**What did you test?**  
Authentication, validation, employee isolation, approver workflow, grounded citations,
analytics, and Power Platform intake.
