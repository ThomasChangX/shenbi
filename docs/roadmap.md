# Project Roadmap — Deferred Work

This file tracks work that was intentionally deferred during P-1.E but must
be picked up by a future PR. Each entry includes the originating PR so the
context can be recovered.

## P0: re-add `registry-lockfile-fresh` pre-commit hook

- **Deferred in:** PR-38 (commit `5655bc1`)
- **Why deferred:** The hook referenced `tests/build_registry.py`, which
  doesn't exist yet. The hook was a no-op today (its `files:` pattern
  matched nothing) but would fail the moment P0 starts creating
  `skills/<name>/meta.yaml` files.
- **Trigger to re-add:** When P0 lands the build-registry tool at
  `tests/build_registry.py`.
- **Re-add pattern:**
  ```yaml
  - id: registry-lockfile-fresh
    name: registry.lock.json freshness
    entry: tests/build_registry.py
    language: system
    files: ^(skills/.*\.yaml|tests/tiers/.*\.yaml)$
    pass_filenames: false
  ```
