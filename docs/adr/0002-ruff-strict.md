# ADR 0002: Use ruff for linting and formatting

- Status: accepted
- Date: 2026-06-14

## Context

Need unified lint + format tool. Options: black + flake8 + isort + pylint (4 tools), ruff (1 tool).

## Decision

Use ruff for both linting and formatting (replaces black, flake8, isort, pylint).

## Consequences

Positive: Single tool, fast (Rust), extensive rule set, auto-fix capable.
Negative: Newer tool, some pylint rules not yet implemented.
Neutral: Configuration in pyproject.toml.

## Alternatives Considered

- black + flake8 + isort + pylint: Established but 4 separate tools, slower, fragmented config.
- pylint standalone: Deep analysis but slow, no formatting.
