# ADR 0004: Use pytest with 7 plugins

- Status: accepted
- Date: 2026-06-14

## Context

Need test framework supporting unit, integration, property-based, and benchmark tests.

## Decision

Use pytest with pytest-cov, pytest-xdist, pytest-asyncio, pytest-timeout, pytest-benchmark, hypothesis, pytest-ordering.

## Consequences

Positive: Comprehensive test pyramid, parallel execution, coverage enforcement, property-based testing.
Negative: Many plugins = more config surface.
Neutral: pytest is Python ecosystem standard.

## Alternatives Considered

- unittest only: Standard library but limited (no fixtures, no parametrization, no coverage).
- nose2: Unmaintained.
