# Contributing to Shenbi

Thank you for your interest in contributing! This document covers setup, workflow, and standards.

## Development Environment

```bash
git clone https://github.com/ThomasChangX/shenbi.git
cd shenbi
uv sync --group dev
uv run pre-commit install
```

Requires: Python 3.11+, uv 0.5+ (PEP 735 dependency-groups), and [just](https://github.com/casey/just) (`brew install just` on macOS, `cargo install just` on other platforms, or see [the just releases](https://github.com/casey/just/releases) for prebuilt binaries).

## Daily Workflow

```bash
just check          # Run all CI checks locally (ruff, mypy, pytest)
just test           # Fast unit tests only
just fix            # Auto-fix lint + format
```

Use `just --list` to see all available commands.

## Pull Request Process

1. **Branch**: feature branches from `main`, short-lived (< 1 week).
2. **Commits**: follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add X`
   - `fix: correct Y`
   - `docs: update Z`
3. **PR title**: same format as commit messages.
4. **PR template**: fill all checkboxes in `.github/pull_request_template.md`.
5. **CI**: all checks must pass before merge.
6. **Squash-merge** preferred.

## Code Style

- **Linter**: ruff (configured in `pyproject.toml`).
- **Formatter**: ruff format.
- **Type checker**: mypy --strict + basedpyright --strict.
- **No `print()`** in framework code; use structlog.
- **No `ignore_errors`** in mypy overrides (target: zero overrides - the `[[tool.mypy.overrides]]` blocks currently in `pyproject.toml` are removed by Plan 1 and Plan 4).

## Architecture Decisions

Significant decisions are recorded as ADRs in `docs/adr/`. Use `docs/adr/0000-template.md` as starting point. Number sequentially (next available: check `docs/adr/` for highest number).

## No-Deferral Rule

**PRs that defer work to "future sessions" are rejected.** If work is in scope, do it; if not, file a GitHub issue and link it in the PR description.

This rule exists because P-1.E (this project's foundation) was created to clean up exactly this kind of accumulated deferral.

## Testing

- **Unit tests**: `tests/unit/` — direct imports, fast.
- **Integration tests**: `tests/integration/` — cross-module, may use subprocess.
- **Property tests**: `tests/property/` — Hypothesis-based.
- **Benchmark tests**: `tests/benchmark/` - pytest-benchmark performance regression tests.

Target density: 0.10 tests/LOC (1 test per 10 framework LOC).

## Skills Are Not Pip-Installable

The Shenbi wheel contains only `src/shenbi/` (framework runtime). Skills under `skills/` are repo assets, not installable. Users needing skills should `git clone`, not `pip install`.

## Questions?

Open a GitHub Discussion.
