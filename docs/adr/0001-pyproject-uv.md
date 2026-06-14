# ADR 0001: Use uv for dependency management

- Status: accepted
- Date: 2026-06-14
- Deciders: ThomasChangX

## Context

Shenbi needs a dependency manager that supports lockfiles with hashes, Python version management, and fast installation. Options: pip-tools, poetry, uv.

## Decision

Use uv (Astral) as the sole dependency manager.

## Consequences

Positive: Fastest Python package manager (Rust-based), native pyproject.toml support, lockfile with hashes, built-in Python version management.
Negative: Newer tool (2024+), smaller community than poetry.
Neutral: Single tool for both dependency resolution and Python installation.

## Alternatives Considered

- poetry: Mature but slower, separate lock format, no built-in Python management.
- pip-tools: Simple but no resolver, manual requirements.in/requirements.txt workflow.
