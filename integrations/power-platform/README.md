# Microsoft Power Platform integration

CentralOps exposes a small, API-key-protected surface for Power Apps, Power Automate,
and Power BI. The integration remains optional: the core product runs with React and
FastAPI, while Microsoft 365 teams can use their existing low-code tools as additional
channels.

## Included assets

- `custom-connector.openapi.yaml`: importable API definition for a Power Platform custom connector.
- `power-automate-flow-spec.json`: environment-neutral workflow specification.
- `power-apps-formulas.md`: Canvas App formulas and field mapping.
- `power-bi-model.md`: suggested query and KPI model.

## Integration flow

1. Power Apps submits an employee request through the custom connector.
2. FastAPI validates the employee, runs AI triage, creates an auditable request, and returns its reference.
3. Power Automate starts a human approval and writes the decision through the normal secured API.
4. Power BI reads the flattened analytics feed for service and SLA reporting.

## Configure

1. Run the API and confirm `GET /health` returns `status: ok`.
2. Replace `localhost:8000` in the OpenAPI file with the HTTPS hostname reachable by Power Platform.
3. Import the OpenAPI file as a custom connector.
4. Set the connector API key to the backend `INTEGRATION_API_KEY` value.
5. Test `SubmitServiceRequest` with `employee@centralops.demo` before wiring the Canvas App.

Do not use the checked-in development key outside a local demo. Use a secret store and rotate
the integration key in every shared environment.
