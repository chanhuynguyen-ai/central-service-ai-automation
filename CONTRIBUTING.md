# Contributing

## Development workflow

1. Create a focused branch from `main`.
2. Keep business rules in services rather than route functions.
3. Add or update tests for authorization, lifecycle, retrieval, or integration changes.
4. Run backend lint/tests and frontend typecheck/lint/build.
5. Update architecture or security documentation when a boundary changes.

## Commit style

Use short conventional commits, for example:

```text
feat(ai): add provider timeout fallback
fix(auth): prevent employee cross-request access
docs(power-platform): document connector import
test(workflow): cover rejected approval branch
```

## Pull request checklist

- [ ] Scope and business impact are explained.
- [ ] Authorization behavior is unchanged or tested.
- [ ] AI output is validated and has a safe fallback.
- [ ] Synthetic data is used in examples and tests.
- [ ] No secret, token, employee data, or generated database is committed.
- [ ] Relevant docs and UAT scenarios are updated.
