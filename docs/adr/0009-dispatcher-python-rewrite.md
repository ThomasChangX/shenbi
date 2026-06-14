# ADR 0009: Python rewrite of dispatch-subagent.sh

- Status: accepted
- Date: 2026-06-14

## Context

dispatch-subagent.sh (247 lines shell) needs type safety, testability, and Python integration.

## Decision

Rewrite dispatcher logic in Python (tests/dispatcher/). Shell wrapper stays as 10-line shim for backward compatibility.

## Consequences

Positive: Type-safe, testable, integrates with structlog + typed exceptions.
Negative: Shell users need to call Python CLI indirectly.
Neutral: PR-13 (P-1.D) applies the rewrite.

## Alternatives Considered

- Keep shell + patch: Fragile, no type safety, hard to test.
- Rewrite in Rust: Over-engineering for CLI dispatcher.
