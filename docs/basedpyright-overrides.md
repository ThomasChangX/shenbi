# basedpyright executionEnvironments — Design Notes

`pyproject.toml` declares three `executionEnvironments` entries that
relax strict-mode diagnostics for specific subdirectories. This file
explains the rationale, the trade-off, and the path to removing each
override.

## Summary

| Root | Disabled rules | Why |
|---|---|---|
| `tests` | reportUnused*, reportUnknown*, reportPrivateUsage, reportMissingParameterType | Industry norm: test code uses fixtures, Mock, dynamic setattr that are inherently untyped. Real-bug rules (reportPossiblyUnboundVariable, reportArgumentType, reportIndexIssue) remain on. |
| `src/shenbi/skill_utils` | reportUnknown*, reportPrivateUsage, reportMissingTypeStubs | Mirrors mypy's existing `ignore_errors = true` for `shenbi.skill_utils.*` (PR-27 deferral). Annotation + tests for these scripts is a follow-up. |
| `src/shenbi/gates` | reportUnusedImport, reportPrivateUsage, reportUnusedVariable, reportUnusedFunction, reportUnknownVariableType, reportUnknownArgumentType, reportUnknownParameterType, reportUnknownLambdaType, reportUnknownMemberType | Router re-export pattern + jload/yload Any + dead stub variables. See below. |

## gates/ override — full rationale

The `src/shenbi/gates` override is the broadest and the most likely to mask
future real bugs. Three categories of justification:

### 1. Router re-export pattern (reportUnusedImport)

Every gate module (`g0.py`, `g1.py`, …, `g_transition.py`) re-exports
symbols from `shared.py` so callers can do
`from shenbi.gates.g4.generic import X`. The re-exports are marked with
`# noqa: F401` (ruff respects this), but basedpyright does not recognize
this comment.

**Alternative considered:** Add `__all__` to each gate module listing
every re-exported symbol. Rejected because maintaining `__all__` across
32 modules is high-churn and easily forgotten.

### 2. jload/yload return Any (reportUnknownMemberType, reportUnknown*)

`shared.py` defines `jload(p) -> Any` and `yload(p) -> Any` because
`json.load` and `yaml.safe_load` are inherently untyped. Callers then
do `.get(...)`, `[key]`, iteration, etc. — all of which propagate the
`Unknown` taint to the result.

There are **102 jload/yload call sites** across gates/. Narrowing each
one inline is impractical.

### 3. Dead stub variables (reportUnusedVariable, reportUnusedFunction)

Three known stubs are tracked with `# TODO post-PR-25:` comments:
- `g0.py` — `allowed_prefixes`
- `g6.py` — `tension_phases`
- `g_transition.py` — `mf`

Plus three router helpers that basedpyright doesn't see cross-module
usage for:
- `shared.py` — `_find_report`, `_normalize_file_paths`
- `g5.py` — `_text_fingerprint`

## Plan to remove the gates/ override

The principled end-state is:

1. Rewrite `jload`/`yload` signatures:
   ```python
   def jload(p: str | Path) -> dict[str, Any] | list[Any]: ...
   def yload(p: str | Path) -> dict[str, Any]: ...
   ```
   This narrows the Any-taint at the source.

2. Add `__all__` to each gate module so re-exports are recognized.
   (Or switch to explicit `from shenbi.gates.shared import X` in each
   caller, dropping the re-export pattern entirely. Design decision.)

3. Wire or delete the three dead stubs.

4. Drop the `src/shenbi/gates` executionEnvironment.

## Why this was deferred from post-PR-25

The post-PR-25 fix commit (`4d78fd9`) was already correcting a misleading
"all pass" claim from PR-25. Adding the 102-call-site refactor on top
would have inflated the commit beyond review. The cheaper option
(broad override + tracking doc + revisit date) was chosen.

**Revisit by:** 2026-09-01.

## Related

- `docs/roadmap.md` — entry tracking this deferral
- `pyproject.toml` — the override declarations
- PR-27 commit — mypy `ignore_errors` for skill_utils (parallel pattern)
