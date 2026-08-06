# Codex workspace setup

This directory contains repository-scoped Codex defaults. Codex loads
`.codex/config.toml` only after the repository is marked as trusted.

## Defaults

- Ask before an action needs elevated permission.
- Allow writes inside this repository only.
- Keep web search in cached mode and disable shell network access by default.
- Leave personal settings such as model, provider, authentication, and notifications in
  `~/.codex/config.toml`; do not commit them here.

## Standard verification

Choose the smallest relevant check while iterating, then run the complete checks before
hand-off when the environment allows it.

```bash
make lint
make typecheck
make test
```

`make check` combines linting and type checking. Use `make run ARGS="..."` only with a
known failing Playwright target and its log or diff.

## Repair guardrail

For E2E repair work, edits may change selectors or wait conditions only. Never change
assertions, test intent, or application business logic to make a test pass. Follow
`docs/sandbox.md` for the target-file and command boundaries.
