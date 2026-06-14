# ADR 0003: Dual type checking with mypy + basedpyright

- Status: accepted
- Date: 2026-06-14

## Context

Single type checker may miss errors. Need comprehensive coverage.

## Decision

Use mypy --strict AND basedpyright (pure-Python pyright fork) for dual type checking.

## Consequences

Positive: Catches more type errors, complementary strengths (mypy for inference, pyright for correctness).
Negative: Occasional conflicting reports, two configs to maintain.
Neutral: basedpyright avoids Node.js dependency (vs. pyright).

## Alternatives Considered

- mypy only: Single checker, may miss pyright-specific findings.
- pyright only: Requires Node.js runtime.
- pyre: Facebook's checker, less ecosystem support.
