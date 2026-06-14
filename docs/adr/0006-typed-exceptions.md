# ADR 0006: Typed exception hierarchy

- Status: accepted
- Date: 2026-06-14

## Context

Framework needs typed errors for structured logging, failure catalog (P3), and user guidance.

## Decision

ShenbiError base class with FrameworkError/GateError/ScoringError/IntegrityError branches. Each error carries context dict for serialization.

## Consequences

Positive: Typed catch blocks, to_dict() for logging/catalog, ErrorGuidance for user messages.
Negative: More classes to maintain.
Neutral: Follows Python exception convention.

## Alternatives Considered

- String-based errors: Simple but no type safety, hard to catch specific errors.
- Result types (monadic): Elegant but unusual in Python ecosystem.
