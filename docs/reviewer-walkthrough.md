# Reviewer walkthrough

The fastest review takes about three minutes.

## 1. Product flow

1. Sign in as the demo admin.
2. Review open work, pending approvals, SLA compliance, AI coverage, and automation health.
3. Create a request titled `VPN access for new finance analyst`.
4. Describe that the analyst is blocked before onboarding.
5. Observe the AI category, priority, summary, confidence, and human approval state.

## 2. Grounded assistant

Ask:

```text
When should a request be marked urgent?
```

The answer should cite `Service Request Priority Policy v2.1`. The assistant must not
claim that it can approve work.

## 3. Engineering depth

- Open FastAPI Swagger at `http://localhost:8000/docs`.
- Inspect `backend/app/services/llm.py` for provider abstraction and fallback.
- Inspect `backend/app/services/retrieval.py` for transparent citation retrieval.
- Inspect `backend/tests/test_api.py` for authorization, workflow, AI, and integration tests.
- Inspect `integrations/power-platform` for the custom connector and low-code extension.

## 4. Suggested demo recording

- 0:00-0:20: business problem and dashboard.
- 0:20-0:55: submit a request and explain AI triage.
- 0:55-1:20: approve it as a human and show audit history.
- 1:20-1:45: ask a grounded policy question.
- 1:45-2:10: show automation metrics and Power Platform integration.
- 2:10-2:30: show tests, Docker, and the architecture diagram.

State clearly that sample data is synthetic and production hardening items are documented.
