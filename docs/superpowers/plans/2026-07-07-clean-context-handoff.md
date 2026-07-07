# Clean-Context Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement decisions-sidecar artifacts (Layer A, 7 skills) + field-level reads with real context filtering (Layer B, 12 skills) + 8 consistency modifications to framework code, fully aligning with Anthropic/LangChain multi-agent best practices.

**Architecture:** Two-layer design. Layer A adds a `decisions.json` sidecar artifact to 7 skills, persisting structured decision summaries that downstream skills read as lightweight references (Anthropic "artifact + lightweight reference"). Layer B implements real context filtering in `_build_skill_prompt` so the LLM sees only declared fields, not entire files (LangChain "filtered portions"). 8 consistency modifications (M1-M8) synchronize the framework's gate/dispatcher/registry infrastructure to handle the new file type.

**Tech Stack:** Python 3.11+, pathlib, json/yaml, pytest (unit marks `@pytest.mark.unit`), structlog, pydantic. Framework code under `src/shenbi/`, tests under `tests/unit/`, skills under `skills/`.

## Global Constraints

- Python 3.11+ (PEP 621 pyproject.toml)
- Framework code uses `pathlib.Path` for file I/O, `json` for structured output
- Gate functions return `passed()`/`fail()` helpers from `shenbi.gates.shared`
- No `print()` in framework code; use structlog (`get_logger`)
- Test fixtures must be real skill outputs (G0.9 prohibits hand-crafted mocks)
- Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- Coverage threshold: ≥85% (`--cov-fail-under=85`)
- All tests must pass: `just check` (ruff + mypy + basedpyright + pytest)

---

## File Structure

### Files Created
| File | Responsibility |
|------|---------------|
| `src/shenbi/gates/g4/_decisions_schema.py` | Decisions schema v1 enums + P2.5 rationale validation rules |
| `docs/framework/decisions-schema.md` | Single source of truth for schema version, fields, enums, per-skill differences |
| `scripts/lint_contract_fields.py` | CI lint: contract.reads field declarations vs truth file actual headings/keys |
| `tests/unit/gates/test_decisions_schema.py` | Unit tests for P2.5 rationale rules |
| `tests/unit/gates/test_g4_decisions.py` | Unit tests for G4 decisions schema validation |
| `tests/unit/pipeline/test_field_filtering.py` | Unit tests for Layer B `_filter_to_fields` + escape hatch |

### Files Modified
| File | Changes |
|------|---------|
| `docs/framework/truth-files.yaml` | M1: register `context/chapter-N-context-decisions.json` + `chapters/chapter-N-decisions.json` as `kind: decisions` |
| `site/framework/truth-files.yaml` | M2: identical changes (mirror of docs/) |
| `src/shenbi/dispatcher/executor.py` | M3: `_decisions_file_set()` + `derive_file_type` decisions branch |
| `src/shenbi/gates/g2.py` | M4: G2.dec.1-3 decisions validation branch (skip word count) |
| `src/shenbi/phase_runner.py` | M5: replace rglob with `derive_output_files`; M8: call `derive_file_type` instead of hardcoded "chapter" |
| `src/shenbi/pipeline/dispatch_helper.py` | M6: multi-file output format reminder; Layer B: `_filter_to_fields` + consume `read_fields` in `_build_skill_prompt` |
| `src/shenbi/gates/g1.py` | B.4: `check_fields_exist` soft WARN check |
| `src/shenbi/gates/g4/generic.py` | Register `g4_decisions` checker for decisions-producing skills |
| `skills/shenbi-context-composing/SKILL.md` | kind→artifact, add decisions.json to writes, add {file, fields} dict-form reads |
| `skills/shenbi-market-radar/SKILL.md` | kind→artifact, add decisions.json to writes |
| `skills/shenbi-chapter-drafting/SKILL.md` | Add decisions.json to writes + reads; add {file, fields} dict-form reads |
| `skills/shenbi-chapter-planning/SKILL.md` | Add decisions.json to writes + reads; add {file, fields} dict-form reads |
| `skills/shenbi-chapter-revision/SKILL.md` | Add decisions.json to writes + reads |
| `skills/shenbi-state-settling/SKILL.md` | Add decisions.json to writes; add {file, fields} dict-form reads |
| `skills/shenbi-short-drafting/SKILL.md` | Add decisions.json to writes + reads |
| `skills/shenbi-foreshadowing-plant/SKILL.md` | Add {file, fields} dict-form reads |
| `skills/shenbi-foreshadowing-track/SKILL.md` | Add {file, fields} dict-form reads |
| `skills/shenbi-style-polishing/SKILL.md` | Add {file, fields} dict-form reads |
| `skills/shenbi-length-normalizing/SKILL.md` | Add {file, fields} dict-form reads |
| `skills/shenbi-review-continuity/SKILL.md` | Add {file, fields} dict-form reads |
| `skills/shenbi-review-pacing/SKILL.md` | Add {file, fields} dict-form reads |
| `tests/unit/test_dispatcher_executor.py` | Extend: decisions branch tests |
| `tests/unit/gates/test_g2.py` | Extend: decisions branch tests |
| `tests/unit/test_phase_runner.py` | Extend: M5 + M8 tests |
| `tests/unit/test_contract.py` | Extend: new registry paths resolve |
| `justfile` | Add `lint-contract-fields` target |

---

## Phase 1 — Infrastructure (Tasks 1-8)

### Task 1: Decisions Schema Module

**Files:**
- Create: `src/shenbi/gates/g4/_decisions_schema.py`
- Test: `tests/unit/gates/test_decisions_schema.py`

**Interfaces:**
- Produces: `DECISIONS_SCHEMA_VERSION`, `VALID_BASIS`, `VALID_SEVERITY`, `VALID_HANDLING`, `VALID_TRIM`, `ROUTINE_BASIS`, `validate_selection_rationale()`, `validate_adjustment_rationale()`

- [ ] **Step 1: Write failing tests for P2.5 rationale rules**

```python
# tests/unit/gates/test_decisions_schema.py
"""Unit tests for decisions schema v1 + P2.5 rationale rules."""

from __future__ import annotations

import pytest

from shenbi.gates.g4._decisions_schema import (
    DECISIONS_SCHEMA_VERSION,
    VALID_BASIS,
    VALID_SEVERITY,
    ROUTINE_BASIS,
    validate_selection_rationale,
    validate_adjustment_rationale,
)


@pytest.mark.unit
class TestSchemaConstants:
    def test_schema_version(self) -> None:
        assert DECISIONS_SCHEMA_VERSION == "shenbi-decisions-v1"

    def test_valid_basis_contains_routine_and_anomaly(self) -> None:
        assert "adjacent_to_target_chapter" in VALID_BASIS
        assert "arc_relevance" in VALID_BASIS
        assert "volume_scope" in VALID_BASIS
        assert "manual_override" in VALID_BASIS

    def test_routine_basis_excludes_manual_override(self) -> None:
        assert "manual_override" not in ROUTINE_BASIS

    def test_valid_severity_has_low_and_high(self) -> None:
        assert "low" in VALID_SEVERITY
        assert "high" in VALID_SEVERITY


@pytest.mark.unit
class TestP25RationaleRules:
    def test_routine_low_severity_with_rationale_fails(self) -> None:
        """P2.5: routine basis + low severity → rationale FORBIDDEN."""
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="low", rationale="some explanation"
        )
        assert len(errors) == 1
        assert "FORBIDDEN" in errors[0] or "forbidden" in errors[0].lower()

    def test_routine_low_severity_without_rationale_passes(self) -> None:
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="low", rationale=None
        )
        assert errors == []

    def test_routine_high_severity_without_rationale_fails(self) -> None:
        """P2.5 escape hatch: high-stakes routine → rationale REQUIRED."""
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="high", rationale=None
        )
        assert len(errors) == 1
        assert "REQUIRED" in errors[0] or "required" in errors[0].lower()

    def test_routine_high_severity_with_rationale_passes(self) -> None:
        errors = validate_selection_rationale(
            basis="arc_relevance", severity="high", rationale="climax chapter, must deliver"
        )
        assert errors == []

    def test_manual_override_without_rationale_fails(self) -> None:
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale=None
        )
        assert len(errors) == 1

    def test_manual_override_with_rationale_passes(self) -> None:
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale="POV conflict"
        )
        assert errors == []

    def test_rationale_over_100_chars_fails(self) -> None:
        long_rationale = "x" * 101
        errors = validate_selection_rationale(
            basis="manual_override", severity="low", rationale=long_rationale
        )
        assert any("100" in e for e in errors)

    def test_invalid_basis_fails(self) -> None:
        errors = validate_selection_rationale(
            basis="invalid_basis", severity="low", rationale=None
        )
        assert any("basis" in e.lower() for e in errors)

    def test_adjustment_without_rationale_fails(self) -> None:
        errors = validate_adjustment_rationale(rationale=None)
        assert len(errors) == 1

    def test_adjustment_with_rationale_passes(self) -> None:
        errors = validate_adjustment_rationale(rationale="drift absorbed by pacing")
        assert errors == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/gates/test_decisions_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.gates.g4._decisions_schema'`

- [ ] **Step 3: Implement the schema module**

```python
# src/shenbi/gates/g4/_decisions_schema.py
"""Decisions schema v1 — enums + P2.5 rationale validation rules.

P2.5 rule (spec A.3):
- basis in ROUTINE_BASIS and severity != "high" → rationale FORBIDDEN
- basis == "manual_override" → rationale REQUIRED (severity ignored)
- severity == "high" (any basis) → rationale REQUIRED
- adjustments[] → rationale ALWAYS REQUIRED (anomalous by definition)
- rationale (when present) must be ≤100 chars
"""

from __future__ import annotations

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"

VALID_BASIS = {
    "adjacent_to_target_chapter",  # routine: chapters near target
    "arc_relevance",               # routine: related to current arc
    "volume_scope",                # routine: within current volume
    "manual_override",             # anomaly: human/skill explicitly overrode routine
}

VALID_SEVERITY = {
    "low",     # default for routine decisions — rationale forbidden
    "high",    # high-stakes routine decision — rationale required (P2.5 escape hatch)
}

VALID_HANDLING = {
    "compensate_via_pacing",
    "explicit_callout",
    "defer_to_next_chapter",
    "ignore",
}

VALID_TRIM = {"none", "oldest_first", "lowest_relevance", "manual"}

ROUTINE_BASIS = VALID_BASIS - {"manual_override"}

_RATIONALE_MAX_CHARS = 100


def validate_selection_rationale(
    basis: str, severity: str, rationale: str | None
) -> list[str]:
    """Validate P2.5 rationale rules for a selections[] entry.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    if basis not in VALID_BASIS:
        errors.append(f"invalid basis: {basis!r}, allowed: {sorted(VALID_BASIS)}")
        return errors

    if severity not in VALID_SEVERITY:
        errors.append(f"invalid severity: {severity!r}, allowed: {sorted(VALID_SEVERITY)}")
        return errors

    needs_rationale = basis == "manual_override" or severity == "high"
    is_routine_low = basis in ROUTINE_BASIS and severity != "high"

    if is_routine_low and rationale is not None:
        errors.append(
            f"rationale FORBIDDEN for routine basis {basis!r} with severity {severity!r}"
        )
    elif needs_rationale and not rationale:
        errors.append(
            f"rationale REQUIRED for basis {basis!r} with severity {severity!r}"
        )

    if rationale and len(rationale) > _RATIONALE_MAX_CHARS:
        errors.append(
            f"rationale exceeds {_RATIONALE_MAX_CHARS} chars (got {len(rationale)})"
        )

    return errors


def validate_adjustment_rationale(rationale: str | None) -> list[str]:
    """Validate that adjustments[] always have rationale (anomalous by definition)."""
    if not rationale:
        return ["rationale REQUIRED for adjustments (anomalous by definition)"]
    if len(rationale) > _RATIONALE_MAX_CHARS:
        return [f"rationale exceeds {_RATIONALE_MAX_CHARS} chars (got {len(rationale)})"]
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/gates/test_decisions_schema.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/_decisions_schema.py tests/unit/gates/test_decisions_schema.py
git commit -m "feat: add decisions schema v1 module with P2.5 rationale rules"
```

---

### Task 2: Registry Registration (M1+M2)

**Files:**
- Modify: `docs/framework/truth-files.yaml`
- Modify: `site/framework/truth-files.yaml`
- Test: `tests/unit/test_contract.py` (extend)

**Interfaces:**
- Produces: two new registry concepts with `kind: decisions`, two new parametrics, two new globs

- [ ] **Step 1: Write failing test for new registry paths**

```python
# Append to tests/unit/test_contract.py

@pytest.mark.unit
class TestDecisionsRegistryPaths:
    def test_context_decisions_json_resolves(self) -> None:
        from shenbi.contracts.legacy import load_registry, resolves
        registry = load_registry()
        assert resolves("context/chapter-N-context-decisions.json", registry)

    def test_chapter_decisions_json_resolves(self) -> None:
        from shenbi.contracts.legacy import load_registry, resolves
        registry = load_registry()
        assert resolves("chapters/chapter-N-decisions.json", registry)

    def test_decisions_kind_in_registry(self) -> None:
        from shenbi.contracts.registry import bootstrap_registry
        reg = bootstrap_registry()
        assert reg.get("context/chapter-N-context-decisions.json") == "decisions"
        assert reg.get("chapters/chapter-N-decisions.json") == "decisions"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_contract.py::TestDecisionsRegistryPaths -v`
Expected: FAIL — paths don't resolve yet

- [ ] **Step 3: Add concepts, patterns, globs to both truth-files.yaml copies**

In `docs/framework/truth-files.yaml`, after the `context/chapter-N-context.md` concept (line 52), add:

```yaml
  - {name: context/chapter-N-context-decisions.json, kind: decisions}  # NEW: decisions sidecar
  - {name: chapters/chapter-N-decisions.json, kind: decisions}          # NEW: decisions sidecar
```

In the `patterns:` section, after the `context/chapter-N-context.md` parametric (line 77), add:

```yaml
  - {parametric: context/chapter-N-context-decisions.json, glob: context/chapter-*-context-decisions.json}
  - {parametric: chapters/chapter-N-decisions.json, glob: chapters/chapter-*-decisions.json}
```

In the `globs:` section, after the `context/chapter-*-context.md` glob, add:

```yaml
  - {pattern: context/chapter-*-context-decisions.json}
  - {pattern: chapters/chapter-*-decisions.json}
```

Apply identical changes to `site/framework/truth-files.yaml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_contract.py::TestDecisionsRegistryPaths -v`
Expected: PASS

- [ ] **Step 5: Verify no existing contracts break**

Run: `pytest tests/unit/contract/ -v`
Expected: all PASS (existing resolves still work)

- [ ] **Step 6: Commit**

```bash
git add docs/framework/truth-files.yaml site/framework/truth-files.yaml tests/unit/test_contract.py
git commit -m "feat: register decisions.json paths in truth-files.yaml (M1+M2)"
```

---

### Task 3: derive_file_type Decisions Branch (M3)

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:31-42` (add `_decisions_file_set`), `:65-85` (add decisions branch to `derive_file_type`)
- Test: `tests/unit/test_dispatcher_executor.py` (extend)

**Interfaces:**
- Produces: `_decisions_file_set() -> set[str]`, modified `derive_file_type(skill) -> str` now returns `"decisions"` when outputs include a decisions-kind file

- [ ] **Step 1: Write failing tests**

```python
# Append to tests/unit/test_dispatcher_executor.py

@pytest.mark.unit
def test_derive_file_type_returns_decisions_for_context_composing_after_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After context-composing migrates to kind=artifact with decisions.json writes,
    derive_file_type returns 'decisions'."""
    import shenbi.dispatcher.executor as exec_mod
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["context/chapter-N-context-decisions.json"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-context-composing") == "decisions"


@pytest.mark.unit
def test_derive_file_type_returns_decisions_for_chapter_drafting_after_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """chapter-drafting writes both chapter-N.md AND chapter-N-decisions.json.
    When it writes a decisions file, derive_file_type returns 'decisions'."""
    import shenbi.dispatcher.executor as exec_mod
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["chapters/chapter-N.md", "chapters/chapter-N-decisions.json"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-chapter-drafting") == "decisions"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_dispatcher_executor.py::test_derive_file_type_returns_decisions_for_context_composing_after_migration tests/unit/test_dispatcher_executor.py::test_derive_file_type_returns_decisions_for_chapter_drafting_after_migration -v`
Expected: FAIL — returns "chapter" not "decisions"

- [ ] **Step 3: Add `_decisions_file_set` and decisions branch to `derive_file_type`**

In `src/shenbi/dispatcher/executor.py`, after the `_truth_file_set` function (line 42), add:

```python
_decisions_files_cache: set[str] | None = None


def _decisions_file_set() -> set[str]:
    """Files listed as kind='decisions' in truth-files.yaml concepts."""
    global _decisions_files_cache
    if _decisions_files_cache is None:
        _decisions_files_cache = {
            name for name, kind in bootstrap_registry().items() if kind == "decisions"
        }
    return _decisions_files_cache
```

In `derive_file_type`, after the truth check (line 84) and before `return "chapter"` (line 85), add:

```python
    if outputs & _decisions_file_set():
        return "decisions"
```

- [ ] **Step 4: Add cache reset fixture (I3 fix)**

The new `_decisions_files_cache` (and existing `_truth_files_cache`) are module globals that persist across tests. Add an autouse fixture to reset them:

```python
# tests/unit/conftest.py — CREATE this file (it does not exist yet).
# Note: the existing autouse fixture (_isolate_structlog_config) lives in
# tests/conftest.py (repo root). pytest merges conftest scopes, so both
# coexist correctly. This file is specifically for unit-test-scoped fixtures.

import pytest
import shenbi.dispatcher.executor as executor


@pytest.fixture(autouse=True)
def reset_executor_caches():
    """Reset module-global caches before each test to prevent order-dependence."""
    executor._truth_files_cache = None
    executor._decisions_files_cache = None
    yield
    executor._truth_files_cache = None
    executor._decisions_files_cache = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_dispatcher_executor.py -v`
Expected: all PASS (new + existing regression)

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/dispatcher/executor.py tests/unit/test_dispatcher_executor.py tests/unit/conftest.py
git commit -m "feat: add derive_file_type decisions branch (M3)"
```

---

### Task 4: G2 Decisions Validation Branch (M4)

**Files:**
- Modify: `src/shenbi/gates/g2.py` (add decisions branch before `file_type == "chapter"`)
- Test: `tests/unit/gates/test_g2.py` (extend)

**Interfaces:**
- Produces: G2.dec.1 (valid JSON), G2.dec.2 (schema version), G2.dec.3 (required keys) checks; skips G2.6/G2.7 word count for decisions files

- [ ] **Step 1: Write failing tests**

```python
# Append to tests/unit/gates/test_g2.py

class TestG2DecisionsBranch:
    """G2.dec.* — decisions.json validation (M4)."""

    def test_valid_decisions_json_passes(self, tmp_path: Path) -> None:
        import json
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "context" / "chapter-5-context-decisions.json"
        fp.parent.mkdir(parents=True)
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "PASS"

    def test_invalid_json_fails_g2_dec_1(self, tmp_path: Path) -> None:
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text("{not valid json", encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.1" in str(c) for c in data.get("checks", []))

    def test_wrong_schema_version_fails_g2_dec_2(self, tmp_path: Path) -> None:
        import json
        decisions = {
            "$schema": "wrong-version",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.2" in str(c) for c in data.get("checks", []))

    def test_missing_required_keys_fails_g2_dec_3(self, tmp_path: Path) -> None:
        import json
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            # missing: chapter, produced_at, selections
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "FAIL"
        assert any("G2.dec.3" in str(c) for c in data.get("checks", []))

    def test_decisions_does_not_trigger_word_count(self, tmp_path: Path) -> None:
        """Critical: G2.6/G2.7 word count must NOT run on decisions files."""
        import json
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
        }
        fp = tmp_path / "chapter-5-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = gate_G2(str(fp), file_type="decisions", round_dir=str(tmp_path))
        data = json.loads(result)
        # G2.6/G2.7 should NOT appear in checks
        check_ids = [c.get("id", "") for c in data.get("checks", [])]
        assert not any(c == "G2.6" for c in check_ids)
        assert not any(c == "G2.7" for c in check_ids)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/gates/test_g2.py::TestG2DecisionsBranch -v`
Expected: FAIL — decisions branch doesn't exist, word count runs on JSON

- [ ] **Step 3: Add decisions branch to `gate_G2`**

**Placement (critical)**: The `content` variable is not defined until line 58 (`content = p.read_text(encoding="utf-8")`, inside the G2.3 try block). The decisions branch uses `json.loads(content)`, so it must be placed **after** the G2.3 try/except block (after line 62, the `continue` in the except clause) and **before** line 75 (the `if fp.endswith(".md"):` YAML frontmatter check).

The G2.3 block (lines 56-62) currently looks like:
```python
        # G2.3 — UTF-8
        try:
            content = p.read_text(encoding="utf-8")
            checks.append({"id": "G2.3", "file": fp, "s": "PASS"})
        except Exception:
            mf.append({"id": "G2.3", "file": fp, "s": "FAIL"})
            continue
```

Insert the decisions branch **immediately after** line 62 (the `continue` in the G2.3 except block), before the G2.4 JSON syntax check at line 64:

```python
        # G2.dec — decisions.json validation (M4)
        # Placed after G2.3 (content is now available) and before G2.4/G2.5.
        if file_type == "decisions":
            # G2.dec.1 — valid JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                mf.append({"id": "G2.dec.1", "file": fp, "s": "FAIL", "r": "invalid JSON"})
                continue
            # G2.dec.2 — schema version
            if data.get("$schema") != "shenbi-decisions-v1":
                mf.append({
                    "id": "G2.dec.2", "file": fp, "s": "FAIL",
                    "r": f"schema version mismatch: {data.get('$schema')}",
                })
            # G2.dec.3 — required keys
            required = {"skill", "chapter", "selections", "produced_at"}
            missing = required - data.keys()
            if missing:
                mf.append({
                    "id": "G2.dec.3", "file": fp, "s": "FAIL",
                    "r": f"missing keys: {missing}",
                })
            else:
                checks.append({"id": "G2.dec", "file": fp, "s": "PASS"})
            continue  # CRITICAL: skip G2.4-G2.10 (word count etc.) for JSON decisions
```

**Why this placement works**: `content` is assigned at line 58 inside the G2.3 try block. If G2.3 succeeds (the normal path), `content` is available when we reach the decisions branch. If G2.3 fails, the `continue` at line 62 skips the decisions branch entirely — which is correct (a file that can't be read as UTF-8 shouldn't be parsed as JSON either). The `continue` at the end of the decisions branch skips G2.4-G2.10 (JSON syntax recheck, frontmatter, word count, placeholders, truth diff) — all of which are irrelevant or harmful for decisions.json files.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/gates/test_g2.py -v`
Expected: all PASS (new + existing regression)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g2.py tests/unit/gates/test_g2.py
git commit -m "feat: add G2 decisions validation branch with word-count skip (M4)"
```

---

### Task 5: phase_runner Output Discovery + file_type Fix (M5+M8)

**Files:**
- Modify: `src/shenbi/phase_runner.py:145-168` (`cmd_post_skill`)
- Test: `tests/unit/test_phase_runner.py` (extend)

**Interfaces:**
- Produces: `cmd_post_skill` now uses `derive_output_files(skill, chapter, proj)` for output discovery and `derive_file_type(skill)` for G2 file_type

- [ ] **Step 1: Write failing tests**

```python
# Append to tests/unit/test_phase_runner.py

@pytest.mark.unit
class TestPostSkillOutputDiscovery:
    """M5: phase_runner uses derive_output_files instead of rglob."""

    def test_post_skill_passes_derived_file_type_not_hardcoded_chapter(
        self, tmp_path, monkeypatch
    ):
        """M8: G2 must receive derive_file_type(skill), not hardcoded 'chapter'."""
        import shenbi.phase_runner as pr
        from shenbi.status import PhaseState

        # Setup: a started phase
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        state_dir = round_dir / "phase-state"
        state_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create state file
        import json
        state = {"phase": "drafting", "state": PhaseState.STARTED, "steps": []}
        (state_dir / "drafting.json").write_text(json.dumps(state))

        # Mock derive_file_type to return 'decisions'
        captured_file_type = []

        def mock_run_gate(gate_name, args):
            if gate_name == "G2":
                captured_file_type.append(args[1])  # file_type is args[1]
                return {"status": "PASS"}
            if gate_name == "G4":
                return {"status": "PASS"}
            return {"status": "PASS"}

        monkeypatch.setattr(pr, "run_gate", mock_run_gate)
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_file_type",
            lambda skill: "decisions",
            raising=True,
        )
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_output_files",
            lambda skill, chapter, rd: [],
            raising=True,
        )

        pr.cmd_post_skill("drafting", "shenbi-context-composing", str(round_dir), str(project_dir))

        # Verify G2 received 'decisions', not 'chapter'
        assert len(captured_file_type) > 0
        assert captured_file_type[0] == "decisions"

    def test_post_skill_uses_derive_output_files_not_rglob(
        self, tmp_path, monkeypatch
    ):
        """M5: output_files comes from derive_output_files, not rglob.
        When chapter is provided, derive_output_files is the sole source —
        rglob fallback does NOT fire (it only fires when chapter is None)."""
        import shenbi.phase_runner as pr
        from shenbi.status import PhaseState
        import json

        round_dir = tmp_path / "round"
        round_dir.mkdir()
        state_dir = round_dir / "phase-state"
        state_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        state = {"phase": "drafting", "state": PhaseState.STARTED, "steps": []}
        (state_dir / "drafting.json").write_text(json.dumps(state))

        # Create a .md file that rglob would find but derive_output_files would NOT
        stray_file = project_dir / "stray.md"
        stray_file.write_text("should not be discovered", encoding="utf-8")

        captured_outputs = []

        def mock_run_gate(gate_name, args):
            if gate_name == "G2":
                captured_outputs.append(args[0])  # file_paths is args[0]
                return {"status": "PASS"}
            if gate_name == "G4":
                return {"status": "PASS"}
            return {"status": "PASS"}

        # derive_output_files returns only contract-declared paths (empty here)
        monkeypatch.setattr(pr, "run_gate", mock_run_gate)
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_output_files",
            lambda skill, chapter, rd: [],
            raising=True,
        )
        monkeypatch.setattr(
            "shenbi.dispatcher.executor.derive_file_type",
            lambda skill: "chapter",
            raising=True,
        )

        # Pass chapter=5 so the rglob fallback does NOT fire.
        # With chapter provided, derive_output_files is the sole source.
        pr.cmd_post_skill(
            "drafting", "shenbi-chapter-drafting", str(round_dir), str(project_dir),
            chapter=5,
        )

        # With empty derive_output_files, G2 should receive empty string (no stray.md)
        if captured_outputs:
            assert "stray.md" not in captured_outputs[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_phase_runner.py::TestPostSkillOutputDiscovery -v`
Expected: FAIL — current code uses rglob and hardcodes "chapter"

- [ ] **Step 3: Modify `cmd_post_skill` to use `derive_output_files` and `derive_file_type`**

**Critical**: `derive_output_files(skill, chapter, proj)` returns `[]` when `chapter=None` for any chapter-parametric path (e.g., `chapters/chapter-N.md`) — `_resolve_chapter_path` returns `""` for unresolved `N`/`NNN`, and `derive_output_files` filters empty strings. Since virtually every chapter skill writes chapter-parametric files, passing `chapter=None` silently disables G2 — a regression from the current `rglob("*.md")` heuristic which at least finds real files on disk.

**Root cause (verified)**: `phase_runner.py` is a CLI invoked as `post-skill <phase> <skill> --round-dir <dir> --project-dir <dir>`. There is **no `prompt` variable** in the caller (`main()` at line 306) — verified: `grep prompt src/shenbi/phase_runner.py` returns 0 matches. `PhaseState` (`status.py:30`) tracks only state strings, no chapter field. The previous fix's `'prompt' in dir()` is both wrong (dir() doesn't check local variables) and moot (prompt doesn't exist).

**Fix**: Add a `--chapter` CLI flag to the `post-skill` command. The pipeline driver (which invokes phase_runner) already knows the chapter — it passes it explicitly.

**Codebase reality (verified)**: `phase_runner.py` does NOT use argparse. It uses a hand-rolled `find_flag()` helper (line 284) that scans `sys.argv[2:]` for `--flag value` pairs. The `post-skill` handler is at line 304-306.

First, add `--chapter` parsing in `main()`, after the existing `find_flag` calls (after line 296):

```python
# After line 296 (project_dir = find_flag("--project-dir", required=False)):
chapter_str = find_flag("--chapter", required=False)
chapter = int(chapter_str) if chapter_str else None
```

Then modify the `post-skill` dispatch (line 304-306) to pass chapter:

```python
# Before (lines 304-306):
    elif cmd == "post-skill":
        phase, skill = args[0], args[1]
        cmd_post_skill(phase, skill, round_dir, project_dir)

# After:
    elif cmd == "post-skill":
        phase, skill = args[0], args[1]
        cmd_post_skill(phase, skill, round_dir, project_dir, chapter=chapter)
```

Then modify `cmd_post_skill`:

```python
# Before (lines 145-153):
def cmd_post_skill(phase: str, skill: str, round_dir: str, project_dir: str | None) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    assert project_dir is not None
    proj = Path(project_dir)
    output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
    g2_status = GateStatus.SKIP.value
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), "chapter", str(round_dir)])
        g2_status = g2.get("status", GateStatus.FAIL.value)

# After:
def cmd_post_skill(
    phase: str, skill: str, round_dir: str, project_dir: str | None,
    chapter: int | None = None,
) -> None:
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    assert project_dir is not None
    proj = Path(project_dir)
    from shenbi.dispatcher.executor import derive_file_type, derive_output_files
    # M5: use contract-declared outputs instead of rglob heuristic.
    # chapter must be provided for chapter-parametric skills; when None
    # (non-pipeline T2), derive_output_files returns [] for parametric paths.
    output_files = [
        p for p in derive_output_files(skill, chapter, proj)
        if Path(p).exists() and Path(p).stat().st_size > 0
    ]
    # M8: use derived file_type instead of hardcoded "chapter".
    file_type = derive_file_type(skill)
    # Safety fallback: when chapter is unknown (non-pipeline T2), fall back to
    # rglob. CRITICAL: the fallback file_type must match what rglob finds (.md).
    # If derive_file_type returns "decisions" but rglob only finds .md files,
    # G2's decisions branch would json.loads() markdown → crash. So the fallback
    # must use file_type="chapter" (the type for .md files).
    if not output_files and chapter is None:
        output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
        file_type = "chapter"  # override: rglob finds .md, not decisions.json
    g2_status = GateStatus.SKIP.value
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), file_type, str(round_dir)])
        g2_status = g2.get("status", GateStatus.FAIL.value)
```

(The caller update is already done above — the `post-skill` dispatch at line 304-306 now passes `chapter=chapter`.)

**Why this works**: The pipeline driver already knows the chapter (it passes "for chapter N" in prompts to `dispatch_helper`). Now it passes `--chapter N` to `phase_runner post-skill` explicitly. In T2 test mode (no pipeline), `--chapter` is absent (None), and the rglob fallback with `file_type="chapter"` preserves backward compatibility — .md files are validated as chapters, which is correct.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_phase_runner.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/phase_runner.py tests/unit/test_phase_runner.py
git commit -m "feat: phase_runner uses derive_output_files + derive_file_type (M5+M8)"
```

---

### Task 6: dispatch_helper Multi-File Output Format (M6)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:228-232` (add multi-file reminder when `len(output_paths) > 1`)
- Test: `tests/unit/pipeline/test_dispatch_helper.py` (extend)

**Interfaces:**
- Produces: when contract has >1 writes, the user prompt includes a reminder about decisions.json schema conformance

- [ ] **Step 1: Write failing test**

```python
# Append to tests/unit/pipeline/test_dispatch_helper.py

class TestMultiFileOutputFormat:
    """M6: when contract has multiple writes, prompt reminds about schema."""

    def test_multi_file_prompt_includes_schema_reminder(self, tmp_path, monkeypatch):
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt
        from shenbi.contracts import OutputKind

        # Mock contract with 2 writes (chapter.md + decisions.json)
        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["chapters/chapter-1.md", "chapters/chapter-1-decisions.json"],
            "updates": [],
            "read_fields": {},
        }
        monkeypatch.setattr(
            "shenbi.pipeline.dispatch_helper.load_contract",
            lambda s: mock_contract,
        )

        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
        )

        assert len(output_paths) == 2
        assert "shenbi-decisions-v1" in user_prompt
        assert "decisions-schema.md" in user_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::TestMultiFileOutputFormat -v`
Expected: FAIL — no schema reminder in prompt

- [ ] **Step 3: Add multi-file reminder to `_build_skill_prompt`**

In `src/shenbi/pipeline/dispatch_helper.py`, after line 232 (`user_parts.append(f"- {p}")`), add:

```python
    if len(output_paths) > 1:
        user_parts.append(
            "\nNote: This skill produces multiple files. "
            "Decisions JSON must conform to shenbi-decisions-v1 schema "
            "(see docs/framework/decisions-schema.md)."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: add multi-file output schema reminder to dispatch_helper (M6)"
```

---

### Task 7: Decisions Schema Document (M7)

**Files:**
- Create: `docs/framework/decisions-schema.md`

**Interfaces:**
- Produces: single source of truth for schema version, fields, enums, per-skill differences. Referenced by G4 validation and skill authors.

- [ ] **Step 1: Write the schema document**

```markdown
# Decisions Schema v1

**Version**: `shenbi-decisions-v1`
**Status**: Active (spec 2026-07-07-clean-context-handoff-design.md, Layer A)

## Purpose

Decisions-sidecar artifacts (`*-decisions.json`) persist structured decision
summaries that downstream skills read as lightweight references (Anthropic
"artifact + lightweight reference" pattern). This document is the single
source of truth for the schema.

## Schema

\`\`\`json
{
  "$schema": "shenbi-decisions-v1",
  "skill": "shenbi-context-composing",
  "chapter": 5,
  "produced_at": "2026-07-07T12:00:00Z",
  "selections": [
    {
      "target": "truth/chapter_summaries.md",
      "selected": ["ch1", "ch2"],
      "basis": "adjacent_to_target_chapter",
      "severity": "low",
      "omitted": []
    }
  ],
  "adjustments": [
    {
      "issue_id": "drift_003",
      "severity": "medium",
      "handling": "compensate_via_pacing",
      "rationale": "drift absorbed by plan pacing"
    }
  ],
  "budget": {
    "context_tokens_estimate": 8500,
    "limit": 12000,
    "trim_applied": "none"
  }
}
\`\`\`

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$schema` | string | yes | Must be `shenbi-decisions-v1` |
| `skill` | string | yes | Skill name that produced this file |
| `chapter` | int | yes | Chapter number |
| `produced_at` | string | yes | ISO 8601 timestamp |
| `selections` | array | yes | List of selection decisions |
| `adjustments` | array | no | Drift/conflict adjustments |
| `budget` | object | no | Context budget tracking |

## Enums

### `selections[].basis`
- `adjacent_to_target_chapter` (routine)
- `arc_relevance` (routine)
- `volume_scope` (routine)
- `manual_override` (anomaly)

### `selections[].severity`
- `low` (default — rationale forbidden)
- `high` (P2.5 escape hatch — rationale required)

### `adjustments[].handling`
- `compensate_via_pacing`
- `explicit_callout`
- `defer_to_next_chapter`
- `ignore`

### `budget.trim_applied`
- `none`
- `oldest_first`
- `lowest_relevance`
- `manual`

## P2.5 Rationale Rules

| Condition | rationale field |
|-----------|----------------|
| routine basis + severity `low` | **FORBIDDEN** |
| routine basis + severity `high` | **REQUIRED** |
| `manual_override` (any severity) | **REQUIRED** |
| `adjustments[]` (any) | **REQUIRED** |
| rationale present | ≤100 chars |

## Per-Skill Differences

| Skill | selections targets | adjustments type |
|-------|-------------------|-----------------|
| `context-composing` | truth files, world/rules, chapters | drift, budget trims |
| `market-radar` | market data, trend signals | trend exceptions |
| `chapter-drafting` | plan beats, foreshadowing | pacing deviations, opening |
| `chapter-planning` | arc elements, beats | plan deviations |
| `chapter-revision` | review issues, strategies | deferred issues |
| `state-settling` | state deltas, summaries | conflicts, resolutions |
| `short-drafting` | outline elements, structure | length, tone shifts |
```

- [ ] **Step 2: Commit**

```bash
git add docs/framework/decisions-schema.md
git commit -m "docs: add decisions-schema.md single source of truth (M7)"
```

---

### Task 8: context-composing + market-radar Skill Migration

**Files:**
- Modify: `skills/shenbi-context-composing/SKILL.md` (frontmatter: kind→artifact, add decisions.json to writes)
- Modify: `skills/shenbi-market-radar/SKILL.md` (frontmatter: kind→artifact, add decisions.json to writes)

**Interfaces:**
- Produces: both skills now `kind: artifact` with `writes` including a decisions.json path

- [ ] **Step 1: Modify context-composing frontmatter**

In `skills/shenbi-context-composing/SKILL.md`, change the frontmatter:

```yaml
# Before:
contract:
  kind: ephemeral
  reads:
    - plans/chapter-N-plan.md
    # ... (existing reads)
  writes: []
  updates: []

# After:
contract:
  kind: artifact
  reads:
    - plans/chapter-N-plan.md
    # ... (existing reads unchanged)
  writes:
    - context/chapter-N-context-decisions.json
  updates: []
```

- [ ] **Step 2: Modify market-radar frontmatter**

In `skills/shenbi-market-radar/SKILL.md`, change the frontmatter:

```yaml
# Before:
contract:
  kind: ephemeral
  reads:
    # ... (existing reads)
  writes: []
  updates: []

# After:
contract:
  kind: artifact
  reads:
    # ... (existing reads unchanged)
  writes:
    - context/market-radar-decisions.json
  updates: []
```

Note: `context/market-radar-decisions.json` is not chapter-parametric. Register it in truth-files.yaml if it's not already covered by a glob. If it doesn't match existing globs, add a new concept:

```yaml
  - {name: context/market-radar-decisions.json, kind: decisions}
```

- [ ] **Step 3: Run contract validation**

Run: `pytest tests/unit/contract/ -v`
Expected: PASS — new writes paths resolve in registry

- [ ] **Step 4: Run derive_file_type test**

Run: `pytest tests/unit/test_dispatcher_executor.py::test_derive_file_type_returns_decisions_for_context_composing_after_migration -v`
Expected: PASS (the monkeypatched test from Task 3 simulates this; now verify the real skill also works)

Run: `python -c "from shenbi.dispatcher.executor import derive_file_type; print(derive_file_type('shenbi-context-composing'))"`
Expected: `decisions`

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-context-composing/SKILL.md skills/shenbi-market-radar/SKILL.md docs/framework/truth-files.yaml site/framework/truth-files.yaml
git commit -m "feat: migrate context-composing + market-radar to artifact kind with decisions.json"
```

---

## Phase 2 — Natural-Language Artifact Skills (Tasks 9-12)

### Task 9: PRE_WRITE_CHECK Overlap Audit (Verifiable Gate)

**Files:**
- Create: `tests/unit/gates/test_pre_write_check_overlap.py`
- Investigate: `skills/shenbi-chapter-drafting/SKILL.md`, `skills/shenbi-chapter-planning/SKILL.md`, `skills/shenbi-chapter-revision/SKILL.md`, `skills/shenbi-state-settling/SKILL.md`, `skills/shenbi-short-drafting/SKILL.md`

**Interfaces:**
- Produces: a test that verifies which skills have PRE_WRITE_CHECK/POST_WRITE_SELF_CHECK embedded mechanisms, documented as a passing test. This is a verifiable gate — the test must pass before Task 10 proceeds.

- [ ] **Step 1: Write a test that audits embedded intent mechanisms**

```python
# tests/unit/gates/test_pre_write_check_overlap.py
"""Audit: which NL-artifact skills have embedded PRE_WRITE_CHECK/POST_WRITE_SELF_CHECK?

This test documents the overlap between existing embedded intent mechanisms
and the proposed decisions.json sidecar (Layer A). It must pass before Task 10
proceeds — the results inform whether decisions.json is redundant or complementary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"

NL_ARTIFACT_SKILLS = [
    "shenbi-chapter-drafting",
    "shenbi-chapter-planning",
    "shenbi-chapter-revision",
    "shenbi-state-settling",
    "shenbi-short-drafting",
]


@pytest.mark.unit
class TestPreWriteCheckOverlap:
    def test_audit_embedded_mechanisms(self) -> None:
        """Document which skills have PRE_WRITE_CHECK / POST_WRITE_SELF_CHECK.
        This test PASSES by documenting the current state — it's an audit, not
        a pass/fail gate on the presence of mechanisms.
        """
        results: dict[str, dict[str, bool]] = {}
        for skill in NL_ARTIFACT_SKILLS:
            skill_md = SKILLS_DIR / skill / "SKILL.md"
            if not skill_md.exists():
                results[skill] = {"exists": False, "pre_write_check": False, "post_write_self_check": False}
                continue
            content = skill_md.read_text(encoding="utf-8")
            results[skill] = {
                "exists": True,
                "pre_write_check": "PRE_WRITE_CHECK" in content,
                "post_write_self_check": "POST_WRITE_SELF_CHECK" in content,
            }

        # Document findings — this test always passes, it's an audit record.
        # The implementer must review the results and decide for each skill:
        # - If PRE_WRITE_CHECK captures the SAME intent as decisions.json → redundant, consider conditional
        # - If decisions.json captures DIFFERENT intent (pacing, foreshadowing) → complementary, proceed
        print("\n=== PRE_WRITE_CHECK Overlap Audit ===")
        for skill, findings in results.items():
            print(f"  {skill}: {findings}")
        assert len(results) == len(NL_ARTIFACT_SKILLS)
```

- [ ] **Step 2: Run test to see the audit results**

Run: `pytest tests/unit/gates/test_pre_write_check_overlap.py -v -s`
Expected: PASS — review the printed audit table to determine overlap

- [ ] **Step 3: Document the decision in spec Open Question #4**

Based on the audit results, update `docs/superpowers/specs/2026-07-07-clean-context-handoff-design.md` Open Question #4 with:
- Which skills have PRE_WRITE_CHECK
- For each: is decisions.json redundant or complementary?
- Decision: proceed with all 5, or narrow scope

- [ ] **Step 4: Commit**

```bash
git add tests/unit/gates/test_pre_write_check_overlap.py docs/superpowers/specs/2026-07-07-clean-context-handoff-design.md
git commit -m "test: add PRE_WRITE_CHECK overlap audit gate (Task 9)"
```

---

### Task 10: chapter-drafting + chapter-planning Decisions Migration

**Files:**
- Modify: `skills/shenbi-chapter-drafting/SKILL.md` (add `chapters/chapter-N-decisions.json` to writes; add `context/chapter-N-context-decisions.json` to reads)
- Modify: `skills/shenbi-chapter-planning/SKILL.md` (add `plans/chapter-N-plan-decisions.json` to writes; add dict-form reads)

**Interfaces:**
- Produces: both skills now produce decisions.json; chapter-drafting reads context-composing's decisions.json

- [ ] **Step 1: Register new decisions paths in truth-files.yaml**

In both `docs/framework/truth-files.yaml` and `site/framework/truth-files.yaml`, add (if not already added in Task 8):

```yaml
concepts:
  - {name: plans/chapter-N-plan-decisions.json, kind: decisions}
patterns:
  - {parametric: plans/chapter-N-plan-decisions.json, glob: plans/chapter-*-plan-decisions.json}
globs:
  - {pattern: plans/chapter-*-plan-decisions.json}
```

- [ ] **Step 2: Modify chapter-drafting frontmatter**

In `skills/shenbi-chapter-drafting/SKILL.md`:

```yaml
# Before:
contract:
  kind: artifact
  reads:
    - plans/chapter-N-plan.md
    - context/chapter-N-context.md
    - style/style_profile.md
    - genre-config.json
    - truth/audit_drift.md
  writes:
    - chapters/chapter-N.md
  updates: []

# After:
contract:
  kind: artifact
  reads:
    - plans/chapter-N-plan.md
    - context/chapter-N-context.md
    - context/chapter-N-context-decisions.json   # NEW: read upstream decisions
    - style/style_profile.md
    - genre-config.json
    - truth/audit_drift.md
  writes:
    - chapters/chapter-N.md
    - chapters/chapter-N-decisions.json           # NEW: persist drafting decisions
  updates: []
```

- [ ] **Step 3: Modify chapter-planning frontmatter**

In `skills/shenbi-chapter-planning/SKILL.md`, add `plans/chapter-N-plan-decisions.json` to writes.

- [ ] **Step 4: Run contract validation**

Run: `pytest tests/unit/contract/ -v && python -c "from shenbi.dispatcher.executor import derive_file_type; print(derive_file_type('shenbi-chapter-drafting'))"`
Expected: PASS, `decisions`

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-chapter-drafting/SKILL.md skills/shenbi-chapter-planning/SKILL.md docs/framework/truth-files.yaml site/framework/truth-files.yaml
git commit -m "feat: add decisions.json to chapter-drafting + chapter-planning writes/reads"
```

---

### Task 11: chapter-revision + state-settling + short-drafting Decisions Migration

**Files:**
- Modify: `skills/shenbi-chapter-revision/SKILL.md`, `skills/shenbi-state-settling/SKILL.md`, `skills/shenbi-short-drafting/SKILL.md`

**Interfaces:**
- Produces: all 3 skills now produce decisions.json; chapter-revision reads chapter-drafting's decisions.json

- [ ] **Step 1: Modify chapter-revision frontmatter**

Add `chapters/chapter-N-revision-decisions.json` to writes. Add `chapters/chapter-N-decisions.json` to reads (revision needs drafting intent).

Register `chapters/chapter-N-revision-decisions.json` in truth-files.yaml if the `chapters/chapter-*-decisions.json` glob doesn't cover it (it should — the glob is `chapters/chapter-*-decisions.json` which matches `chapter-N-revision-decisions.json`? **No** — the glob `chapters/chapter-*-decisions.json` matches `chapters/chapter-5-decisions.json` but NOT `chapters/chapter-5-revision-decisions.json` because of the `-revision` infix). Add a new concept + glob:

```yaml
  - {name: chapters/chapter-N-revision-decisions.json, kind: decisions}
  - {pattern: chapters/chapter-*-revision-decisions.json}
```

- [ ] **Step 2: Modify state-settling frontmatter**

Add `truth/state-settling-decisions.json` to writes. Register if needed.

- [ ] **Step 3: Modify short-drafting frontmatter**

Add `short/short-N-decisions.json` to writes. Register in truth-files.yaml.

- [ ] **Step 4: Run contract validation**

Run: `pytest tests/unit/contract/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-chapter-revision/SKILL.md skills/shenbi-state-settling/SKILL.md skills/shenbi-short-drafting/SKILL.md docs/framework/truth-files.yaml site/framework/truth-files.yaml
git commit -m "feat: add decisions.json to chapter-revision + state-settling + short-drafting"
```

---

### Task 12: G4 Decisions Schema Validation

**Files:**
- Create: `src/shenbi/gates/g4/decisions_validator.py`
- Modify: `src/shenbi/gates/g4/generic.py` (register checker)
- Test: `tests/unit/gates/test_g4_decisions.py`

**Interfaces:**
- Produces: `g4_decisions(fps, rd) -> str` — validates decisions.json schema (enums, P2.5 rules, required keys)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/gates/test_g4_decisions.py
"""Unit tests for G4 decisions schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.decisions_validator import g4_decisions


@pytest.mark.unit
class TestG4DecisionsValidation:
    def test_valid_decisions_passes(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {"target": "truth/audit_drift.md", "selected": ["drift_1"],
                 "basis": "adjacent_to_target_chapter", "severity": "low", "omitted": []}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "PASS"

    def test_routine_low_severity_with_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {"target": "truth/audit_drift.md", "selected": ["drift_1"],
                 "basis": "arc_relevance", "severity": "low", "omitted": [],
                 "rationale": "should not be here"}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_manual_override_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {"target": "world/rules.md", "selected": ["rule_1"],
                 "basis": "manual_override", "severity": "low", "omitted": ["rule_2"]}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_high_severity_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [
                {"target": "truth/arcs/arc-N.md", "selected": ["climax"],
                 "basis": "arc_relevance", "severity": "high", "omitted": []}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"

    def test_adjustment_without_rationale_fails(self, tmp_path: Path) -> None:
        decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-context-composing",
            "chapter": 5,
            "produced_at": "2026-07-07T12:00:00Z",
            "selections": [],
            "adjustments": [
                {"issue_id": "drift_1", "severity": "medium",
                 "handling": "compensate_via_pacing"}
            ],
        }
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(decisions), encoding="utf-8")
        result = g4_decisions([str(fp)])
        data = json.loads(result)
        assert data["status"] == "FAIL"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/gates/test_g4_decisions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `g4_decisions`**

```python
# src/shenbi/gates/g4/decisions_validator.py
"""G4 checker for decisions.json schema validation (Layer A)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from shenbi.gates.shared import fail, passed
from shenbi.gates.g4._decisions_schema import (
    DECISIONS_SCHEMA_VERSION,
    validate_selection_rationale,
    validate_adjustment_rationale,
)


def g4_decisions(fps: list[str], rd: str | None = None) -> str:
    """Validate decisions.json against shenbi-decisions-v1 schema + P2.5 rules.

    Only processes *.json files — non-JSON files (e.g., the main .md artifact
    passed by composite checkers) are silently skipped. This prevents crashes
    when g4_decisions is used as the decisions_checker in a composite that
    receives all skill outputs including markdown.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    base = Path(rd) if rd else Path.cwd()

    for fp in fps or []:
        p = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not p.exists():
            mf.append(f"G4.dec.not_found:{fp}")
            continue

        # CRITICAL: skip non-JSON files — the composite checker passes ALL skill
        # outputs (including .md artifacts). json.loads() on markdown would crash.
        if not fp.endswith(".json"):
            continue  # skip .md and other non-decisions files

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            mf.append(f"G4.dec.invalid_json:{fp}")
            continue

        # Schema version
        if data.get("$schema") != DECISIONS_SCHEMA_VERSION:
            mf.append(f"G4.dec.schema_version:{fp}:{data.get('$schema')}")

        # Required keys
        required = {"skill", "chapter", "selections", "produced_at"}
        missing = required - data.keys()
        if missing:
            mf.append(f"G4.dec.missing_keys:{fp}:{missing}")

        # Validate selections (P2.5)
        for i, sel in enumerate(data.get("selections", [])):
            errors = validate_selection_rationale(
                basis=sel.get("basis", ""),
                severity=sel.get("severity", "low"),
                rationale=sel.get("rationale"),
            )
            for err in errors:
                mf.append(f"G4.dec.selection[{i}]:{fp}:{err}")

        # Validate adjustments (always require rationale)
        for i, adj in enumerate(data.get("adjustments", [])):
            errors = validate_adjustment_rationale(adj.get("rationale"))
            for err in errors:
                mf.append(f"G4.dec.adjustment[{i}]:{fp}:{err}")

        c.append({"id": "G4.dec", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.dec", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-decisions", c, "scoring", mf)
    return passed("G4-decisions", c)
```

- [ ] **Step 4: Register `g4_decisions` in the G4 dispatcher (composite, not override)**

**Critical**: 4 of the 7 Layer A skills already have dedicated G4 checkers in `generic.py:187-216`:
- `shenbi-context-composing` → `g4_context_composing`
- `shenbi-chapter-drafting` → `g4_chapter_drafting`
- `shenbi-chapter-planning` → `g4_chapter_planning`
- `shenbi-state-settling` → `g4_state_settling`

Directly replacing these with `g4_decisions` would lose the existing structural validation (section titles, P1+P2 non-empty, etc.) — a shipped regression on a quality gate. Instead, create **composite checkers** that run both the existing checker and the decisions validator.

In `src/shenbi/gates/g4/decisions_validator.py`, add a composite helper at the end of the file:

```python
G4CheckerFn = Callable[[list[str], str | None], str]


def make_composite_checker(
    existing_checker: G4CheckerFn, decisions_checker: G4CheckerFn
) -> G4CheckerFn:
    """Create a composite G4 checker that runs both existing + decisions validation.

    Returns FAIL if either checker fails; aggregates all checks and must_fix items.
    Both checkers always run (even if the first fails) to collect all failures.
    """
    def composite(fps: list[str], rd: str | None = None) -> str:
        import json

        existing_result = existing_checker(fps, rd)
        decisions_result = decisions_checker(fps, rd)

        # Parse both results and aggregate.
        # CRITICAL: fail() emits key "must_fix" (not "failures") — see shared.py:113.
        try:
            existing_data = json.loads(existing_result)
        except (json.JSONDecodeError, TypeError):
            existing_data = {"status": "FAIL", "checks": [], "must_fix": ["unparseable"]}
        try:
            decisions_data = json.loads(decisions_result)
        except (json.JSONDecodeError, TypeError):
            decisions_data = {"status": "FAIL", "checks": [], "must_fix": ["unparseable"]}

        combined_checks = existing_data.get("checks", []) + decisions_data.get("checks", [])
        combined_must_fix = (
            existing_data.get("must_fix", []) + decisions_data.get("must_fix", [])
        )

        if combined_must_fix:
            return fail(
                f"G4-composite-{existing_checker.__name__}",
                combined_checks,
                "scoring",
                combined_must_fix,
            )
        return passed(f"G4-composite-{existing_checker.__name__}", combined_checks)
    return composite
```

In `src/shenbi/gates/g4/generic.py`, add the import after line 185:

```python
    from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker
```

In the `checkers` dict, **replace** the 4 existing entries with composites, and **add** the 3 new ones:

```python
        # Composite: existing structural check + decisions validation
        "shenbi-context-composing": make_composite_checker(g4_context_composing, g4_decisions),
        "shenbi-chapter-drafting": make_composite_checker(g4_chapter_drafting, g4_decisions),
        "shenbi-chapter-planning": make_composite_checker(g4_chapter_planning, g4_decisions),
        "shenbi-state-settling": make_composite_checker(g4_state_settling, g4_decisions),
        # New: decisions-only (no existing dedicated checker)
        "shenbi-market-radar": g4_decisions,
        "shenbi-chapter-revision": g4_decisions,
        "shenbi-short-drafting": g4_decisions,
```

**Why composite, not override**: the existing checkers validate the main artifact's structure (e.g., context-composing's P1-P7 section titles, chapter-drafting's PRE_WRITE_CHECK). The decisions validator validates the sidecar JSON. Both must pass — losing either is a quality-gate regression. The composite runs both and fails if either fails.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/gates/test_g4_decisions.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/g4/decisions_validator.py src/shenbi/gates/g4/generic.py tests/unit/gates/test_g4_decisions.py
git commit -m "feat: add G4 decisions schema validator with P2.5 rules"
```

---

## Phase 3 — Layer B Field-Level Reads (Tasks 13-16)

### Task 13: Implement `_filter_to_fields` in dispatch_helper

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add `_filter_to_fields`, `_extract_h2_sections`, `_project_json_keys`; wire into `_build_skill_prompt`)
- Test: `tests/unit/pipeline/test_field_filtering.py`

**Interfaces:**
- Produces: `_filter_to_fields(text: str, fields: list[str], path: str) -> str`, `_extract_h2_sections(text, fields) -> str`, `_project_json_keys(text, fields) -> str`
- Modifies: `_build_skill_prompt` now consumes `contract["read_fields"]` and filters file content

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_field_filtering.py
"""Unit tests for Layer B field-level filtering (B.1)."""

from __future__ import annotations

import json

import pytest

from shenbi.pipeline.dispatch_helper import (
    _filter_to_fields,
    _extract_h2_sections,
    _project_json_keys,
)


@pytest.mark.unit
class TestExtractH2Sections:
    def test_extracts_declared_h2_sections(self) -> None:
        text = """# File

## chapter_goal
Do the thing.

## beats
Beat 1, Beat 2.

## unused_section
Should not appear.
"""
        result = _extract_h2_sections(text, ["chapter_goal", "beats"])
        assert "chapter_goal" in result
        assert "Do the thing" in result
        assert "beats" in result
        assert "Beat 1" in result
        assert "unused_section" not in result

    def test_returns_full_text_when_no_fields_match(self) -> None:
        """Escape hatch: no declared field found → return full text."""
        text = "## some_other_section\ncontent"
        result = _extract_h2_sections(text, ["nonexistent_field"])
        assert result == text  # fallback to full text

    def test_empty_fields_returns_full_text(self) -> None:
        text = "## anything\ncontent"
        result = _extract_h2_sections(text, [])
        assert result == text


@pytest.mark.unit
class TestProjectJsonKeys:
    def test_projects_declared_keys(self) -> None:
        data = {"a": 1, "b": 2, "c": 3}
        text = json.dumps(data)
        result = _project_json_keys(text, ["a", "c"])
        projected = json.loads(result)
        assert projected == {"a": 1, "c": 3}
        assert "b" not in projected

    def test_returns_full_text_when_no_keys_match(self) -> None:
        """Escape hatch: no declared key found → return full text."""
        data = {"x": 1}
        text = json.dumps(data)
        result = _project_json_keys(text, ["nonexistent"])
        assert result == text  # fallback

    def test_invalid_json_returns_full_text(self) -> None:
        """Escape hatch: invalid JSON → return original text."""
        result = _project_json_keys("not json", ["a"])
        assert result == "not json"


@pytest.mark.unit
class TestFilterToFields:
    def test_markdown_filter(self) -> None:
        text = "## goal\ncontent"
        result = _filter_to_fields(text, ["goal"], "plans/chapter-1-plan.md")
        assert "goal" in result

    def test_json_filter(self) -> None:
        text = json.dumps({"a": 1, "b": 2})
        result = _filter_to_fields(text, ["a"], "genre-config.json")
        projected = json.loads(result)
        assert "a" in projected
        assert "b" not in projected

    def test_unknown_extension_no_filter(self) -> None:
        text = "some content"
        result = _filter_to_fields(text, ["field"], "file.txt")
        assert result == text  # safe default: no filtering
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/pipeline/test_field_filtering.py -v`
Expected: FAIL — functions don't exist

- [ ] **Step 3: Implement filtering functions**

In `src/shenbi/pipeline/dispatch_helper.py`, add these functions before `_build_skill_prompt` (before line 117):

```python
def _extract_h2_sections(text: str, fields: list[str]) -> str:
    """Extract H2 sections whose heading matches a declared field name.

    Returns concatenated sections. If no fields match, returns full text
    (escape hatch — prevents silent information loss).
    """
    if not fields:
        return text

    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = current_body
            # Normalize heading: strip "## " prefix and trim whitespace ONLY.
            # Do NOT lowercase or translate — real truth files use Chinese
            # headings (## 主角, ## 主角情感弧线). Field declarations must use
            # the actual heading text. See spec B.3.
            raw = line[3:].strip()
            current_heading = raw
            current_body = [line]
        elif current_heading is not None:
            current_body.append(line)

    if current_heading is not None:
        sections[current_heading] = current_body

    # Match declared fields against headings (exact match, no normalization).
    # Fields must be declared using the real heading text (Chinese or English).
    # This is consistent with G1's check_fields_exist which uses set difference.
    matched: list[str] = []
    for field in fields:
        if field in sections:
            matched.extend(sections[field])

    if not matched:
        # Escape hatch: no declared field found → return full text
        log.warning("field_filter_no_match", fields=fields, available=list(sections.keys()))
        return text

    return "\n".join(matched)


def _project_json_keys(text: str, fields: list[str]) -> str:
    """Project JSON to only declared top-level keys.

    Returns JSON string with only declared keys. If no keys match or
    JSON is invalid, returns original text (escape hatch).
    """
    if not fields:
        return text

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        log.warning("field_filter_invalid_json")
        return text

    if not isinstance(data, dict):
        return text

    projected = {k: v for k, v in data.items() if k in fields}

    if not projected:
        # Escape hatch: no declared key found → return full text
        log.warning("field_filter_no_json_keys", fields=fields, available=list(data.keys()))
        return text

    return json.dumps(projected, ensure_ascii=False, indent=2)


def _filter_to_fields(text: str, fields: list[str], path: str) -> str:
    """Filter file content to only declared fields.

    - markdown: extract H2 sections matching field names
    - json: project to declared top-level keys
    - other: no filtering (safe default)

    Escape hatch: if no fields match, returns full text + logs WARN.
    """
    if not fields:
        return text

    if path.endswith(".md"):
        return _extract_h2_sections(text, fields)
    if path.endswith(".json"):
        return _project_json_keys(text, fields)
    return text  # unknown extension: no filtering
```

- [ ] **Step 4: Wire `read_fields` into `_build_skill_prompt`**

**Critical**: Replace **only** lines 149-161 (the read loop). Lines 162-191 contain the input budget/truncation logic (`_INPUT_MAX_CHARS_TOTAL`, `_INPUT_MAX_CHARS_PER_FILE`, proportional budgeting) which must be preserved. Replacing lines 149-191 would delete this safeguard and allow runaway inputs to blow the token budget.

In `_build_skill_prompt`, replace **only** lines 149-161 (the read loop, from `input_texts: dict[str, str] = {}` through the `else: raw_inputs[resolved] = ...` line). The truncation logic at lines 162-191 stays intact and consumes the `raw_inputs` dict:

```python
    # Read contract inputs with field-level filtering (Layer B)
    # Replaces only the read loop (lines 149-161). Truncation logic (162-191) stays.
    input_texts: dict[str, str] = {}
    raw_inputs: dict[str, str] = {}
    fields_map = contract.get("read_fields", {})   # Layer B: consume stored field map
    for read_path in contract.get("reads", []):
        resolved = _resolve_path(read_path, chapter)
        full_path = project_dir / resolved
        if full_path.exists():
            try:
                raw_text = full_path.read_text(encoding="utf-8")
            except Exception:
                raw_text = f"[binary or unreadable: {resolved}]"
            # Layer B: filter to declared fields if available
            fields = fields_map.get(resolved) or fields_map.get(read_path)
            if fields:
                raw_text = _filter_to_fields(raw_text, fields, resolved)
            raw_inputs[resolved] = raw_text
        else:
            raw_inputs[resolved] = f"[file not found: {resolved}]"
    # --- existing truncation logic at lines 162-191 continues from here, unchanged ---
    # It reads raw_inputs and applies _INPUT_MAX_CHARS_TOTAL / _INPUT_MAX_CHARS_PER_FILE
```

**What NOT to change**: The block starting with `# Apply per-file cap and proportional total budget` (line 162) through `input_texts[fname] = text` (line 191) must remain exactly as-is. It reads `raw_inputs` (which our modified loop populates) and produces `input_texts` (which the rest of `_build_skill_prompt` consumes). Our change only affects how `raw_inputs` is populated — filtering is applied before truncation, so truncated content is already field-filtered.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/pipeline/test_field_filtering.py -v`
Expected: all PASS

- [ ] **Step 6: Run existing dispatch_helper tests for regression**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: all PASS (existing tests don't use dict-form reads, so `read_fields` is empty, no filtering)

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_field_filtering.py
git commit -m "feat: implement Layer B field-level filtering with escape hatch"
```

---

### Task 14: G1 Soft Check for Field Existence (B.4)

**Files:**
- Modify: `src/shenbi/gates/g1.py` (add `check_fields_exist` function)
- Test: `tests/unit/gates/test_g1_fields.py`

**Interfaces:**
- Produces: `check_fields_exist(skill: str, inputs: list[str], fields_map: dict) -> list[str]` — returns WARN strings, non-blocking

- [ ] **Step 1: Write failing test**

```python
# tests/unit/gates/test_g1_fields.py
"""Unit tests for G1 field-existence soft check (B.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g1 import check_fields_exist


@pytest.mark.unit
class TestCheckFieldsExist:
    def test_warns_when_declared_field_missing_from_markdown(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("## chapter_goal\ndo the thing\n", encoding="utf-8")
        warnings = check_fields_exist(
            "shenbi-chapter-drafting",
            [str(fp)],
            {str(fp): ["chapter_goal", "nonexistent_field"]},
        )
        assert len(warnings) == 1
        assert "nonexistent_field" in warnings[0]

    def test_no_warning_when_all_fields_present(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("## chapter_goal\ndo the thing\n## beats\nbeat1\n", encoding="utf-8")
        warnings = check_fields_exist(
            "shenbi-chapter-drafting",
            [str(fp)],
            {str(fp): ["chapter_goal", "beats"]},
        )
        assert warnings == []

    def test_no_warning_when_no_fields_declared(self, tmp_path: Path) -> None:
        fp = tmp_path / "plan.md"
        fp.write_text("content", encoding="utf-8")
        warnings = check_fields_exist("shenbi-skill", [str(fp)], {})
        assert warnings == []

    def test_warns_when_json_key_missing(self, tmp_path: Path) -> None:
        import json
        fp = tmp_path / "config.json"
        fp.write_text(json.dumps({"a": 1}), encoding="utf-8")
        warnings = check_fields_exist(
            "shenbi-skill", [str(fp)], {str(fp): ["a", "missing_key"]}
        )
        assert len(warnings) == 1
        assert "missing_key" in warnings[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/test_g1_fields.py -v`
Expected: FAIL — `check_fields_exist` doesn't exist

- [ ] **Step 3: Implement `check_fields_exist` in g1.py**

Add to `src/shenbi/gates/g1.py`:

```python
def check_fields_exist(
    skill: str, inputs: list[str], fields_map: dict[str, list[str]]
) -> list[str]:
    """WARN (not FAIL) if declared fields not found in input files.

    Runs before _build_skill_prompt's filtering, so skill authors see
    field-name drift warnings before the LLM sees filtered content.
    Non-blocking — returns warning strings only.
    """
    warnings: list[str] = []
    for fp in inputs:
        fields = fields_map.get(fp) or fields_map.get(Path(fp).name)
        if not fields:
            continue
        p = Path(fp)
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        if fp.endswith(".md"):
            # Extract H2 headings
            actual = set()
            for line in content.splitlines():
                if line.startswith("## "):
                    raw = line[3:].strip().lower().replace(" ", "_")
                    actual.add(raw)
            missing = set(fields) - actual
            if missing:
                warnings.append(f"{fp}: declared fields {missing} not found in file")
        elif fp.endswith(".json"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    actual = set(data.keys())
                    missing = set(fields) - actual
                    if missing:
                        warnings.append(f"{fp}: declared keys {missing} not found in file")
            except json.JSONDecodeError:
                pass  # G1.2 already handles JSON parse errors
    return warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/test_g1_fields.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g1.py tests/unit/gates/test_g1_fields.py
git commit -m "feat: add G1 field-existence soft check (B.4)"
```

---

### Task 15: Add Dict-Form Reads to 12 Skills (Batch 1+2)

**Files:**
- Modify: 12 skill SKILL.md files (add `{file, fields}` dict-form to reads)

**Interfaces:**
- Produces: 12 skills now declare which fields they consume from each read file

- [ ] **Step 1: Batch 1 — 6 high-coupling skills**

For each of these skills, convert relevant `reads:` entries from plain strings to `{file, fields}` dict-form:

1. `skills/shenbi-context-composing/SKILL.md` — fields for truth files
2. `skills/shenbi-chapter-drafting/SKILL.md` — fields for plan, context, audit_drift
3. `skills/shenbi-chapter-planning/SKILL.md` — fields for outline, volume_map
4. `skills/shenbi-state-settling/SKILL.md` — fields for chapter, current_state
5. `skills/shenbi-foreshadowing-plant/SKILL.md` — fields for plan, pending_hooks
6. `skills/shenbi-foreshadowing-track/SKILL.md` — fields for plan, chapter

Example for chapter-drafting:

```yaml
# Before:
  reads:
    - plans/chapter-N-plan.md
    - context/chapter-N-context.md
    - context/chapter-N-context-decisions.json
    - style/style_profile.md
    - genre-config.json
    - truth/audit_drift.md

# After (fields use ACTUAL heading text from the file — Chinese where applicable):
  reads:
    - file: plans/chapter-N-plan.md
      fields: [本章核心任务, 要兑现的伏笔, 本章禁忌, 节奏区间]   # real H2 headings
    - context/chapter-N-context.md        # no fields = full read (context is curated)
    - context/chapter-N-context-decisions.json  # no fields = full read (decisions)
    - file: style/style_profile.md
      fields: [文风指纹, 语调参数]                               # real H2 headings
    - file: genre-config.json
      fields: [genre, sub_genre, pov_mode]                     # JSON keys (English)
    - file: truth/current_state.md
      fields: [主角状态, 当前世界局势, 活跃线索]                # verified real H2 headings
```

**Critical (C3 fix)**: Field declarations MUST use the actual heading text from the file. For markdown truth files, this means Chinese headings (`## 主角状态` → field `主角状态`), NOT English translations. For JSON files, use the actual top-level keys.

**Verified example**: `tests/fixtures/snapshots/chapter-025/truth/current_state.md` has these real H2 headings:
```
## 主角状态
## 当前世界局势
## 活跃线索
```
(verified via `grep "^## " tests/fixtures/snapshots/chapter-025/truth/current_state.md`)

Before writing field declarations for each skill, run this audit for every target truth file:

```bash
# Audit actual headings in each target truth file:
grep "^## " tests/fixtures/snapshots/chapter-025/truth/current_state.md
grep "^## " tests/fixtures/snapshots/chapter-025/truth/character_matrix.md
grep "^## " tests/fixtures/snapshots/chapter-025/truth/emotional_arcs.md
# etc. for each file the skill reads
```

Use the exact heading text returned by grep as the field name. Do NOT translate, lowercase, or snake_case. If a truth file doesn't exist in fixtures yet, skip it (no fields) rather than guessing heading names.

- [ ] **Step 2: Batch 2 — 6 medium-coupling skills**

Apply dict-form to:
1. `skills/shenbi-chapter-revision/SKILL.md`
2. `skills/shenbi-short-drafting/SKILL.md`
3. `skills/shenbi-style-polishing/SKILL.md`
4. `skills/shenbi-length-normalizing/SKILL.md`
5. `skills/shenbi-review-continuity/SKILL.md`
6. `skills/shenbi-review-pacing/SKILL.md`

- [ ] **Step 3: Run contract validation**

Run: `pytest tests/unit/contract/ -v`
Expected: PASS — dict-form is already supported by `_normalize_read_item`

- [ ] **Step 4: Run field filtering tests**

Run: `pytest tests/unit/pipeline/test_field_filtering.py tests/unit/gates/test_g1_fields.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/shenbi-*/SKILL.md
git commit -m "feat: add field-level dict-form reads to 12 skills (Layer B Batch 1+2)"
```

---

### Task 16: CI Lint — Contract Fields vs Truth File Consistency (B.5)

**Files:**
- Create: `scripts/lint_contract_fields.py`
- Modify: `justfile` (add `lint-contract-fields` target)

**Interfaces:**
- Produces: a script that scans all skills' contract reads dict-form fields and compares against actual truth file headings/keys

- [ ] **Step 1: Write the lint script**

```python
#!/usr/bin/env python3
"""Lint: contract.reads field declarations vs truth file actual headings/keys.

Scans all skills' contract.reads dict-form fields, reads the actual file,
and reports mismatches. Hooked into `just check` via `just lint-contract-fields`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROJECT_DIR = REPO_ROOT  # truth files live under project root


def extract_headings_md(text: str) -> set[str]:
    """Extract snake_cased H2 headings from markdown."""
    headings = set()
    for line in text.splitlines():
        if line.startswith("## "):
            raw = line[3:].strip().lower().replace(" ", "_")
            headings.add(raw)
    return headings


def extract_keys_json(text: str) -> set[str]:
    """Extract top-level keys from JSON."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return set(data.keys())
    except json.JSONDecodeError:
        pass
    return set()


def lint_skill(skill_dir: Path) -> list[str]:
    """Check one skill's contract reads fields against actual files."""
    issues: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return issues

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return issues
    parts = text.split("---", 2)
    if len(parts) < 3:
        return issues
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return issues

    contract = data.get("contract", {})
    reads = contract.get("reads", [])

    for item in reads:
        if isinstance(item, dict) and "file" in item:
            path = item["file"]
            fields = item.get("fields", [])
            if not fields:
                continue
            # Resolve parametric paths: convert chapter-N to a glob and find
            # a sample file on disk. This covers the majority of Layer B
            # declarations which are on chapter-parametric truth files.
            full_path = PROJECT_DIR / path
            if not full_path.exists():
                # Try resolving parametric path by finding a sample file
                import glob as _glob
                # Convert parametric patterns: N → *, NNN → *
                glob_pattern = path.replace("NNN", "*").replace("N", "*")
                glob_path = str(PROJECT_DIR / glob_pattern)
                matches = _glob.glob(glob_path)
                if matches:
                    full_path = Path(matches[0])  # check first sample
                else:
                    issues.append(f"{skill_dir.name}: {path} not found (no glob match)")
                    continue
            content = full_path.read_text(encoding="utf-8")
            if path.endswith(".md"):
                actual = extract_headings_md(content)
            elif path.endswith(".json"):
                actual = extract_keys_json(content)
            else:
                continue
            missing = set(fields) - actual
            if missing:
                issues.append(
                    f"{skill_dir.name}: {path} declares fields {missing} "
                    f"not found in file (actual: {sorted(actual)[:10]})"
                )
    return issues


def main() -> int:
    all_issues: list[str] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            all_issues.extend(lint_skill(skill_dir))

    if all_issues:
        print("Contract field mismatches found:", file=sys.stderr)
        for issue in all_issues:
            print(f"  {issue}", file=sys.stderr)
        return 1
    print("All contract field declarations match truth files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add justfile target**

In `justfile`, add:

```makefile
lint-contract-fields:
    uv run python scripts/lint_contract_fields.py
```

- [ ] **Step 3: Run the lint**

Run: `just lint-contract-fields`
Expected: either "All contract field declarations match" or a list of mismatches to fix

- [ ] **Step 4: Fix any mismatches**

If the lint reports mismatches, update the skill's `fields:` declarations to match actual truth file headings/keys.

- [ ] **Step 5: Commit**

```bash
git add scripts/lint_contract_fields.py justfile
git commit -m "feat: add contract fields lint script (B.5)"
```

---

## Phase 4 — Regression + Documentation (Tasks 17-18)

### Task 17: Full Regression Test Suite

**Files:**
- Run: all existing tests + new tests

- [ ] **Step 1: Run full test suite**

Run: `just check`
Expected: all PASS (ruff + mypy + basedpyright + pytest, ≥85% coverage)

- [ ] **Step 2: Run regression-specific tests**

Verify the T3 regression points from the spec:

```bash
# 53 unchanged skills' G2 still uses chapter/truth/report branches (68 total - 15 touched)
pytest tests/unit/test_dispatcher_executor.py -v

# phase_runner output discovery change (M5) doesn't affect existing skills
pytest tests/unit/test_phase_runner.py -v

# truth-files.yaml additions don't break existing resolve
pytest tests/unit/contract/ -v

# Clean-context invariant
pytest tests/unit/test_phase_runner_property.py -v
```

- [ ] **Step 3: Fix any regressions**

If any tests fail, fix the issue. Common regression points:
- `derive_file_type` returning "decisions" for a skill that shouldn't (check contract writes)
- G2 decisions branch triggering on non-decisions files (check file_type propagation)
- Field filtering removing needed content (check escape hatch is working)

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve regression issues from full test suite"
```

---

### Task 18: Update AGENTS.md + Finalize Documentation

**Files:**
- Modify: `AGENTS.md` (add decisions.json mechanism documentation)

- [ ] **Step 1: Add decisions.json section to AGENTS.md**

In the "### Skill Authoring" section, add:

```markdown
### Decisions-Sidecar Artifacts

Skills that produce natural-language or ephemeral outputs also produce a
`*-decisions.json` sidecar artifact (Layer A). This carries structured
decision summaries (selections, adjustments, budget) that downstream skills
read as lightweight references.

Key rules:
- `kind: ephemeral` skills migrate to `kind: artifact` with decisions.json in writes
- Schema: `shenbi-decisions-v1` (see `docs/framework/decisions-schema.md`)
- P2.5 rationale rule: rationale FORBIDDEN on routine+low-severity, REQUIRED on manual_override + high-severity + adjustments
- G2 validates decisions.json as `file_type="decisions"` (skips word count)
- G4 validates schema + P2.5 rules
- Downstream skills declare decisions.json in their `reads:`

### Field-Level Reads

Skills can declare which fields of a truth file they consume via dict-form
reads (Layer B):

```yaml
contract:
  reads:
    - file: truth/audit_drift.md
      fields: [active_drifts, severity, compensation_directives]
```

The dispatcher filters file content to only declared fields before the LLM
sees it (LangChain "filtered portions" strategy). If a declared field is
missing from the file, the escape hatch returns the full file + logs WARN.
```

- [ ] **Step 2: Final verification**

Run: `just check`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add decisions-sidecar + field-level reads to AGENTS.md"
```

---

## Self-Review

### Spec Coverage Check

| Spec Section | Task(s) |
|-------------|---------|
| M1+M2: truth-files.yaml registration | Task 2 |
| M3: derive_file_type decisions branch | Task 3 |
| M4: G2 decisions validation branch | Task 4 |
| M5: phase_runner output discovery | Task 5 |
| M6: dispatch_helper multi-file format | Task 6 |
| M7: decisions-schema.md | Task 7 |
| M8: phase_runner hardcoded file_type | Task 5 (combined with M5) |
| Layer A: 2 ephemeral skills | Task 8 |
| Layer A: 5 NL-artifact skills | Tasks 10, 11 |
| Open Question #4: PRE_WRITE_CHECK overlap | Task 9 |
| G4 decisions schema validation | Task 12 |
| Layer B: _filter_to_fields + escape hatch | Task 13 |
| Layer B: G1 soft check | Task 14 |
| Layer B: 12 skills dict-form reads | Task 15 |
| Layer B: CI lint | Task 16 |
| Regression tests | Task 17 |
| AGENTS.md documentation | Task 18 |

**Gaps found**: None — all spec sections covered.

### Placeholder Scan

Searched for: "TBD", "TODO", "implement later", "fill in details", "Add appropriate", "handle edge cases", "Similar to Task N".
- Task 9 (Open Question #4) intentionally has investigation steps without predetermined code — this is correct per the spec's deferral.
- Task 11 has a note about glob matching that needs verification during implementation — flagged honestly, not a placeholder.
- All code steps contain complete code.

### Type Consistency

- `validate_selection_rationale(basis: str, severity: str, rationale: str | None) -> list[str]` — consistent across Task 1 (definition) and Task 12 (usage in `g4_decisions`)
- `validate_adjustment_rationale(rationale: str | None) -> list[str]` — consistent
- `_filter_to_fields(text: str, fields: list[str], path: str) -> str` — consistent across Task 13 (definition) and B.1 spec
- `derive_file_type(skill: str) -> str` — consistent, returns "chapter"|"truth"|"report"|"decisions"
- `derive_output_files(skill, chapter, round_dir) -> list[str]` — consistent, signature verified against `executor.py:105`
- `g4_decisions(fps: list[str], rd: str | None = None) -> str` — consistent with existing G4 checker pattern (`g4_context_composing(fps, rd)`)
- `check_fields_exist(skill, inputs, fields_map) -> list[str]` — consistent across Task 14 (definition) and B.4 spec

No type inconsistencies found.
