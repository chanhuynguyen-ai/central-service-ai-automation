# Security and responsible AI

## Implemented controls

- Passwords are hashed with Argon2 through `pwdlib`.
- User sessions use signed, expiring JWT access tokens.
- Employee, approver, and admin endpoints enforce role checks.
- Power Platform endpoints use a separate integration key.
- Requests, decisions, status changes, and AI triage results create audit events.
- Policy answers include retrieved source titles and versions.
- AI suggestions never execute an approval or access-grant decision.
- External LLM failure uses a deterministic fallback instead of silently dropping work.

## Data handling

The sample dataset contains synthetic people and requests. Before using real employee
data, define retention, access, export, and deletion policies. Remove unnecessary
personal data before sending any prompt to an external model.

## Production hardening checklist

- Replace demo credentials and all checked-in local defaults.
- Store JWT and integration secrets in a managed secret store.
- Replace local JWT login with organizational SSO/OIDC and MFA.
- Terminate TLS at a trusted reverse proxy.
- Rate-limit authentication, AI, and integration endpoints.
- Add refresh-token rotation or short-lived sessions.
- Add database migrations, backups, row-level access review, and retention jobs.
- Add prompt-injection evaluation and an approved policy-content publishing workflow.
- Send structured logs and traces to the organization's monitoring platform.
- Review dependency and container vulnerabilities in CI.

## Known limitations

The included lexical retriever is intentionally lightweight and transparent. For a
larger knowledge base, evaluate chunking, embeddings, hybrid retrieval, reranking,
document-level permissions, and offline retrieval-quality test sets.
