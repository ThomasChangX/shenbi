# ADR 0008: Strangler fig for validate-gate.py modularization

- Status: accepted
- Date: 2026-06-14

## Context

validate-gate.py is 3900+ lines monolithic. Need to split without behavior change.

## Decision

Use strangler fig pattern: physical split by gate (g0.py, g1.py, ... g4/ subdir) preserving behavior. CLI entry stays as shim.

## Consequences

Positive: Each gate independently testable, revertable. No behavior risk.
Negative: Temporary ignore_errors overrides until PR-12 adds type hints.
Neutral: PR-12 (P-1.D) applies the split.

## Alternatives Considered

- Full rewrite: Risky, couples to P0 schemas.
- Status quo: Unmaintainable at 3900 lines.
