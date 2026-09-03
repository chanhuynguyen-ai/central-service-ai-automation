# UAT and functional test plan

This checklist is prepared for a business user to execute. The repository's automated
tests do not claim to replace user acceptance testing.

| ID | Business scenario | Expected result | Evidence |
| --- | --- | --- | --- |
| UAT-01 | Employee submits a complete IT request | Reference is created and request enters pending approval | UI + API response |
| UAT-02 | Employee omits required detail | Submission is blocked with a useful validation message | UI validation |
| UAT-03 | VPN/access wording is submitted | AI recommends access request and explains confidence | Request detail |
| UAT-04 | Business-critical outage is submitted | AI recommends urgent priority and two-hour SLA | Request detail |
| UAT-05 | Approver approves pending work | Status changes to in progress and decision is audited | Timeline/audit row |
| UAT-06 | Approver rejects with a comment | Status changes to rejected and comment is retained | Request detail |
| UAT-07 | Employee opens another user's request | API returns not found and does not disclose data | HTTP response |
| UAT-08 | User asks an SLA question | Assistant answers with policy citation and version | Assistant response |
| UAT-09 | External LLM is unavailable | Triage completes using recorded deterministic fallback | Automation run |
| UAT-10 | Power Apps connector submits a request | Same request and AI workflow are used as the React channel | API + connector test |
| UAT-11 | Manager opens analytics | Counts and SLA metrics reflect stored records | Dashboard/API comparison |
| UAT-12 | Invalid integration key is used | Integration endpoint returns 401 | HTTP response |

## Acceptance criteria

- All critical scenarios UAT-01 through UAT-08 pass.
- No employee can read or modify another employee's request.
- Every approval decision has a named human actor and timestamp.
- Every policy answer exposes at least one source when relevant content exists.
- Automation failure never removes the original employee request.

Record actual result, tester, date, status, screenshot, and defect reference when a
real stakeholder executes this plan.
