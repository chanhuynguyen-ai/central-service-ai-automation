# M7 — AI-assisted Request Intake

## Purpose

M7 reduces request-entry effort without making AI authoritative. Employees can describe
a need in natural language, receive a suggestion constrained to the published service
catalog, review extracted values and missing information, then continue through the
same normal draft/save/submit path as every other request.

## Safety and correctness boundaries

AI may:

- classify free text into an active published request type,
- propose schema-known field values,
- expose confidence and alternatives,
- identify missing required fields,
- present clarification prompts.

AI may not:

- authorize the employee,
- publish catalog/workflow configuration,
- choose final approval authority,
- bypass deterministic routing,
- silently change a human-selected request type,
- save or submit a request automatically,
- approve a request.

All extracted values are revalidated using the normal dynamic-form validator. Required
fields and clarification prompts are derived from the immutable published form schema.

## API

### `POST /api/v1/ai/intake/classify`

Input:

```json
{"text":"My laptop keeps failing and I need a replacement."}
```

Output includes:

- selected request-type code/version,
- confidence,
- alternatives,
- provider/model metadata,
- `needs_human_confirmation=true`.

Only active `PUBLISHED` catalog entries are eligible.

### `POST /api/v1/ai/intake/draft`

Input may optionally contain a request type explicitly selected by the employee.

Output adds:

- `extracted_fields`,
- `missing_required_fields`,
- deterministic `clarifications`,
- rejected/invalid field issue codes.

The response remains a suggestion only. No request row is created by this endpoint.

## Provider behavior

The existing provider modes are reused:

- `mock` — deterministic catalog ranker/extractor for repeatable tests and demos,
- `ollama` — local external model adapter,
- `openai_compatible` — compatible hosted/self-hosted endpoint.

External model JSON is validated with Pydantic. An invalid response, unpublished type,
network failure or extraction attempt that changes a human-selected type falls back to
the deterministic path rather than bypassing governance.

## User experience

```text
Employee opens Service catalog
  -> describes need
  -> receives suggested published service + confidence/alternatives
  -> sees prefilled and still-required fields
  -> sees schema-derived clarification prompts
  -> selects Review this draft
  -> normal dynamic form opens with editable values
  -> employee reviews/changes data
  -> explicitly saves draft
  -> explicitly submits through the existing human approval workflow
```

## Evaluation

`backend/evals/ai_intake_cases.json` contains 30 deterministic evaluation utterances
across three representative demo services:

- laptop replacement,
- software access,
- expense reimbursement.

`backend/tests/test_ai_intake_eval.py` tracks:

- top-1 classification accuracy,
- top-2 classification accuracy,
- correctness of explicitly expected extracted fields,
- deterministic missing-required-field correctness.

Quality gates currently require:

- at least 30 cases,
- top-1 >= 90%,
- top-2 >= 95%,
- expected-field extraction >= 90%,
- missing-field correctness = 100%.

These metrics validate the deterministic test/demo path. They are not a claim about a
production LLM provider or real enterprise distribution. Production provider evaluation
must additionally cover privacy/redaction, latency, cost, multilingual requests and a
representative held-out dataset.

## Browser verification

`scripts/m7_browser_smoke.py` exercises production Docker + Chromium using
`LLM_PROVIDER=mock`:

```text
free-text request
  -> AI catalog suggestion
  -> advisory/human-review indicators
  -> schema-bound prefill
  -> Review this draft
  -> normal editable dynamic form
  -> explicit Save draft
```

The test intentionally stops before submission to demonstrate that AI does not invoke
the approval workflow autonomously.

## Database

M7 adds no database migration. It reuses published request-type versions and existing
automation-run telemetry.

## Known limits

- No multilingual evaluation corpus yet.
- No production-model benchmark yet.
- No prompt-injection/red-team benchmark yet.
- No AI usage/cost dashboard yet.
- Clarification prompts are deterministic schema prompts rather than a conversational
  multi-turn state machine.
- Policy RAG remains Phase 11/M8 and is intentionally separate from request intake.
