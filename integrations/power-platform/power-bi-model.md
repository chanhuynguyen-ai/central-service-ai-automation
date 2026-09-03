# Power BI model

Connect Power Query to:

```text
GET https://<api-host>/api/v1/integrations/power-platform/analytics-feed
Header: X-Integration-Key = <secret>
```

## Cleaning steps

1. Set `submitted_at`, `due_at`, and `completed_at` to Date/Time.
2. Replace null `completed_at` with the report refresh timestamp only in duration calculations.
3. Standardize category labels by replacing underscores with spaces.
4. Remove duplicate `reference` values.
5. Validate that `ai_confidence` is between 0 and 1.

## Recommended measures

```dax
Total Requests = COUNTROWS(ServiceRequests)

Open Requests =
CALCULATE(
    [Total Requests],
    ServiceRequests[status] IN {"pending_approval", "in_progress"}
)

SLA Compliance % =
DIVIDE(
    CALCULATE([Total Requests], ServiceRequests[within_sla] = TRUE()),
    [Total Requests]
)

AI Triage Coverage % =
DIVIDE(
    CALCULATE([Total Requests], NOT ISBLANK(ServiceRequests[ai_confidence])),
    [Total Requests]
)
```

Display total, open, pending approval, SLA compliance, requests by category, requests by
department, and weekly volume. Treat AI confidence as a monitoring signal, not a business KPI.
