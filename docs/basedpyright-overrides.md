# basedpyright Configuration — Design Notes

`pyproject.toml` configures basedpyright in strict mode with two
categories of relaxation:

1. **Per-directory `executionEnvironments`** for `tests/` and
   `src/shenbi/skill_utils/` — mirrors mypy's existing overrides.
2. **Project-level rule downgrades** for the Unknown-family rules.

## Project-level rule downgrades

```toml
reportMissingTypeStubs = "warning"
reportUnknownMemberType = "warning"
reportUnknownVariableType = "warning"
reportUnknownArgumentType = "warning"
reportUnknownLambdaType = "warning"
reportUnknownParameterType = "warning"
```

### Why

Gates load heterogeneous external data (`progress.json`, `deps.json`,
`summary.json`, score files, YAML frontmatter) via `jload`/`yload`
which return `dict[str, Any]`. Value access on `dict[str, Any]`
produces `Any`, which strict mode flags as Unknown. These are noise,
not bugs — the type system cannot know the shape of arbitrary JSON
without schema validation.

Real type errors are still caught by rules that remain as errors:
- `reportArgumentType` — passing wrong type to typed parameter
- `reportPossiblyUnboundVariable` — using potentially undefined variable
- `reportIndexIssue` — invalid dict/list indexing
- `reportUnnecessaryIsInstance` — redundant type narrowing
- `reportAttributeAccessIssue` — accessing non-existent attribute

### Alternative considered: TypedDicts

The "textbook proper" fix would be to define TypedDicts for each JSON
shape and validate at boundaries. Rejected for this codebase because:

1. **9+ distinct JSON shapes** (progress, deps, acceptance, genre-config,
   novel, summary, score files, exempt_data, markers) each with nested
   fields — high upfront cost.
2. **Schemas are evolving** as the framework develops — TypedDicts would
   require ongoing maintenance to track schema changes.
3. **`cast()` at every `jload` boundary** adds boilerplate without
   runtime validation (TypedDicts are erased at runtime).

If the project later adopts Pydantic for runtime-validated models at
boundaries, these rules can be re-tightened to error.

## executionEnvironments

| Root | Disabled rules | Why |
|---|---|---|
| `tests` | reportUnused*, reportUnknown*, reportPrivateUsage, reportMissingParameterType | Industry norm: test code uses fixtures, Mock, dynamic setattr that are inherently untyped. |
| `src/shenbi/skill_utils` | reportUnknown*, reportPrivateUsage, reportMissingTypeStubs | Mirrors mypy's `ignore_errors = true` for `shenbi.skill_utils.*` (PR-27 deferral). |

## What was removed (post-PR-25 follow-up)

The original post-PR-25 fix added a third executionEnvironment for
`src/shenbi/gates/` that broadly suppressed 9 diagnostic categories.
This was a deferral, not a fix. The deferral has been resolved:

1. **jload/yload narrowed** from `Any` to `dict[str, Any]` with
   runtime `isinstance` checks that fail loud on non-dict JSON/YAML.
2. **587 unused imports removed** — gate modules no longer re-export
   30+ symbols from `shared.py` that nobody imports from them.
3. **Private helpers renamed** — `_find_report` → `find_report`,
   `_normalize_file_paths` → `normalize_file_paths`. Cross-module
   helpers shouldn't pretend to be private.
4. **Dead code deleted** — `allowed_prefixes` (g0), `tension_phases`
   (g6), `mf` (g_transition), `_text_fingerprint` (moved from g5 to
   chapter_drafting where it's actually used).
5. **Redundant `isinstance(x, dict)` checks removed** — now that
   jload/yload guarantee dict, these were provably unnecessary.
6. **Dead `try: import yaml` blocks removed** from 21 gate modules —
   yaml is a hard dependency, and `yload` handles it internally.
7. **Dead `yload(...) if yaml else {}` guards removed** — same reason.

The `src/shenbi/gates` executionEnvironment is gone. Gates are now
checked under the same strict-mode rules as the rest of `src/shenbi/`,
with only the project-level Unknown-family downgrade applying.
