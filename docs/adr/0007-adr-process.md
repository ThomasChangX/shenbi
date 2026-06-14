# ADR 0007: Use ADR process for architectural decisions

- Status: accepted
- Date: 2026-06-14

## Context

Need traceable decision-making for framework architecture.

## Decision

Use Michael Nygard's ADR format (Context/Decision/Consequences/Alternatives) stored in docs/adr/.

## Consequences

Positive: Decisions are traceable, reviewable, reversible (superseded status).
Negative: Overhead of writing ADRs for each decision.
Neutral: Could be README instead of numbered ADR; chose numbered for searchability.

## Alternatives Considered

- README only: Simple but no individual decision tracking.
- GitHub Issues: Decisions mixed with bug reports.
