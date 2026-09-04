# UI/UX Design Guide

## 1. Design direction

Use a **calm enterprise SaaS** style: modern, clean, trustworthy, and information-dense without looking like an old admin panel.

Keywords:

- professional,
- calm,
- structured,
- transparent,
- efficient,
- accessible,
- AI-assisted but not “sci-fi.”

Avoid excessive gradients, neon effects, floating glass cards, and animated chatbot gimmicks. The main product value is confidence and workflow clarity.

---

## 2. Visual identity

### Primary palette

| Token | Hex | Usage |
|---|---:|---|
| Primary 600 | `#2563EB` | Primary CTA, active navigation, links |
| Primary 700 | `#1D4ED8` | Hover/pressed primary |
| Primary 50 | `#EFF6FF` | Selected rows, subtle primary background |
| Accent 500 | `#14B8A6` | AI/automation accent, secondary highlights |
| Accent 50 | `#F0FDFA` | AI assistant surfaces |

### Neutral palette

| Token | Hex | Usage |
|---|---:|---|
| Slate 950 | `#020617` | Strong dark text |
| Slate 900 | `#0F172A` | Main headings |
| Slate 700 | `#334155` | Body text |
| Slate 500 | `#64748B` | Secondary/meta text |
| Slate 300 | `#CBD5E1` | Borders |
| Slate 200 | `#E2E8F0` | Dividers/subtle surfaces |
| Slate 100 | `#F1F5F9` | Background sections |
| Slate 50 | `#F8FAFC` | App background |
| White | `#FFFFFF` | Cards/content surfaces |

### Semantic palette

| State | Hex | Usage |
|---|---:|---|
| Success | `#16A34A` | Approved, resolved, healthy SLA |
| Warning | `#F59E0B` | Waiting, nearing SLA, attention |
| Danger | `#DC2626` | Rejected, overdue, destructive action |
| Info | `#0284C7` | Neutral informational states |
| Purple | `#7C3AED` | Optional workflow/configuration accent |

Use color plus icon/text; never communicate status by color alone.

---

## 3. Typography

Recommended family:

- **Inter** for the main application UI, or
- **Geist Sans** if the frontend template already uses it.

Use only one primary sans-serif family in MVP.

### Type scale

| Style | Size | Weight | Usage |
|---|---:|---:|---|
| Display | 32 px | 700 | Rare dashboard hero/title |
| H1 | 28 px | 700 | Page title |
| H2 | 22 px | 650/700 | Major section |
| H3 | 18 px | 600 | Card/section title |
| Body | 14–16 px | 400 | Main content |
| Label | 13–14 px | 500/600 | Form/table labels |
| Meta | 12–13 px | 400/500 | Timestamp, helper text |

Line height should favor readability, especially in request descriptions and policy text.

---

## 4. Spacing and geometry

Use an 8-point spacing system:

```text
4, 8, 12, 16, 24, 32, 40, 48, 64
```

Recommended:

- card radius: 12 px,
- input radius: 8–10 px,
- button radius: 8–10 px,
- border: 1 px subtle slate,
- shadow: minimal; use borders and background hierarchy before shadows.

---

## 5. Global layout

Desktop application shell:

```text
┌──────────────────────────────────────────────────────────────┐
│ Top bar: breadcrumb/search/notifications/profile            │
├───────────────┬──────────────────────────────────────────────┤
│ Sidebar       │ Page title + actions                         │
│               │                                              │
│ Home          │ Main content                                 │
│ Requests      │                                              │
│ Approvals     │                                              │
│ Service Desk  │                                              │
│ Knowledge     │                                              │
│ Analytics     │                                              │
│ Admin         │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

### Sidebar

- 240–264 px expanded.
- Optional collapsible mode.
- Role-aware items.
- Badge pending approval count.
- Current section clearly highlighted.

### Main content

- Max practical content width around 1440 px.
- 24–32 px page padding desktop.
- Dense tables can use more width.

---

## 6. Dashboard design

### Employee dashboard

Top section:

```text
Good morning, Huy
What do you need help with today?
[ Describe a request...                           ] [Ask AI]
```

Below:

```text
[Open Requests] [Waiting for Me] [Completed This Month]

Recent requests
┌──────────┬───────────────┬─────────────┬──────────────┐
│ ID       │ Request       │ Status      │ Updated      │
└──────────┴───────────────┴─────────────┴──────────────┘

Common services
[IT Access] [Equipment] [HR Letter] [Reimbursement]
```

AI entry should be prominent but should not hide the standard catalog.

---

## 7. New request experience

Offer two clear paths:

### A. Ask AI

Large input:

> “Tell us what you need. You can write naturally.”

After classification:

```text
I think this is: IT > Software Access          92% confidence
[Use this request type] [See alternatives]
```

Then show extracted fields inside normal form controls so the user understands and can edit them.

### B. Browse services

Search + category cards:

```text
Search services...

IT        Human Resources        Finance       Facilities
```

Do not force AI for users who already know the correct request type.

---

## 8. Dynamic form UI

Form structure:

- Request title/context at top.
- Logical sections.
- Required marker `*`.
- Inline validation.
- Explanatory helper text only where useful.
- Attachment drop zone.
- Sticky summary/submit panel on large screens.

Example:

```text
Laptop Replacement

Reason for replacement *
[................................................]

Business impact *
[................................................]

Preferred device class *
[ Standard office v ]

Cost center *
[ ENG-001          ]

Attachments
[ Drop files here or browse ]

                     [Save draft] [Review request]
```

Before final submission, use a **Review** step rather than sending immediately.

---

## 9. Request detail page

Recommended desktop layout:

```text
Request #REQ-2026-00124                         [Pending approval]
Laptop replacement for client work

┌─────────────────────────────────┬────────────────────────────┐
│ Request details                 │ Approval progress          │
│ Requester                       │ ✓ Submitted                │
│ Department                      │ ● Manager approval         │
│ Form answers                    │ ○ IT approval              │
│ Attachments                     │ ○ Fulfillment              │
│                                 │                            │
│ Comments                        │ SLA / due date             │
└─────────────────────────────────┴────────────────────────────┘

Activity timeline
```

The current actor/action should be immediately obvious:

> **Waiting for: Nguyen Van A — Direct Manager**

or

> **Action needed from you: provide the missing cost center.**

---

## 10. Status presentation

Use status chips with icon + text.

Examples:

- Draft — neutral gray.
- Pending approval — blue.
- Changes requested — amber.
- Approved — green.
- Rejected — red.
- In progress — blue/teal.
- Waiting for requester — amber.
- Resolved — green.
- Cancelled — gray.

Never use vague labels such as “Processing” for every state.

---

## 11. Approval inbox

Approvers need speed.

Use table/list with filters:

```text
Pending approvals (8)
[All] [Urgent] [Overdue]                    Search...

Requester | Request | Submitted | Age | Amount/Key field | Action
```

Click opens a right-side detail panel for quick review; full page available for complex requests.

Decision area:

```text
AI summary
“Employee requests replacement because repeated shutdowns affect client meetings...”

[Approve] [Request changes] [Reject]
```

Reject/request-changes should open a reason field.

---

## 12. Service desk UI

Use a queue-first layout.

Columns/filters:

- status,
- priority,
- SLA,
- service team,
- assignee,
- request type,
- requester department.

Optional board view later:

```text
Unassigned | Assigned | In Progress | Waiting | Resolved
```

Table view should remain the default for operational scalability.

---

## 13. Admin UI

### Request type editor

Tabs:

1. General.
2. Form fields.
3. Workflow.
4. SLA.
5. Notifications.
6. Permissions.
7. Version/history.

### Workflow editor

For MVP, use a structured step list rather than building a complex node canvas.

```text
Step 1 — Direct Manager
Mode: ALL
Due in: 24h

Step 2 — Department Head
Condition: estimated_cost >= 1000

Step 3 — IT Service Lead
```

A visual flow builder can be added later.

---

## 14. AI visual language

AI should have a distinct but subtle identity:

- teal accent,
- sparkle/assistant icon,
- “AI suggestion” label,
- confidence or “review recommended” text when applicable.

Never make AI-generated content visually indistinguishable from verified system data.

Example:

```text
AI suggestion
Request type: Software Access
Confidence: High

Extracted values are suggestions. Review before submitting.
```

---

## 15. Empty states

Good empty states explain the next action.

Bad:

> No data.

Better:

> You have no open requests. Create a request to ask IT, HR, Finance, or Facilities for help.
> [Create request]

---

## 16. Loading states

- Skeleton rows for tables.
- Button spinner for short actions.
- AI streaming/progress message for long generation.
- Never block the whole screen if only one panel is loading.

---

## 17. Error states

Errors should tell the user what happened and what they can do.

Examples:

- “The request was not submitted. Your draft is still saved.”
- “This approval has already been completed by another approver.”
- “AI assistance is temporarily unavailable. You can continue using the standard form.”

AI failure must not make the core request system unusable.

---

## 18. Confirmation patterns

Require confirmation for:

- final request submission if consequences are significant,
- rejection,
- cancellation,
- destructive admin actions,
- workflow publication.

Do not show confirmation modals for trivial reversible actions.

---

## 19. Responsive behavior

### Desktop

Primary work environment; show table/detail split views.

### Tablet

Collapse sidebar; preserve full request/approval actions.

### Mobile

Prioritize:

- notification view,
- my requests,
- request detail,
- approve/reject,
- simple new request.

Admin workflow/form configuration can remain desktop-first.

---

## 20. Accessibility

Target WCAG 2.1 AA or newer applicable guidance during implementation.

Minimum practices:

- keyboard navigation,
- visible focus states,
- semantic labels,
- ARIA only where native HTML is insufficient,
- sufficient contrast,
- errors linked to fields,
- touch targets large enough for mobile,
- status meaning not dependent on color,
- reduced-motion preference respected.

---

## 21. UX principles for approval systems

1. Always show **who must act next**.
2. Always show **why a workflow step exists** when policy allows.
3. Separate **request data**, **approval decisions**, and **service work** visually.
4. Preserve historical actions; do not silently overwrite.
5. Make destructive decisions deliberate.
6. Minimize repeated entry by pre-filling trustworthy known data.
7. Keep AI suggestions editable and clearly labeled.
8. Preserve a manual path when AI is unavailable.

---

## 22. Design token starter

```css
:root {
  --background: #F8FAFC;
  --surface: #FFFFFF;
  --text-primary: #0F172A;
  --text-secondary: #64748B;
  --border: #E2E8F0;

  --primary: #2563EB;
  --primary-hover: #1D4ED8;
  --primary-soft: #EFF6FF;

  --ai: #14B8A6;
  --ai-soft: #F0FDFA;

  --success: #16A34A;
  --warning: #F59E0B;
  --danger: #DC2626;

  --radius-card: 12px;
  --radius-control: 9px;
}
```

These tokens are a starting point; final implementation must verify actual contrast ratios for specific text/background combinations.
