# Repository Guidelines

## Project Structure & Module Organization

This Python 3.13 CLI package heals broken Playwright E2E selectors. Core code lives in
`app/`: `cli.py` is the entry point, `graph.py` wires the LangGraph flow, `nodes/` contains
repair-loop nodes, `preprocess/` extracts context from logs and diffs, `verify/` checks
selectors, and `prompts/` holds LLM prompts. Tests live in `tests/` with `test_*.py` files.
Docs are in `docs/`, CI/action examples are in `ci/` and `action.yml`, and `examples/` is
a runnable Playwright fixture.

## Build, Test, and Development Commands

Use `uv` and the `Makefile` targets:

- `make install` installs runtime and dev dependencies with `uv sync --extra dev`.
- `make lint` runs `ruff check .`.
- `make format` applies `ruff format .`.
- `make typecheck` runs `pyright`.
- `make check` runs linting plus type checking.
- `make test` runs `pytest`.
- `make run ARGS="tests/example.spec.ts --log playwright.log"` invokes `e2e-healer`.

For the demo, run `cd examples && npm install && npx playwright install chromium`.

## Coding Style & Naming Conventions

Follow `ruff` with a 100-character line length and Python 3.13 syntax. Use typed
signatures, top-level imports, lowercase_underscore filenames, and Pydantic models or
`TypedDict` for structured data. Use `structlog` event names with kwargs, not f-string
messages. Use `rich` for CLI output and `tenacity` for retries.

## Testing Guidelines

Use `pytest`; tests are collected only from `tests/` per `pyproject.toml`. Name files
`test_<module>.py` and test behavior near the module boundary. Add tests for changes to
parsing, graph routing, schemas, patching, selector verification, or CLI behavior. Run
`make test` before opening a PR, and run `make check` for lint and types.

## Commit & Pull Request Guidelines

Recent commits use short conventional-style subjects such as `fix: ...`, `feat: ...`,
`docs: ...`, `ci: ...`, and `release: ...`. Keep commits focused and imperative. PRs
should describe the change, list verification (`make check`, `make test`, demo steps),
link issues when available, and include screenshots or logs for visible CLI, CI, or demo
behavior.

## Security & Agent-Specific Notes

Never commit `.env` or API keys; use `.env.example` for configuration names. Preserve the
core guardrail: patch generation may fix selectors and wait conditions only, never
assertions, test intent, or business logic. Keep repair logic in the CLI core; CI wrappers
should only orchestrate calls to `e2e-healer`. For sandbox boundaries, follow
`docs/sandbox.md`: read logs, diffs, snapshots, and source context; write only the failing
test target and known temporary artifacts unless the user explicitly requests broader
access.

## Codex Workflow

Repository-specific Codex defaults and the short verification checklist live in
`.codex/`. Before making a change, inspect the relevant module and nearby tests. Keep the
change scoped, run the smallest relevant test first, then run `make check` and `make test`
when the environment permits. Report any checks not run and why.
