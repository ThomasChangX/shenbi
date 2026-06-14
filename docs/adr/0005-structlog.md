# ADR 0005: Use structlog for structured logging

- Status: accepted
- Date: 2026-06-14

## Context

Need structured logging for CI aggregation and debugging. Options: stdlib logging, structlog, loguru.

## Decision

Use structlog with JSON renderer (production) + Console renderer (dev).

## Consequences

Positive: Structured events (not string templates), context propagation via contextvars, dual renderer.
Negative: Learning curve for structlog API.
Neutral: structlog wraps stdlib logging internally.

## Alternatives Considered

- stdlib logging: Standard but verbose config, no structured events.
- loguru: Simple but single-output, less flexible.
