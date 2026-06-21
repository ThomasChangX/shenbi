# Consistency: Single Source of Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the frontmatter `contract` block the single editable source for every skill's I/O, derive everything else (`expected_outputs`, DAG, registry index, body view) from it, and make each inconsistency class from the 2026-06-21 audit structurally impossible to land.

**Architecture:** A schema-validated `contract` block in each skill's frontmatter (typed `Contract` + `OutputKind` enum) is loaded by exactly one function (`contract.load_contract`) that also validates against a canonical file registry. A generator (`shenbi-sync-contracts`) derives deps.json `expected_outputs`, the producer/consumer DAG, the registry usage index, and an auto-rendered body view from the contracts; a set of pre-commit/CI lints forbid body restatement, a second parser, hand-edited generated artifacts, bare status strings, and banned terminology. Status vocabulary moves into typed `StrEnum`s + typed result structures so typos are type errors under mypy and basedpyright.

**Tech Stack:** Python 3.11, stdlib `enum.StrEnum` / `TypedDict`, PyYAML (already a dep), pytest (TDD), ruff + mypy + basedpyright (enforcement), `just` + pre-commit + GitHub Actions (checkpoints). No new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-06-21-consistency-single-source-design.md` (accepted rev 2).

---

## Conventions for every task

- **Run the failing test, watch it fail, implement, watch it pass, commit.** Never skip the red step.
- **Green gate before each commit:** `uv run ruff check . && uv run ruff format --check . && uv run mypy src/shenbi/ && uv run basedpyright` (the full `just check` also runs tests; use `just check` as the final verification in each task).
- **Commit messages** follow Conventional Commits (`feat:`, `refactor:`, `test:`, `chore:`).
- The repo's ruff config currently suppresses many rules per-directory for legacy code; **do not relax suppression lists** — if a new module needs a rule, it is a clean file that should pass without suppression. New files (`status.py`, `contract.py`, the generator, lints) MUST be clean (no per-file ignores added for them).
- Frontmatter is parsed today by `shared.yload` (verified: it correctly parses nested `contract:` keys). New loaders reuse `yload` or read frontmatter the same way.

## Scope / split note

This plan is sequenced into five Parts, each ending with a commit + green `just check` so each is independently mergeable:

- **Part I — Typed status vocabulary (audit D3).** Zero dependency on the contract work. *This is the clean split point* — if you want a separate PR/plan for D3, it is exactly Tasks 1–3.
- **Parts II–V — the contract single-source system (audit A, B, C, D1, D2, D4).**

Do Part I first: the contract rewire in Part II then naturally uses the new status enums.

---

# Part I — Typed status vocabulary (D3)

Fixes the `"status"` overload: gate result / phase state-machine / score classification all become typed `StrEnum`s in one module, emitted through typed result structures, so `"status": "PASSED"` is a type error (not a runtime risk) under **both** mypy and basedpyright.

Values are chosen to **equal the existing serialized strings**, so this Part is wire-compatible (no state-file or JSON-consumer migration).

---

### Task 1: Create `status.py` — enums + typed result structures

**Files:**
- Create: `src/shenbi/status.py`
- Test: `tests/unit/test_status.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_status.py`:

```python
"""Typed status vocabulary — enums serialize to the existing wire values."""
from __future__ import annotations

import pytest

from shenbi.status import (
    STATUS_STRING_LITERALS,
    CommandStatus,
    GateResult,
    GateStatus,
    PhaseState,
    ScoreClassification,
    ScoringStatus,
)


@pytest.mark.unit
class TestGateStatusWireValues:
    def test_pass_serializes_to_uppercase_pass(self) -> None:
        assert GateStatus.PASS.value == "PASS"
        assert str(GateStatus.PASS) == "PASS"

    def test_exhaustive_set(self) -> None:
        assert {g.value for g in GateStatus} == {"PASS", "FAIL", "SKIP", "WARN"}


@pytest.mark.unit
class TestPhaseStateWireValues:
    def test_preserves_existing_lowercase_values(self) -> None:
        """State files already on disk use lowercase; serialization must match."""
        assert PhaseState.CREATED.value == "created"
        assert PhaseState.SKILLS_DONE.value == "skills_done"
        assert {p.value for p in PhaseState} == {
            "created",
            "started",
            "skills_done",
            "scored",
            "finalized",
        }


@pytest.mark.unit
class TestCommandStatusWireValues:
    def test_values(self) -> None:
        assert {c.value for c in CommandStatus} == {"ok", "blocked", "error"}


@pytest.mark.unit
class TestScoringAndClassification:
    def test_scoring_status_values(self) -> None:
        assert ScoringStatus.REJECT.value == "REJECT"
        assert ScoringStatus.MARKER_MISSING.value == "MARKER_MISSING"

    def test_classification_strings_match_classifier_output(self) -> None:
        assert ScoreClassification.PASS_EXCELLENT.value == "PASS (excellent)"
        assert ScoreClassification.CONDITIONAL.value == "CONDITIONAL"


@pytest.mark.unit
class TestStatusStringLiteralSet:
    def test_set_is_complete_vocab(self) -> None:
        # The lint (Task 3) forbids these bare strings outside status.py.
        assert "PASS" in STATUS_STRING_LITERALS
        assert "created" in STATUS_STRING_LITERALS
        assert "REJECT" in STATUS_STRING_LITERALS
        assert "PASS (excellent)" in STATUS_STRING_LITERALS


@pytest.mark.unit
class TestGateResultTyped:
    def test_status_field_is_gate_status_typed(self) -> None:
        # A GateResult's status field carries a GateStatus member, not a bare str.
        result: GateResult = {
            "gate": "G1",
            "status": GateStatus.PASS,
            "timestamp": "2026-06-21T00:00:00Z",
            "checks": [],
        }
        assert result["status"] is GateStatus.PASS
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.status'`.

- [ ] **Step 3: Write the implementation**

`src/shenbi/status.py`:

```python
"""Typed status vocabulary + typed result structures (spec §5.2, audit D3).

THE single definition of every status string in the framework. Emit sites use
enum members through typed result structures, so ``"status": "PASSED"`` is a
static type error (not merely a runtime risk) under mypy AND basedpyright.

Wire compatibility: each enum's value equals the string the framework already
serializes, so this module changes no on-disk state files or JSON contracts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict


class GateStatus(StrEnum):
    """Result of a gate check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"


class PhaseState(StrEnum):
    """Phase state-machine states (values match existing phase-state/*.json)."""

    CREATED = "created"
    STARTED = "started"
    SKILLS_DONE = "skills_done"
    SCORED = "scored"
    FINALIZED = "finalized"


class CommandStatus(StrEnum):
    """phase_runner command outcome."""

    OK = "ok"
    BLOCKED = "blocked"
    ERROR = "error"


class ScoringStatus(StrEnum):
    """Scoring-pipeline outcome."""

    OK = "ok"
    REJECT = "REJECT"
    MARKER_MISSING = "MARKER_MISSING"
    UNIMPLEMENTED = "UNIMPLEMENTED"


class ScoreClassification(StrEnum):
    """classify() bucket for a final score."""

    PASS_EXCELLENT = "PASS (excellent)"
    PASS_ACCEPTABLE = "PASS (acceptable)"
    CONDITIONAL = "CONDITIONAL"
    FAIL = "FAIL"


class GateResult(TypedDict, total=False):
    """Typed envelope for a gate result. ``status`` carries a GateStatus member."""

    gate: str
    status: GateStatus
    timestamp: str
    checks: list[dict[str, Any]]
    blocked_action: str
    must_fix: list[str]


class CommandResult(TypedDict, total=False):
    """Typed envelope for a phase_runner command outcome."""

    status: CommandStatus
    phase: str
    skill: str
    action: str
    reads: list[str]
    writes: list[str]


# Every bare status string the framework emits. The lint in Task 3 forbids
# these as dict *values* outside this module, so a second source cannot land.
STATUS_STRING_LITERALS: frozenset[str] = frozenset(
    s.value
    for s in (
        *GateStatus,
        *PhaseState,
        *CommandStatus,
        *ScoringStatus,
        *ScoreClassification,
    )
)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_status.py -v`
Expected: PASS (all tests green).

- [ ] **Step 5: Verify type-checkers are clean**

Run: `uv run mypy src/shenbi/status.py && uv run basedpyright src/shenbi/status.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/status.py tests/unit/test_status.py
git commit -m "feat(status): typed status enums + GateResult (spec D3)"
```

---

### Task 2: Rewire emit sites to enum members

All status **emit** sites (where the framework *produces* a status value) use enum members via typed result structures. **Read comparisons on external JSON** (`result.get("status") == "FAIL"`) are NOT touched — they are not emit sites, they work correctly against the serialized string values, and churning them adds risk for zero benefit. Touched files today emit bare strings: `shared.py` (`passed`/`fail`/`unimplemented`), `scoring.py` (`classify`, result `status`), `phase_runner.py` (`status: ok/blocked/error`, the `g2_status`/`g4_status` default/fallback values that flow into emitted output).

**Files:**
- Modify: `src/shenbi/gates/shared.py:82-185` (`fail`, `passed`, `unimplemented`)
- Modify: `src/shenbi/scoring.py` (`classify`, `REJECT`/`MARKER_MISSING`/`UNIMPLEMENTED` emit sites)
- Modify: `src/shenbi/phase_runner.py:37,87,91,152-170,204,224,252` (state strings + command statuses)
- Test: `tests/unit/test_dispatcher_executor.py` (read comparisons stay valid), `tests/unit/test_phase_runner.py`

- [ ] **Step 1: Write a characterization test locking the wire values**

This is a behavior-preserving refactor (enum values equal the existing strings), so the test **characterizes** current output and must stay green before *and* after. The guard against *future* drift is the type-checker (this task) + the lint (Task 3). Add to `tests/unit/test_status.py`:

```python
@pytest.mark.unit
class TestSharedHelpersUseEnums:
    def test_passed_result_has_gate_status_pass(self) -> None:
        import json

        from shenbi.gates.shared import passed

        result = json.loads(passed("G1", [{"id": "G1.1", "s": "PASS"}]))
        assert result["status"] == GateStatus.PASS.value

    def test_fail_result_has_gate_status_fail(self) -> None:
        import json

        from shenbi.gates.shared import fail

        result = json.loads(fail("G1", [], "scoring", ["G1.0:x"]))
        assert result["status"] == GateStatus.FAIL.value
        assert result["blocked_action"] == "scoring"

    def test_unimplemented_result_status(self) -> None:
        import json

        from shenbi.gates.shared import unimplemented

        result = json.loads(unimplemented("G9"))
        assert result["status"] == ScoringStatus.UNIMPLEMENTED.value
```

- [ ] **Step 2: Run the test — it is GREEN (characterizing current behavior)**

Run: `uv run pytest tests/unit/test_status.py::TestSharedHelpersUseEnums -v`
Expected: PASS. (This is correct for a characterization test: it proves the refactor that follows changes no wire value. The genuine "red" for this task is the **type-checker** in Step 5 — once the emit sites are typed `GateResult`, a bare string like `"PASSED"` becomes a hard type error.)

- [ ] **Step 3: Rewire `shared.py` emit helpers to build typed `GateResult`**

Replace the bodies of `fail`, `passed`, `unimplemented` in `src/shenbi/gates/shared.py` so each constructs a `GateResult` using `GateStatus` / `ScoringStatus` members (add `from shenbi.status import GateResult, GateStatus, ScoringStatus` at the top of the file, after the existing imports). Keep the JSON-string return signature identical.

```python
def fail(gid: str, checks: list[dict[str, Any]], blocked: str, must_fix: list[str]) -> str:
    """Return FAIL JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.FAIL,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "blocked_action": blocked,
        "must_fix": must_fix,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def passed(gid: str, checks: list[dict[str, Any]]) -> str:
    """Return PASS JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.PASS,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def unimplemented(gate_name: str, note: str = "") -> str:
    """Return UNIMPLEMENTED JSON string for stub gates."""
    return json.dumps(
        {
            "gate": gate_name,
            "status": ScoringStatus.UNIMPLEMENTED,
            "note": note or f"{gate_name} not yet implemented — stub",
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": [],
        },
        indent=2,
        ensure_ascii=False,
    )
```

- [ ] **Step 4: Rewire `scoring.py`**

In `src/shenbi/scoring.py`: import `from shenbi.status import ScoreClassification, ScoringStatus`. Replace the `classify()` return literals (lines ~177–182) with members:

```python
def classify(score: float) -> ScoreClassification:
    if score >= 90:
        return ScoreClassification.PASS_EXCELLENT
    if score >= 75:
        return ScoreClassification.PASS_ACCEPTABLE
    if score >= 60:
        return ScoreClassification.CONDITIONAL
    return ScoreClassification.FAIL
```

Keep `is_valid = not any(e.startswith(ScoringStatus.REJECT.value) for e in errors)` so the error-prefix logic is unchanged. Replace the two result-dict emit sites (`"status": "MARKER_MISSING"` ~line 303, `"status": "REJECT"` ~line 356) with `ScoringStatus.MARKER_MISSING` and `ScoringStatus.REJECT`. Replace `"classification": classify(final)` with `"classification": classify(final).value` if `classify` now returns an enum and the field is serialized into JSON via `json.dumps` elsewhere — verify by grepping: `grep -n "classify(" src/shenbi/scoring.py` and ensure each call site serializes (`.value` or relies on `json.dumps` of the enum, which emits the value automatically because it is a `StrEnum`). `json.dumps(ScoreClassification.FAIL)` → `"FAIL"`, so no `.value` needed at json.dumps sites.

- [ ] **Step 5: Rewire `phase_runner.py`**

In `src/shenbi/phase_runner.py`: import `from shenbi.status import CommandStatus, PhaseState`. Replace:
- `return {"phase": phase, "state": "created", "steps": []}` (line 37) → `"state": PhaseState.CREATED`.
- `state["state"] = "started"` → `PhaseState.STARTED`; `"skills_done"` → `PhaseState.SKILLS_DONE`; `"scored"` → `PhaseState.SCORED`; `"finalized"` → `PhaseState.FINALIZED`. (These are dict values written via `json.dumps` to state files; `StrEnum` serializes to its value, so on-disk content is unchanged.)
- `emit_json({"status": "ok", ...})` → `{"status": CommandStatus.OK, ...}`; `"blocked"` → `CommandStatus.BLOCKED`; `"error"` → `CommandStatus.ERROR`.
- `g2_status = "SKIP"` / `g2.get("status", "UNKNOWN")` → default `"UNKNOWN"` becomes a real value: `g2_status = GateStatus.SKIP.value` and `g2.get("status", CommandStatus.ERROR.value)` (import `GateStatus`). The fallback for an unparseable gate result should be `CommandStatus.ERROR` (an explicit error path, not a bare `"UNKNOWN"`).

- [ ] **Step 6: Run the full unit suite + type-checkers**

Run: `uv run pytest tests/unit/ -n auto -q && uv run mypy src/shenbi/ && uv run basedpyright`
Expected: PASS, no type errors. (Read comparisons on external JSON like `result.get("status") == "FAIL"` are intentionally left as-is — they are not emit sites and work correctly; do not churn them.)

- [ ] **Step 7: Verify no behavior change in integration tests**

Run: `uv run pytest -n auto -m "not last" --hypothesis-profile=ci -q`
Expected: PASS (wire-compatible change).

- [ ] **Step 8: Commit**

```bash
git add src/shenbi/gates/shared.py src/shenbi/scoring.py src/shenbi/phase_runner.py tests/unit/test_status.py
git commit -m "refactor(status): emit sites use typed enums + GateResult (spec D3)"
```

---

### Task 3: Bare-status-string lint (backstop; both checkers)

The primary enforcement is the typed structures from Tasks 1–2. This lint is the backstop that makes a *second* bare-string source unlandable: it rejects a status-vocab string literal assigned to one of the three overloaded keys — **`"status"`** (gate/command/scoring result), **`"state"`** (phase state-machine), **`"classification"`** (score bucket) — outside `status.py`. The key-scope is essential: gate modules legitimately build check-item dicts like `{"id": "G3.1", "s": "PASS"}` (key `"s"`) by the thousand — flagging *any* status-valued dict literal would drown the lint in false positives. Restricting to these three keys targets only the result-envelope emit sites; read-comparisons (`== "FAIL"`) are not dict values so are not flagged.

**Files:**
- Create: `tools/lint_status_strings.py`
- Test: `tests/unit/test_lint_status_strings.py`
- Modify: `.pre-commit-config.yaml` (add local hook), `.github/workflows/ci.yml` (add step), `justfile` (add `lint-status` recipe)

- [ ] **Step 1: Write the failing test**

`tests/unit/test_lint_status_strings.py`:

```python
"""The bare-status-string lint flags status-vocab dict values outside status.py."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tools.lint_status_strings import find_violations


def _violations_in(source: str, filename: str = "x.py") -> list[str]:
    return find_violations(filename, ast.parse(source))


@pytest.mark.unit
def test_bare_pass_dict_value_outside_status_py_is_flagged() -> None:
    src = 'd = {"status": "PASS"}\n'
    assert any("PASS" in v for v in _violations_in(src, "src/shenbi/gates/g1.py"))


@pytest.mark.unit
def test_bare_state_and_classification_keys_are_flagged() -> None:
    """The three overloaded keys (status/state/classification) are all enforced."""
    assert _violations_in('d = {"state": "started"}\n', "src/shenbi/phase_runner.py")
    assert _violations_in('d = {"classification": "FAIL"}\n', "src/shenbi/scoring.py")


@pytest.mark.unit
def test_status_py_is_exempt() -> None:
    src = 'x = {"status": "PASS"}\n'
    assert _violations_in(src, "src/shenbi/status.py") == []


@pytest.mark.unit
def test_read_comparison_is_not_flagged() -> None:
    """Comparisons read external JSON; only the 'status' dict key is an emit site."""
    src = 'if result.get("status") == "FAIL":\n    pass\n'
    assert _violations_in(src, "src/shenbi/gates/g3.py") == []


@pytest.mark.unit
def test_check_item_s_value_is_not_flagged() -> None:
    """Gate check-item dicts use key 's' with status-like values by the
    thousand (e.g. {"id":"G3.1","s":"PASS"}). Only the 'status' key is flagged."""
    src = 'c.append({"id": "G3.1", "s": "PASS"})\n'
    assert _violations_in(src, "src/shenbi/gates/g3.py") == []


@pytest.mark.unit
def test_non_status_string_is_not_flagged() -> None:
    src = 'd = {"name": "chapter-1"}\n'
    assert _violations_in(src, "src/shenbi/gates/g1.py") == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_lint_status_strings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.lint_status_strings'`.

- [ ] **Step 3: Implement the lint**

`tools/lint_status_strings.py`:

```python
#!/usr/bin/env python3
"""Lint: no bare status-vocab string literal on a dict's "status" key outside status.py.

Enforces spec D3's "no bare status string-literals outside status.py" rule, scoped
to the ``"status"`` dict key (the result-envelope emit site). This avoids false
positives on check-item dicts like ``{"id": "G3.1", "s": "PASS"}`` (key "s") and
on read-comparisons (``x == "FAIL"``), which are not emit sites.
"""
from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shenbi.status import STATUS_STRING_LITERALS  # noqa: E402

EXEMPT = "status.py"
# The three keys the audit (D3) identifies as overloading status vocabulary.
STATUS_KEYS = frozenset({"status", "state", "classification"})
TARGET_GLOBS = ("src/shenbi/**/*.py",)


def _is_status_value(s: object) -> bool:
    return isinstance(s, str) and s in STATUS_STRING_LITERALS


def _is_status_key(node: object) -> bool:
    return isinstance(node, ast.Constant) and node.value in STATUS_KEYS


class _Visitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_Dict(self, node: ast.Dict) -> None:
        # node.keys may contain None (for ** unpacks); pair with values by index.
        for k, v in zip(node.keys, node.values, strict=False):
            if (
                _is_status_key(k)
                and isinstance(v, ast.Constant)
                and _is_status_value(v.value)
            ):
                self.violations.append(f"{self.filename}:{v.lineno}: bare status string {v.value!r}")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # d["status"] = "PASS"  →  Subscript target keyed by "status"
        if isinstance(node.value, ast.Constant) and _is_status_value(node.value.value):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Subscript)
                    and _is_status_key(tgt.slice)
                ):
                    self.violations.append(
                        f"{self.filename}:{node.lineno}: bare status string {node.value.value!r}"
                    )
        self.generic_visit(node)


def find_violations(filename: str, tree: ast.AST) -> list[str]:
    v = _Visitor(filename)
    v.visit(tree)
    return v.violations


def scan(roots: Iterable[str]) -> list[str]:
    out: list[str] = []
    for pattern in TARGET_GLOBS:
        for py in Path().glob(pattern):
            if py.name == EXEMPT:
                continue
            out.extend(find_violations(str(py), ast.parse(py.read_text(encoding="utf-8"))))
    return out


def main() -> int:
    vios = scan(TARGET_GLOBS)
    for v in vios:
        print(v)  # noqa: T201
    return 1 if vios else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_lint_status_strings.py -v`
Expected: PASS.

- [ ] **Step 5: Run the lint over the real source — this is the gate that makes Task 2 exhaustive**

Task 2 rewires the three highest-volume emit sites (`shared.py`, `scoring.py`, `phase_runner.py`), but other modules emit result statuses directly too (`recovery.py`, `update_progress.py`, `summarize_round.py`, `dispatcher/cli.py`, `gates/cli.py`, and any gate that builds a `{"status": ...}` instead of calling `passed()`/`fail()`). This step catches all of them.

Run: `uv run python tools/lint_status_strings.py`
Expected: a list of remaining emit sites (or `CLEAN`). For each reported `file:line`, route the value through the matching enum member — e.g. `{"status": "ok"}` → `{"status": CommandStatus.OK}`, `{"state": "started"}` → `PhaseState.STARTED`, `{"classification": "FAIL"}` → `ScoreClassification.FAIL`. Re-run until the command exits 0. (Gate modules that already emit via `passed()`/`fail()`/`unimplemented()` need no change — those helpers were rewired in Task 2.) Then:

Run: `uv run python tools/lint_status_strings.py && echo CLEAN`
Expected: `CLEAN`.

- [ ] **Step 6: Wire the lint into pre-commit, CI, and justfile**

In `.pre-commit-config.yaml`, add under the existing `repo: local` hooks:

```yaml
      - id: lint-status-strings
        name: lint bare status strings (spec D3)
        entry: uv run python tools/lint_status_strings.py
        language: system
        pass_filenames: false
        types: [python]
```

In `.github/workflows/ci.yml`, inside the `quality` job steps (after the `basedpyright` step):

```yaml
      - name: Lint bare status strings (spec D3)
        run: uv run python tools/lint_status_strings.py
```

In `justfile`, add a recipe:

```makefile
# Lint bare status strings (spec D3)
lint-status:
	uv run python tools/lint_status_strings.py
```

- [ ] **Step 7: Commit**

```bash
git add tools/lint_status_strings.py tests/unit/test_lint_status_strings.py .pre-commit-config.yaml .github/workflows/ci.yml justfile src/shenbi/
git commit -m "feat(lint): bare-status-string lint + remaining emit-site rewires (spec D3)"
```

> `git add src/shenbi/` captures any additional emit-site rewires from Step 5 (modules beyond the three Task 2 touched). If Step 5 reported `CLEAN` with no extra edits, `src/shenbi/` adds nothing.

---

# Part II — Contract loader: the single source (C, D2)

Makes the frontmatter `contract` block the one editable location and `contract.load_contract` the only reader. The three incompatible value shapes (Layer C) become unexpressible: `writes` is a typed `list[str]`, `report only` is rejected at load, globs must be registered.

---

### Task 4: Create `contract.py` — schema, loader, registry resolution

**Files:**
- Create: `src/shenbi/contract.py`
- Test: `tests/unit/test_contract.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_contract.py`:

```python
"""contract.load_contract: one loader, schema-validated, registry-resolved."""
from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contract import Contract, ContractError, OutputKind, load_contract

# A minimal registry the test paths resolve against. Tests monkeypatch
# shenbi.contract.REGISTRY_PATH to this tmp file, so they are fully isolated
# from the real docs/framework/truth-files.yaml (authored in Task 5).
_TEST_REGISTRY = (
    "concepts:\n"
    "  - {name: plans/chapter-N-plan.md, kind: plan}\n"
    "  - {name: chapters/chapter-N.md, kind: chapter}\n"
    "patterns:\n"
    "  - {parametric: plans/chapter-N-plan.md, glob: plans/chapter-*-plan.md}\n"
    "  - {parametric: chapters/chapter-N.md, glob: chapters/chapter-*.md}\n"
    "globs: []\n"
)


def _setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, body: str
) -> None:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    reg = tmp_path / "registry.yaml"
    reg.write_text(_TEST_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contract.SKILLS", tmp_path)
    monkeypatch.setattr("shenbi.contract.REGISTRY_PATH", reg)


@pytest.mark.unit
def test_valid_artifact_contract_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-x",
        "---\n"
        "name: shenbi-x\ndescription: Use when x\n"
        "contract:\n  kind: artifact\n  reads:\n    - plans/chapter-N-plan.md\n"
        "  writes:\n    - chapters/chapter-N.md\n  updates: []\n"
        "---\n\n# Body\n",
    )
    c = load_contract("shenbi-x")
    assert c["kind"] is OutputKind.ARTIFACT
    assert c["writes"] == ["chapters/chapter-N.md"]


@pytest.mark.unit
def test_prose_writes_report_only_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Layer C root cause: 'report only' is not a list -> ContractError."""
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: Use when bad\n"
        "contract:\n  kind: report\n  reads: []\n  writes: report only\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_invalid_kind_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: wat\n  reads: []\n  writes: []\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_non_list_reads_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: artifact\n  reads: chapters/chapter-N.md\n  writes: []\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_unregistered_path_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: artifact\n  reads:\n    - totally/made/up.md\n"
        "  writes: []\n  updates: []\n---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_missing_skill_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reg = tmp_path / "registry.yaml"
    reg.write_text(_TEST_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contract.SKILLS", tmp_path)
    monkeypatch.setattr("shenbi.contract.REGISTRY_PATH", reg)
    with pytest.raises(ContractError):
        load_contract("shenbi-nope")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_contract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.contract'`.

- [ ] **Step 3: Implement `contract.py`**

`src/shenbi/contract.py`:

```python
"""Single loader for skill I/O contracts (spec §5.1, fixes audit D2).

The frontmatter ``contract:`` block is the ONE editable location for a skill's
I/O. Every consumer (dispatcher, phase_runner, gates, generator) imports
``load_contract`` — the loader-uniqueness lint forbids a second reader of the
frontmatter ``contract:`` key.

Validation layers (spec §4.2, all "impossible to land"):
  * schema  — kind in OutputKind; reads/writes/updates are list[str]
  * registry — every path resolves to a concept, glob, or parametric pattern
A per-skill load does NOT check cross-skill completeness (that needs the DAG);
the contract-completeness lint (Part IV) does.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, TypedDict

import yaml

from shenbi.exceptions import FrameworkError
from shenbi.gates.shared import PROJECT, SKILLS

REGISTRY_PATH = PROJECT / "docs" / "framework" / "truth-files.yaml"


class ContractError(FrameworkError):
    """A skill contract is missing, malformed, or fails registry resolution."""


class OutputKind(StrEnum):
    ARTIFACT = "artifact"   # writes a durable project file -> G2 chapter/truth validation
    REPORT = "report"       # emits a persisted report (path declared in writes) -> G2 report-type
    EPHEMERAL = "ephemeral" # transient guidance, no persisted artifact -> output gates skip


class Contract(TypedDict):
    kind: OutputKind
    reads: list[str]
    writes: list[str]
    updates: list[str]


def _skill_path(skill: str) -> Path:
    return SKILLS / skill / "SKILL.md"


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise ContractError("registry missing", registry=str(REGISTRY_PATH))
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContractError("registry malformed", registry=str(REGISTRY_PATH))
    return data


def resolves(path: str, registry: dict[str, Any]) -> bool:
    """True if path is a concept, a declared glob, or a registered parametric."""
    import fnmatch

    concepts = {c["name"] for c in registry.get("concepts", [])}
    if path in concepts:
        return True
    globs = [g["pattern"] for g in registry.get("globs", [])]
    if any(fnmatch.fnmatch(path, g) for g in globs):
        return True
    # parametric: a contract may declare a parametric pattern (e.g. chapters/chapter-N.md);
    # it resolves if the registry has that parametric (lookup, not inference).
    parametrics = {p["parametric"] for p in registry.get("patterns", [])}
    if path in parametrics:
        return True
    return False


def _read_frontmatter_contract(skill: str, skill_md: Path) -> dict[str, Any]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ContractError("frontmatter missing", skill=skill)
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ContractError("frontmatter unterminated", skill=skill)
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise ContractError("frontmatter not a mapping", skill=skill)
    contract = data.get("contract")
    if not isinstance(contract, dict):
        raise ContractError("contract block missing", skill=skill)
    return contract


def _validate(raw: dict[str, Any], skill: str, registry: dict[str, Any]) -> Contract:
    if "kind" not in raw:
        raise ContractError("contract.kind missing", skill=skill)
    try:
        kind = OutputKind(raw["kind"])
    except ValueError:
        raise ContractError(
            "contract.kind invalid", skill=skill, kind=raw["kind"], allowed=[k.value for k in OutputKind]
        ) from None

    out: dict[str, Any] = {"kind": kind}
    for field in ("reads", "writes", "updates"):
        val = raw.get(field)
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            raise ContractError(
                f"contract.{field} must be a list[str]", skill=skill, field=field
            )
        for p in val:
            if not resolves(p, registry):
                raise ContractError(
                    "contract path does not resolve in registry", skill=skill, field=field, path=p
                )
        out[field] = val
    return out  # type: ignore[return-value]


def load_contract(skill: str) -> Contract:
    """Load and fully validate a skill's frontmatter contract."""
    path = _skill_path(skill)
    if not path.exists():
        raise ContractError("skill SKILL.md not found", skill=skill)
    registry = load_registry()
    raw = _read_frontmatter_contract(skill, path)
    return _validate(raw, skill, registry)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_contract.py -v`
Expected: PASS. (The tests monkeypatch `REGISTRY_PATH` to a tmp registry, so they are green immediately — independent of Task 5's real `truth-files.yaml`. The real registry is what makes *production* `load_contract` calls resolve; the unit tests stay isolated.)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contract.py tests/unit/test_contract.py
git commit -m "feat(contract): single schema-validated loader (spec §5.1, D2)"
```

---

### Task 5: Author the canonical file registry (`truth-files.yaml`)

The registry is the schema source — the one place a new file concept is added, so synonyms are PR-visible (D1). Author it from the inventory observed across all 57 contracts + deps.json, resolving the synonym drift the audit flagged.

**Files:**
- Create: `docs/framework/truth-files.yaml`
- Modify: `src/shenbi/contract.py` (registry path already points here)

- [ ] **Step 1: Author the registry**

`docs/framework/truth-files.yaml`:

```yaml
# Canonical file vocabulary — the schema source (spec §5.3, fixes D1).
# Adding a genuinely new file = ONE edit here; that edit is the PR-visible
# decision point that prevents silent synonym creation.
#
# Concepts are matched verbatim; globs via fnmatch; parametrics are literal
# contract strings (the generator looks up a parametric's declared glob).

concepts:
  # project config
  - {name: novel.json, kind: config}
  - {name: genre-config.json, kind: config}
  - {name: era-reference.md, kind: reference}        # author-supplied (read-only)
  # world
  - {name: world/story_bible.md, kind: world}
  - {name: world/rules.md, kind: world}
  - {name: world/locations.md, kind: world}
  - {name: world/power_system.md, kind: world}
  - {name: world/factions.md, kind: world}
  # characters
  - {name: characters/protagonist.md, kind: character}
  - {name: characters/relationships.md, kind: character}
  # outline
  - {name: outline/story_frame.md, kind: outline}
  - {name: outline/volume_map.md, kind: outline}
  - {name: outline/rhythm_principles.md, kind: outline}
  - {name: outline/thread_map.md, kind: outline}
  - {name: outline/chapter_patterns.md, kind: outline}
  - {name: outline/short_story_map.md, kind: outline}
  # truth
  - {name: truth/current_state.md, kind: truth}
  - {name: truth/pending_hooks.md, kind: truth}
  - {name: truth/chapter_summaries.md, kind: truth}
  - {name: truth/character_matrix.md, kind: truth}
  - {name: truth/emotional_arcs.md, kind: truth}
  - {name: truth/subplot_board.md, kind: truth}
  - {name: truth/audit_drift.md, kind: truth}
  - {name: truth/author_intent.md, kind: truth}
  - {name: truth/current_focus.md, kind: truth}
  - {name: truth/drift_guidance.md, kind: truth}
  - {name: truth/particle_ledger.md, kind: truth}
  - {name: truth/volume_summaries.md, kind: truth}
  - {name: truth/parent_canon.md, kind: truth}
  # plans / chapters / context
  - {name: plans/chapter-N-plan.md, kind: plan}      # parametric: N
  - {name: chapters/chapter-N.md, kind: chapter}     # parametric: N
  - {name: context/chapter-N-context.md, kind: context}
  # style
  - {name: style/style_profile.md, kind: style}
  # audits (one concept covers all 18 dims via the glob below)
  - {name: audits/chapter-N-<dim>.md, kind: report}  # parametric: N, <dim>
  # foundation / snapshots / import / short
  - {name: foundation/review_report.md, kind: report}
  - {name: snapshots/chapter-NNN/manifest.json, kind: snapshot}
  - {name: import/analysis/01_overview.md, kind: import}
  - {name: import/canon/01_SECTION.md, kind: import}
  - {name: import/packaging/package.md, kind: import}
  - {name: short/outline.md, kind: short}
  - {name: short/package.md, kind: short}

patterns:  # parametric -> glob (the generator's normalization is a lookup)
  - {parametric: plans/chapter-N-plan.md, glob: plans/chapter-*-plan.md}
  - {parametric: chapters/chapter-N.md, glob: chapters/chapter-*.md}
  - {parametric: context/chapter-N-context.md, glob: context/chapter-*-context.md}
  - {parametric: snapshots/chapter-NNN/manifest.json, glob: snapshots/chapter-*/manifest.json}
  - {parametric: audits/chapter-N-<dim>.md, glob: audits/chapter-*.md}

globs:  # declared wildcards contracts may use verbatim
  - {pattern: truth/*.md}
  - {pattern: world/*.md}
  - {pattern: outline/*.md}
  - {pattern: characters/major/*.md}
  - {pattern: characters/minor/*.md}
  - {pattern: characters/**/*.md}
  - {pattern: chapters/*.md}
  - {pattern: plans/chapter-*-plan.md}
  - {pattern: context/chapter-*-context.md}
  - {pattern: audits/chapter-*.md}
  - {pattern: snapshots/chapter-NNN/*}
  - {pattern: snapshots/*.json}
  - {pattern: import/analysis/*.md}
  - {pattern: import/canon/*.md}
  - {pattern: import/packaging/*}
  - {pattern: import/source/*.txt}
  - {pattern: source_canon/*}
  - {pattern: short/chapter-*.md}
  - {pattern: chapters/chapter-*-revised.md}

# Resolved synonym decisions (the audit's D1 drift surfaces):
#   style/style_profile.md  is canonical; deps.json's legacy
#     config/style_profile.md  is STALE and is regenerated away (Part III).
#   truth/volume_summaries.md is canonical; deps.json's legacy
#     volumes/volume-*-summary.md is STALE and regenerated away (Part III).
#   world/faction-relations.md (legacy deps.json) has no producer -> dropped.
```

- [ ] **Step 2: Verify the registry loads and resolves the plan's test paths**

Run:
```bash
uv run python -c "
from shenbi.contract import load_registry, resolves
r = load_registry()
for p in ['plans/chapter-N-plan.md','chapters/chapter-N.md','audits/chapter-N-<dim>.md','truth/*.md','style/style_profile.md']:
    assert resolves(p, r), p
print('registry resolves plan test paths: OK')
"
```
Expected: `registry resolves plan test paths: OK`.

- [ ] **Step 3: Re-run Task 4's tests (resolver now has a registry)**

Run: `uv run pytest tests/unit/test_contract.py -v`
Expected: PASS (all 6 tests green).

- [ ] **Step 4: Commit**

```bash
git add docs/framework/truth-files.yaml
git commit -m "feat(registry): canonical truth-files.yaml vocabulary (spec §5.3, D1)"
```

---

### Task 6: Rewire consumers to `load_contract`; delete the regex parsers

Fixes D2 going forward: `executor.py` and `phase_runner.py` import the single loader; the duplicated regex is deleted. `derive_file_type` becomes contract-driven where possible (it already exists as a name-set; leave it but have `derive_input_files`/`derive_output_files` delegate to `load_contract`).

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:51-75` (delete `derive_input_files`/`derive_output_files` regex bodies; delegate to `load_contract`)
- Modify: `src/shenbi/phase_runner.py:110-143` (`cmd_pre_skill` inline parse → `load_contract`)
- Test: `tests/unit/test_dispatcher_executor.py:35-49`, `tests/unit/test_phase_runner.py:261-345`

- [ ] **Step 1: Write the failing test — executor derives from the contract**

Append to `tests/unit/test_dispatcher_executor.py`:

```python
@pytest.mark.unit
def test_derive_input_files_uses_contract_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """derive_input_files delegates to contract.load_contract (no regex)."""
    from shenbi.dispatcher import executor as exec_mod

    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda skill: {"kind": "artifact", "reads": ["plans/chapter-N-plan.md"], "writes": ["chapters/chapter-N.md"], "updates": []},
    )
    assert exec_mod.derive_input_files("shenbi-x") == ["plans/chapter-N-plan.md"]
    assert exec_mod.derive_output_files("shenbi-x") == ["chapters/chapter-N.md"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_dispatcher_executor.py::test_derive_input_files_uses_contract_loader -v`
Expected: FAIL (`load_contract` not imported in executor).

- [ ] **Step 3: Rewrite the executor functions to delegate**

In `src/shenbi/dispatcher/executor.py`, replace `derive_input_files` and `derive_output_files` (lines 51–75) with:

```python
from shenbi.contract import load_contract


def derive_input_files(skill: str) -> list[str]:
    """Return the skill's contract reads via the single loader."""
    try:
        return list(load_contract(skill)["reads"])
    except Exception:
        # A skill outside the contract system (e.g. a meta skill) has no inputs.
        return []


def derive_output_files(skill: str) -> list[str]:
    """Return the skill's contract writes + updates via the single loader."""
    try:
        c = load_contract(skill)
        return [*c["writes"], *c["updates"]]
    except Exception:
        return []
```

> Rationale for the bare `except Exception`: `dispatch()` is the runtime path; an un-loadable contract (meta skill) must not crash dispatch. The *loader-uniqueness* and *contract-schema* lints (Part IV) are what prevent a real skill from having a broken contract landing — they run at commit/CI. Keep the swallow narrow (only in these two derive helpers) and document it. (If a reviewer prefers, narrow to `ContractError`.)

- [ ] **Step 4: Rewrite `phase_runner.cmd_pre_skill` to use the loader**

In `src/shenbi/phase_runner.py`, replace the regex block (lines ~110–143) — the `import re as _re` and the four `findall` calls — with:

```python
    # Extract data contract via the single loader (spec D2 — no second parser).
    from shenbi.contract import ContractError, load_contract

    try:
        contract = load_contract(skill)
        read_files = list(contract["reads"])
        write_files = [*contract["writes"], *contract["updates"]]
    except ContractError:
        read_files, write_files = [], []
```

Remove the now-dead `skill_md = skill_path.read_text(...)` line (the skill-path existence check above it stays). Delete the `import re` at module top if it becomes unused (`grep -n "re\." src/shenbi/phase_runner.py`).

- [ ] **Step 5: Update the legacy tests that hardcoded the `**Reads:**` format**

The rewired `cmd_pre_skill` / `derive_*` call `load_contract`, which reads `shenbi.contract.SKILLS` and `shenbi.contract.REGISTRY_PATH` — **not** `phase_runner.PROJECT`. So the existing tests (which monkeypatch `phase_runner.PROJECT` and write fake skills with body blocks) must be rewritten to (a) give fake skills a **frontmatter contract** and (b) monkeypatch `shenbi.contract.SKILLS` + `shenbi.contract.REGISTRY_PATH`.

For the **phase_runner** tests (`test_phase_runner.py` ~lines 261–345), replace the body-block fixtures + `monkeypatch.setattr(phase_runner, "PROJECT", round_dir)` with a helper that writes a frontmatter contract and points the loader at it. Add this helper near the test class:

```python
_TEST_REGISTRY = (
    "concepts:\n"
    "  - {name: world/story_bible.md, kind: world}\n"
    "  - {name: outline/story_frame.md, kind: outline}\n"
    "  - {name: world/locations.md, kind: world}\n"
    "  - {name: truth/current_state.md, kind: truth}\n"
    "patterns: []\nglobs: []\n"
)


def _point_loader_at(monkeypatch, skills_root: Path) -> None:
    """Redirect contract.load_contract at a tmp skills dir + tmp registry."""
    reg = skills_root / "registry.yaml"
    reg.write_text(_TEST_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contract.SKILLS", skills_root)
    monkeypatch.setattr("shenbi.contract.REGISTRY_PATH", reg)
```

Then each test writes a frontmatter-contract skill and calls `_point_loader_at(monkeypatch, fake_skills)` — note `SKILLS` must point at the dir *containing* the skill subdirs (`round_dir/skills`), so `load_contract` resolves `SKILLS/shenbi-test-skill/SKILL.md`:

```python
(fake_skills / "shenbi-test-skill" / "SKILL.md").write_text(
    "---\nname: shenbi-test-skill\ndescription: Use when test\n"
    "contract:\n  kind: artifact\n"
    "  reads:\n    - world/story_bible.md\n    - outline/story_frame.md\n"
    "  writes:\n    - world/locations.md\n"
    "  updates:\n    - truth/current_state.md\n"
    "---\n\n# Skill\n",
    encoding="utf-8",
)
_point_loader_at(monkeypatch, fake_skills)
cmd_pre_skill("design", "shenbi-test-skill", str(round_dir))
emitted = json.loads(capsys.readouterr().out)
assert "world/story_bible.md" in emitted["reads"]
assert "world/locations.md" in emitted["writes"]
assert "truth/current_state.md" in emitted["writes"]  # updates fold into writes
```

For `test_returns_empty_lists_when_skill_md_has_no_contract`, give the skill a valid contract with `reads: []`/`writes: []`/`updates: []` (a bare body now raises `ContractError` → empty lists, which also satisfies the assertion; either form works, but a valid empty contract is clearer).

For the **executor** tests (`test_dispatcher_executor.py` ~lines 35–49, `test_derive_input_files_*`/`test_derive_output_files_*`): the simplest fix is to monkeypatch the stubbed loader added in Step 1, so they don't depend on the real (pre-migration) skill:

```python
@pytest.mark.unit
def test_derive_input_files_delegates_to_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    from shenbi.dispatcher import executor as exec_mod

    monkeypatch.setattr(
        exec_mod, "load_contract",
        lambda s: {"kind": "artifact", "reads": ["plans/chapter-N-plan.md"], "writes": [], "updates": []},
    )
    assert exec_mod.derive_input_files("shenbi-x") == ["plans/chapter-N-plan.md"]
    assert exec_mod.derive_output_files("shenbi-x") == []
```

(Delete the old real-skill assertions at lines 35–49 and replace with the stubbed form above; keep the `derive_file_type` and dispatch tests unchanged.)

- [ ] **Step 6: Run the affected tests**

Run: `uv run pytest tests/unit/test_dispatcher_executor.py tests/unit/test_phase_runner.py -v`
Expected: PASS.

- [ ] **Step 7: Confirm no regex parser remains**

Run: `grep -rn 'Reads:\*\*\\|Writes:\*\*\\|Updates:\*\*' src/shenbi/ || echo "no body-contract regex in src"`
Expected: `no body-contract regex in src`.

- [ ] **Step 8: Commit**

```bash
git add src/shenbi/dispatcher/executor.py src/shenbi/phase_runner.py tests/unit/test_dispatcher_executor.py tests/unit/test_phase_runner.py
git commit -m "refactor(contract): consumers use single loader; delete regex parsers (spec D2)"
```

---

# Part III — The generator (D4, D1, OD-1)

Derives `expected_outputs`, the producer/consumer DAG, the registry usage index, and the auto-rendered body view from contracts — via `load_contract` (no third parser). Hand-edits to any generated artifact are rejected by the idempotency lint.

---

### Task 7: Generator entry point `shenbi-sync-contracts`

**Files:**
- Create: `src/shenbi/sync_contracts.py`
- Modify: `pyproject.toml:46-53` (add entry point)
- Test: `tests/unit/test_sync_contracts.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_sync_contracts.py`:

```python
"""Generator: expected_outputs (parametric->glob), DAG, index — from contracts."""
from __future__ import annotations

import pytest

from shenbi.sync_contracts import (
    build_dag,
    derive_expected_outputs,
    normalize_to_glob,
    verify_bijection,
)


@pytest.mark.unit
def test_parametric_normalizes_to_glob() -> None:
    reg = {"patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}]}
    assert normalize_to_glob("chapters/chapter-N.md", reg) == "chapters/chapter-*.md"


@pytest.mark.unit
def test_declared_glob_passes_through() -> None:
    reg = {"globs": [{"pattern": "truth/*.md"}], "patterns": []}
    assert normalize_to_glob("truth/*.md", reg) == "truth/*.md"


@pytest.mark.unit
def test_concrete_path_stays_concrete() -> None:
    reg = {"concepts": [{"name": "novel.json"}], "patterns": [], "globs": []}
    assert normalize_to_glob("novel.json", reg) == "novel.json"


@pytest.mark.unit
def test_dag_edge_from_producer_to_consumer() -> None:
    contracts = {
        "A": {"writes": ["chapters/chapter-N.md"], "updates": [], "reads": []},
        "B": {"writes": [], "updates": [], "reads": ["chapters/chapter-N.md"]},
    }
    reg = {"patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
           "globs": [], "concepts": []}
    dag = build_dag(contracts, reg)
    assert {"producer": "A", "consumer": "B", "file": "chapters/chapter-N.md"} in dag["edges"]


@pytest.mark.unit
def test_dag_connects_concrete_write_to_glob_read() -> None:
    """A concrete audit write must join a glob audit read (glob-aware matching)."""
    contracts = {
        "reviewer": {"writes": ["audits/chapter-N-anti-ai.md"], "updates": [], "reads": []},
        "drift": {"writes": [], "updates": [], "reads": ["audits/chapter-N-*.md"]},
    }
    reg = {"concepts": [], "patterns": [], "globs": [{"pattern": "audits/chapter-*.md"}]}
    dag = build_dag(contracts, reg)
    assert any(e["producer"] == "reviewer" and e["consumer"] == "drift" for e in dag["edges"])


@pytest.mark.unit
def test_derive_expected_outputs_normalizes_and_dedups() -> None:
    """Two members writing the same glob -> one entry; parametric -> glob."""
    phase = {"prerequisites": ["A", "B"]}
    contracts = {
        "A": {"writes": ["chapters/chapter-N.md"], "updates": [], "reads": []},
        "B": {"writes": [], "updates": ["chapters/chapter-N.md"], "reads": []},
    }
    reg = {"patterns": [{"parametric": "chapters/chapter-N.md", "glob": "chapters/chapter-*.md"}],
           "globs": [], "concepts": []}
    assert derive_expected_outputs(phase, contracts, reg) == ["chapters/chapter-*.md"]


@pytest.mark.unit
def test_bijection_self_check_passes_when_complete() -> None:
    """Every member write is emitted and every emitted entry traces to a member."""
    phase = {"prerequisites": ["A"]}
    contracts = {"A": {"writes": ["novel.json"], "updates": [], "reads": []}}
    reg = {"concepts": [{"name": "novel.json"}], "patterns": [], "globs": []}
    generated = derive_expected_outputs(phase, contracts, reg)
    # No raise == bijection holds (catches generator bugs, not curated drift).
    verify_bijection(generated, phase, contracts, reg)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_sync_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the generator**

`src/shenbi/sync_contracts.py`:

```python
"""Derive generated artifacts from contracts (spec §5.4, fixes D4/D1).

Reads every skill's contract via contract.load_contract (no third parser) and
derives:
  * deps.json expected_outputs  (parametric -> glob; in place)
  * docs/framework/dependency-dag.json   (producer/consumer graph — NEW)
  * docs/framework/truth-files.index.json (per-file usage)
  * the auto-rendered body 数据契约 view (OD-1)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shenbi.contract import load_contract, load_registry
from shenbi.gates.shared import ALL_SKILLS, PROJECT

DEPS_PATH = PROJECT / "tests" / "tiers" / "deps.json"
DAG_PATH = PROJECT / "docs" / "framework" / "dependency-dag.json"
INDEX_PATH = PROJECT / "docs" / "framework" / "truth-files.index.json"
BODY_BANNER = "<!-- AUTO-GENERATED from frontmatter — do not edit -->"
BODY_END = "<!-- END AUTO-GENERATED -->"


def normalize_to_glob(path: str, registry: dict[str, Any]) -> str:
    """Parametric -> its declared glob; globs/concrete pass through."""
    for p in registry.get("patterns", []):
        if p["parametric"] == path:
            return p["glob"]
    return path


def load_all_contracts() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for skill in ALL_SKILLS:
        try:
            c = load_contract(skill)
        except Exception:
            continue  # meta skills / not-yet-migrated skills skipped
        out[skill] = {
            "reads": list(c["reads"]),
            "writes": list(c["writes"]),
            "updates": list(c["updates"]),
        }
    return out


def dag_key(path: str, registry: dict[str, Any]) -> str:
    """Canonical matching key for a path in the DAG.

    A concrete write (audits/chapter-N-anti-ai.md) and a glob read
    (audits/chapter-N-*.md) must join under one edge, so the completeness check
    can see that a report is consumed downstream. Map any path to a declared
    glob it matches; else its parametric glob; else itself.
    """
    import fnmatch

    for g in registry.get("globs", []):
        if fnmatch.fnmatch(path, g["pattern"]):
            return g["pattern"]
    return normalize_to_glob(path, registry)


def build_dag(
    contracts: dict[str, dict[str, Any]], registry: dict[str, Any]
) -> dict[str, Any]:
    """skill B reads file X that skill A writes/updates => A -> B.

    Matching is glob-aware (via dag_key) so a concrete producer write and a glob
    consumer read connect even when their literal strings differ.
    """
    producers: dict[str, list[str]] = {}
    for skill, c in contracts.items():
        for f in [*c["writes"], *c["updates"]]:
            producers.setdefault(dag_key(f, registry), []).append(skill)
    edges: list[dict[str, str]] = []
    for consumer, c in contracts.items():
        for f in c["reads"]:
            for producer in producers.get(dag_key(f, registry), []):
                if producer != consumer:
                    edges.append({"producer": producer, "consumer": consumer, "file": f})
    return {"edges": edges}


def derive_expected_outputs(
    phase: dict[str, Any], contracts: dict[str, dict[str, Any]], registry: dict[str, Any]
) -> list[str]:
    """Derive a phase's expected_outputs from member writes/updates.

    Parametric patterns normalize to their declared glob; declared globs and
    concrete paths pass through. The curated ``expected_outputs`` is NOT read
    here — it is the drift surface being regenerated, so comparing against it
    would make the generator fail on its own first run.
    """
    members: list[str] = phase.get("prerequisites", [])
    produced: list[str] = []
    for skill in members:
        c = contracts.get(skill, {})
        for f in [*c.get("writes", []), *c.get("updates", [])]:
            produced.append(normalize_to_glob(f, registry))
    return sorted(set(produced))


def verify_bijection(
    generated: list[str],
    phase: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
    registry: dict[str, Any],
) -> None:
    """Spec §5.4 round-trip self-check: every member write is emitted and every
    emitted entry traces to a member write (bijection within the phase).

    This catches GENERATOR bugs (a member write dropped, or a spurious entry),
    not curated drift. Raises AssertionError on mismatch.
    """
    members: list[str] = phase.get("prerequisites", [])
    expected = sorted(
        {normalize_to_glob(f, registry)
         for s in members for f in [*contracts.get(s, {}).get("writes", []),
                                    *contracts.get(s, {}).get("updates", [])]}
    )
    assert generated == expected, f"bijection broken: {generated} != {expected}"
```

- [ ] **Step 4: Add the entry point + the `main()` that writes all artifacts**

Append to `src/shenbi/sync_contracts.py`:

```python
import json

from shenbi.logging import get_logger

log = get_logger(__name__)


def render_body_view(skill: str, contract: dict[str, Any]) -> str:
    """The auto-generated 数据契约 block, wrapped in start/end sentinels so
    re-rendering is an unambiguous regex replace (idempotent)."""
    lines = [BODY_BANNER, "", "## 数据契约", ""]
    lines.append(f"- **Reads:** {', '.join(contract['reads']) or 'none'}")
    lines.append(f"- **Writes:** {', '.join(contract['writes']) or 'none'}")
    lines.append(f"- **Updates:** {', '.join(contract['updates']) or 'none'}")
    lines.append("")
    lines.append(BODY_END)
    return "\n".join(lines) + "\n"


def render_body_into(skill_md: Path, contract: dict[str, Any]) -> None:
    """Inject/replace the auto-generated body block in a SKILL.md (OD-1).

    Idempotent: the block is delimited by BODY_BANNER ... BODY_END, so an
    existing block is replaced wholesale and a missing one is prepended after
    the frontmatter.
    """
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", text, flags=re.DOTALL)
    if not m:
        return  # not a skill file with frontmatter
    frontmatter, body = m.group(1), m.group(2)
    block = render_body_view(skill_md.parent.name, contract)
    pattern = re.compile(re.escape(BODY_BANNER) + r".*?" + re.escape(BODY_END) + r"\n?", re.DOTALL)
    if pattern.search(body):
        body = pattern.sub(block, body, count=1)
    else:
        body = block + "\n" + body.lstrip("\n")
    skill_md.write_text(frontmatter + body, encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    registry = load_registry()
    contracts = load_all_contracts()
    if not contracts:
        # Pre-migration (Parts III–IV): no skill has a frontmatter contract yet.
        # Bail BEFORE writing anything — otherwise every phase's expected_outputs
        # would be overwritten with []. Run `just generate` only after Task 13.
        log.error("no_contracts_loaded", hint="run after the Task 13 migration")
        return 1

    # DAG + index
    _write_json(DAG_PATH, build_dag(contracts, registry))
    usage: dict[str, dict[str, list[str]]] = {}
    for skill, c in contracts.items():
        for role, files in (("reads", c["reads"]), ("writes", c["writes"]), ("updates", c["updates"])):
            for f in files:
                usage.setdefault(f, {"reads": [], "writes": [], "updates": []})[role].append(skill)
    _write_json(INDEX_PATH, usage)

    # Auto-rendered body 数据契约 view into each migrated skill (OD-1).
    from shenbi.gates.shared import SKILLS

    for skill, c in contracts.items():
        render_body_into(SKILLS / skill / "SKILL.md", c)

    # deps.json expected_outputs in place (organizational fields preserved).
    # The curated expected_outputs is OVERWRITTEN — it is the D4 drift surface
    # being regenerated, so we never compare against it (that would fail the
    # generator on its own first run). Correctness is the bijection self-check.
    deps = json.loads(DEPS_PATH.read_text(encoding="utf-8"))
    for phase_name, phase in deps.get("t2-phases", {}).items():
        generated = derive_expected_outputs(phase, contracts, registry)
        verify_bijection(generated, phase, contracts, registry)
        phase["expected_outputs"] = generated
        log.info("phase_synced", phase=phase_name, outputs=generated)
    _write_json(DEPS_PATH, deps)
    log.info("sync_complete", skills=len(contracts))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
```

In `pyproject.toml`, add to `[project.scripts]`:

```toml
shenbi-sync-contracts = "shenbi.sync_contracts:main"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_sync_contracts.py -v && uv sync`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/sync_contracts.py tests/unit/test_sync_contracts.py pyproject.toml
git commit -m "feat(sync): contract-driven generator (expected_outputs, DAG, index) (spec §5.4)"
```

---

### Task 8: `just generate` recipe

The idempotency CI/pre-commit gate is added in Task 13 (it can only go green after the Part V migration regenerates the artifacts for the first time). This task lands only the recipe + entry point so the generator is runnable.

**Files:**
- Modify: `justfile` (add `generate` recipe)

- [ ] **Step 1: Add the `generate` recipe**

In `justfile`:

```makefile
# Regenerate contract-derived artifacts (deps.json expected_outputs, DAG, index, body views)
generate:
	uv run shenbi-sync-contracts
```

- [ ] **Step 2: Commit**

```bash
git add justfile
git commit -m "chore(sync): just generate recipe (spec §5.4)"
```

---

# Part IV — The lints (prevention model)

Each inconsistency class is blocked at the cheapest checkpoint (spec §4.2). Lints live under `tools/` and run in pre-commit + CI.

---

### Task 9: Contract lints — schema, completeness, registry (load-time + CI)

`load_contract` already enforces schema + registry at load (Task 4). This task adds the **cross-skill completeness** check (needs the DAG) as a CI lint over all 57 in-pipeline skills, and a load-all loop that surfaces any `ContractError`.

**Files:**
- Create: `tools/lint_contracts.py`
- Test: `tests/unit/test_lint_contracts.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_lint_contracts.py`:

```python
"""Contract lints: every in-pipeline skill loads; report consumed => persisted."""
from __future__ import annotations

from tools.lint_contracts import find_completeness_violations

_REG = {"concepts": [], "patterns": [], "globs": [{"pattern": "audits/chapter-*.md"}]}


def test_report_consumed_downstream_without_writes_is_flagged() -> None:
    dag = {"edges": [{"producer": "R", "consumer": "X", "file": "audits/chapter-N-anti-ai.md"}]}
    contracts = {
        "R": {"kind": "report", "reads": [], "writes": [], "updates": []},
        "X": {"kind": "artifact", "reads": ["audits/chapter-N-anti-ai.md"], "writes": [], "updates": []},
    }
    vios = find_completeness_violations(contracts, dag, _REG)
    assert any(v["skill"] == "R" for v in vios)


def test_report_with_persisted_writes_is_clean() -> None:
    dag = {"edges": [{"producer": "R", "consumer": "X", "file": "audits/chapter-N-anti-ai.md"}]}
    contracts = {
        "R": {"kind": "report", "reads": [], "writes": ["audits/chapter-N-anti-ai.md"], "updates": []},
        "X": {"kind": "artifact", "reads": ["audits/chapter-N-anti-ai.md"], "writes": [], "updates": []},
    }
    assert find_completeness_violations(contracts, dag, _REG) == []


def test_glob_read_satisfied_by_concrete_report_write() -> None:
    """The completeness check is glob-aware: a concrete audit write satisfies
    a glob audit read (the real drift-guidance → review-* case)."""
    dag = {"edges": [{"producer": "reviewer", "consumer": "drift", "file": "audits/chapter-N-*.md"}]}
    contracts = {
        "reviewer": {"kind": "report", "reads": [], "writes": ["audits/chapter-N-anti-ai.md"], "updates": []},
        "drift": {"kind": "report", "reads": ["audits/chapter-N-*.md"], "writes": ["truth/drift_guidance.md"], "updates": []},
    }
    assert find_completeness_violations(contracts, dag, _REG) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_lint_contracts.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement the lint**

`tools/lint_contracts.py`:

```python
#!/usr/bin/env python3
"""Contract lints (spec §5.5 #1, #2).

1. load-all  — every in-pipeline skill's contract loads (schema + registry).
2. completeness — a REPORT skill consumed downstream (per DAG) declares a
   persisted writes path (kills the "report only" drift).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shenbi.contract import ContractError, load_contract  # noqa: E402
from shenbi.gates.shared import ALL_SKILLS  # noqa: E402
from shenbi.sync_contracts import build_dag, dag_key, load_all_contracts  # noqa: E402

META_SKILLS = {"using-shenbi", "shenbi-writing-skills"}


def in_pipeline_skills() -> list[str]:
    return [s for s in ALL_SKILLS if s not in META_SKILLS]


def find_load_violations() -> list[str]:
    vios: list[str] = []
    for skill in in_pipeline_skills():
        try:
            load_contract(skill)
        except ContractError as e:
            vios.append(f"{skill}: {e}")
    return vios


def find_completeness_violations(
    contracts: dict[str, dict[str, Any]], dag: dict[str, Any], registry: dict[str, Any]
) -> list[dict[str, str]]:
    """A REPORT skill whose output is consumed downstream (per DAG) must declare
    a persisted write sharing the file's dag_key (glob-aware, so a concrete
    audit write satisfies a glob audit read)."""
    write_keys: dict[str, set[str]] = {
        s: {dag_key(f, registry) for f in [*c.get("writes", []), *c.get("updates", [])]}
        for s, c in contracts.items()
    }
    vios: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for e in dag["edges"]:
        producer = e["producer"]
        c = contracts.get(producer, {})
        if c.get("kind") != "report":
            continue
        key = dag_key(e["file"], registry)
        if key not in write_keys.get(producer, set()):
            tag = (producer, key)
            if tag not in seen:
                seen.add(tag)
                vios.append(
                    {"skill": producer, "file": e["file"], "reason": "report consumed downstream but no persisted write"}
                )
    return vios


def main() -> int:
    from shenbi.contract import load_registry

    vios = find_load_violations()
    registry = load_registry()
    contracts = load_all_contracts()
    dag = build_dag(contracts, registry)
    vios.extend(str(v) for v in find_completeness_violations(contracts, dag, registry))
    for v in vios:
        print(v)  # noqa: T201
    return 1 if vios else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_lint_contracts.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/lint_contracts.py tests/unit/test_lint_contracts.py
git commit -m "feat(lint): contract schema + completeness lints (spec §5.5 #1,#2)"
```

---

### Task 10: Repo-scan lints — body-ban, loader-uniqueness, terminology, section-header

**Files:**
- Create: `tools/lint_repo_consistency.py`
- Test: `tests/unit/test_lint_repo_consistency.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_lint_repo_consistency.py`:

```python
"""Repo lints: body-ban, loader-uniqueness, terminology, section-headers."""
from __future__ import annotations

import pytest

from tools.lint_repo_consistency import (
    find_body_contract_blocks,
    find_banned_synonyms,
    find_extra_contract_key_readers,
    find_section_header_deviants,
)


@pytest.mark.unit
def test_body_reads_block_in_skills_is_flagged() -> None:
    md = "# X\n\n## 数据契约\n\n- **Reads:** `a.md`\n"
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == ["skills/x/SKILL.md"]


@pytest.mark.unit
def test_archived_rounds_are_exempt() -> None:
    md = "# X\n\n- **Reads:** `a.md`\n"
    assert find_body_contract_blocks([("tests/rounds/archived/r1/SKILL.md", md)]) == []


@pytest.mark.unit
def test_auto_generated_body_block_is_exempt() -> None:
    md = (
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\n\n## 数据契约\n\n"
        "- **Reads:** a.md\n- **Writes:** b.md\n- **Updates:** none\n\n"
        "<!-- END AUTO-GENERATED -->\n\n## 流程\n"
    )
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == []


@pytest.mark.unit
def test_handwritten_block_alongside_auto_gen_is_flagged() -> None:
    """A second, hand-written contract block must not hide behind the banner."""
    md = (
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\n\n## 数据契约\n\n"
        "- **Reads:** a.md\n\n<!-- END AUTO-GENERATED -->\n\n"
        "## 铁律\n\n- **Writes:** secret.md\n"
    )
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == ["skills/x/SKILL.md"]


@pytest.mark.unit
def test_hook_pool_synonym_flagged() -> None:
    md = "use the hook pool to ...\n"
    assert "hook pool" in find_banned_synonyms([("skills/x/SKILL.md", md)])[0][1]


@pytest.mark.unit
def test_banned_output_header_flagged() -> None:
    md = "# X\n\n## 输出契约\n\nbody\n"
    assert ("skills/x/SKILL.md", "输出契约") in find_section_header_deviants([("skills/x/SKILL.md", md)])


@pytest.mark.unit
def test_legitimate_non_canonical_header_not_flagged() -> None:
    """Skills legitimately have many section titles; only banned ones are drift."""
    md = "# X\n\n## 检查执行\n\n## 缺陷证据格式\n"
    assert find_section_header_deviants([("skills/x/SKILL.md", md)]) == []


@pytest.mark.unit
def test_loader_uniqueness_flags_contract_key_outside_contract_py() -> None:
    py = 'd = yload(p); c = d["contract"]\n'
    assert "src/shenbi/other.py" in find_extra_contract_key_readers(
        [("src/shenbi/other.py", py), ("src/shenbi/contract.py", py)]
    )[0]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_lint_repo_consistency.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement the lint**

`tools/lint_repo_consistency.py`:

```python
#!/usr/bin/env python3
"""Repo-consistency lints (spec §5.5 #3,#4,#7).

3. body-ban        — skills/*/SKILL.md may not carry a hand-written 数据契约
                     block or **Reads:**/**Writes:**/**Updates:** (archived
                     rounds and the AUTO-GENERATED banner are exempt).
4. loader-uniqueness — only contract.py may read the frontmatter contract: key.
7. terminology     — banned synonyms (hook pool, truth-files, the author) +
                     section-header canonical set.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BANNER = "<!-- AUTO-GENERATED from frontmatter — do not edit -->"
BODY_END = "<!-- END AUTO-GENERATED -->"
# Strip the auto-generated block before scanning, so a hand-written contract
# block added ALONGSIDE the auto-gen one is still caught (spec §3.3).
AUTO_BLOCK_RE = re.compile(re.escape(BANNER) + r".*?" + re.escape(BODY_END) + r"\n?", re.DOTALL)
CONTRACT_BODY_RE = re.compile(r"\*\*(Reads|Writes|Updates):\*\*|^## 数据契约", re.MULTILINE)
BANNED_SYNONYMS = {"hook pool": "hook ledger", "truth-files": "truth files", "the author": "your human partner"}
# Layer A: output-section header deviants that must normalize to 输出格式.
# (We flag a banned set, NOT "anything not canonical" — skills legitimately have
# many other section headers like 检查执行 / 创作原则 / 缺陷证据格式.)
BANNED_HEADERS = {"输出契约", "输出", "Key Results", "输出文件"}
CANONICAL_OUTPUT_HEADER = "输出格式"
File = tuple[str, str]


def _skill_files() -> list[File]:
    out: list[File] = []
    for p in sorted((REPO / "skills").glob("*/SKILL.md")):
        out.append((str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


def find_body_contract_blocks(files: Iterable[File]) -> list[str]:
    flagged: list[str] = []
    for path, md in files:
        if "tests/rounds/archived" in path:
            continue
        # Remove any auto-generated block first; a hand-written block that
        # remains after removal is a forbidden second source.
        stripped = AUTO_BLOCK_RE.sub("", md)
        if CONTRACT_BODY_RE.search(stripped):
            flagged.append(path)
    return flagged


def find_banned_synonyms(files: Iterable[File]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for path, md in files:
        for syn in BANNED_SYNONYMS:
            if syn in md.lower():
                out.append((path, syn))
    return out


def find_section_header_deviants(files: Iterable[File]) -> list[tuple[str, str]]:
    """Flag Layer A output-section header deviants (must normalize to 输出格式).

    Does NOT flag arbitrary non-canonical headers — skills legitimately carry
    many section titles (检查执行, 创作原则, 缺陷证据格式, …). Only the banned
    output-section synonyms are drift.
    """
    out: list[tuple[str, str]] = []
    for path, md in files:
        for m in re.finditer(r"^##\s+(.+?)\s*$", md, re.MULTILINE):
            header = m.group(1).strip()
            if header in BANNED_HEADERS:
                out.append((path, header))
    return out


def find_extra_contract_key_readers(files: Iterable[File]) -> list[str]:
    """A module other than contract.py indexing/reading the 'contract' key."""
    flagged: list[str] = []
    for path, src in files:
        if path.endswith("contract.py"):
            continue
        if re.search(r'["\']contract["\']\s*\]', src) or re.search(r"\.get\(\s*["\']contract["\']\s*\)", src):
            flagged.append(path)
    return flagged


def main() -> int:
    vios: list[str] = []
    skills = _skill_files()
    for p in find_body_contract_blocks(skills):
        vios.append(f"body-ban: {p}")
    for p, syn in find_banned_synonyms(skills):
        vios.append(f"terminology: {p}: '{syn}' -> '{BANNED_SYNONYMS[syn]}'")
    for p, h in find_section_header_deviants(skills):
        vios.append(f"section-header: {p}: '## {h}'")
    py_files = [
        (str(p.relative_to(REPO)), p.read_text(encoding="utf-8"))
        for p in (REPO / "src" / "shenbi").rglob("*.py")
    ]
    for p in find_extra_contract_key_readers(py_files):
        vios.append(f"loader-uniqueness: {p} reads frontmatter contract: key")
    for v in vios:
        print(v)  # noqa: T201
    return 1 if vios else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_lint_repo_consistency.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/lint_repo_consistency.py tests/unit/test_lint_repo_consistency.py
git commit -m "feat(lint): body-ban + loader-uniqueness + terminology lints (spec §5.5 #3,#4,#7)"
```

---

### Task 11: Wire all lints into pre-commit + CI (gated behind Part V)

The lints will go green only after Part V migrates skills. Land the wiring now but **do not** enable them as blocking until Task 13 (or scope CI with the path filter). Decision: **add pre-commit + CI wiring in Task 13** alongside the migration commit so the repo is never red. This task is therefore folded into Task 13 — skip to Part V.

---

# Part V — Migration

Migrate all 57 skills, rewrite the contract-format tests, fix the test-input gap, normalize terminology/section-headers, then enable the lints.

---

### Task 12: Migrator script + classification table

**Files:**
- Create: `tools/migrate_contract_to_frontmatter.py`

- [ ] **Step 1: Encode the per-skill classification table**

The table below is the authoritative migration spec (derived from the live contracts + deps.json). `kind` follows spec §7.2 rules; persisted report paths come from deps.json expected_outputs (the `"report only"` correction).

| Skill | kind | reads | writes | updates |
|---|---|---|---|---|
| shenbi-chapter-drafting | artifact | plans/chapter-N-plan.md, style/style_profile.md, genre-config.json, truth/audit_drift.md | chapters/chapter-N.md | — |
| shenbi-chapter-planning | artifact | truth/current_state.md, truth/pending_hooks.md, truth/chapter_summaries.md, outline/volume_map.md, outline/story_frame.md, truth/current_focus.md, truth/author_intent.md | plans/chapter-N-plan.md | — |
| shenbi-chapter-revision | artifact | chapters/chapter-N.md, audits/chapter-N-*.md | — | chapters/chapter-N.md |
| shenbi-anti-detect | artifact | chapters/chapter-N.md, genre-config.json | — | chapters/chapter-N.md |
| shenbi-length-normalizing | artifact | chapters/chapter-N.md, novel.json | — | chapters/chapter-N.md |
| shenbi-style-polishing | artifact | chapters/chapter-N.md, genre-config.json, style/style_profile.md | — | chapters/chapter-N.md |
| shenbi-character-design | artifact | world/story_bible.md, world/rules.md | characters/protagonist.md, characters/major/*.md, characters/minor/*.md, characters/relationships.md | — |
| shenbi-character-extraction | artifact | import/analysis/02_characters.md, chapters/*.md, import/analysis/04_plot.md | characters/protagonist.md, characters/major/*.md, characters/minor/*.md, characters/relationships.md | — |
| shenbi-worldbuilding | artifact | novel.json | novel.json, genre-config.json, world/story_bible.md, world/rules.md, world/locations.md, truth/*.md | — |
| shenbi-world-extraction | artifact | import/analysis/03_world.md, chapters/*.md, import/analysis/04_plot.md | world/story_bible.md, world/rules.md, world/locations.md, world/factions.md, world/power_system.md | — |
| shenbi-story-architecture | artifact | world/story_bible.md, characters/**/*.md | outline/story_frame.md, outline/volume_map.md, outline/rhythm_principles.md | — |
| shenbi-style-learning | artifact | chapters/*.md, import/source/*.txt | style/style_profile.md | — |
| shenbi-short-outline | artifact | novel.json, truth/author_intent.md, outline/story_frame.md | outline/short_story_map.md | — |
| shenbi-short-drafting | artifact | outline/short_story_map.md, truth/author_intent.md, genre-config.json, style/style_profile.md | chapters/chapter-N.md | — |
| shenbi-short-packaging | artifact | outline/short_story_map.md, chapters/*.md, world/story_bible.md, truth/author_intent.md | import/packaging/* | — |
| shenbi-import-analysis | artifact | import/source/*.txt | import/analysis/*.md | — |
| shenbi-canon-import | artifact | source_canon/* | import/canon/*.md | — |
| shenbi-snapshot-manage | artifact | truth/*.md, chapters/chapter-N.md, characters/**/*.md | snapshots/chapter-NNN/* | — |
| shenbi-volume-consolidation | artifact | chapters/chapter-N.md, truth/chapter_summaries.md, truth/pending_hooks.md | truth/volume_summaries.md | truth/chapter_summaries.md |
| shenbi-state-settling | artifact | chapters/chapter-N.md | — | truth/current_state.md, truth/particle_ledger.md, truth/character_matrix.md, truth/emotional_arcs.md, truth/subplot_board.md, truth/pending_hooks.md, truth/chapter_summaries.md |
| shenbi-foreshadowing-plant | artifact | plans/chapter-N-plan.md, truth/pending_hooks.md, genre-config.json | — | truth/pending_hooks.md |
| shenbi-foreshadowing-track | artifact | chapters/chapter-N.md, truth/pending_hooks.md, truth/chapter_summaries.md | — | truth/pending_hooks.md |
| shenbi-foreshadowing-resolve | artifact | truth/pending_hooks.md, truth/chapter_summaries.md | — | truth/pending_hooks.md |
| shenbi-truth-sync | artifact | chapters/chapter-N.md, truth/*.md, world/*.md, characters/**/*.md | — | truth/*.md |
| shenbi-intent-management | artifact | truth/author_intent.md, truth/audit_drift.md | — | truth/author_intent.md, truth/current_focus.md |
| shenbi-faction-builder | artifact | novel.json, world/story_bible.md, world/rules.md, characters/**/*.md, outline/story_frame.md | — | world/factions.md |
| shenbi-location-builder | artifact | novel.json, world/story_bible.md, world/rules.md, world/locations.md, outline/story_frame.md | — | world/locations.md |
| shenbi-power-system | artifact | novel.json, world/story_bible.md, world/rules.md, outline/story_frame.md | — | world/power_system.md |
| shenbi-pacing-design | artifact | novel.json, outline/story_frame.md, outline/volume_map.md, genre-config.json | — | outline/rhythm_principles.md |
| shenbi-plot-thread-weaver | artifact | outline/story_frame.md, outline/volume_map.md, outline/rhythm_principles.md, truth/pending_hooks.md | — | outline/thread_map.md |
| shenbi-relationship-map | artifact | characters/**/*.md, characters/relationships.md, truth/character_matrix.md, world/factions.md | — | characters/relationships.md, truth/character_matrix.md |
| shenbi-volume-outlining | artifact | outline/story_frame.md, outline/volume_map.md, truth/author_intent.md | — | outline/volume_map.md |
| shenbi-genre-config | artifact | novel.json, genre-config.json | — | genre-config.json |
| shenbi-sequel-writing | artifact | snapshots/chapter-NNN/*, truth/*.md, outline/volume_map.md, outline/thread_map.md | chapters/chapter-N.md | truth/*.md |
| shenbi-context-composing | ephemeral | plans/chapter-N-plan.md, truth/chapter_summaries.md, truth/pending_hooks.md, truth/audit_drift.md, world/rules.md, truth/character_matrix.md, style/style_profile.md, chapters/chapter-N.md | — | — |
| shenbi-market-radar | ephemeral | novel.json, genre-config.json | — | — |
| shenbi-review-anti-ai | report | chapters/chapter-N.md, genre-config.json | audits/chapter-N-anti-ai.md | — |
| shenbi-review-character | report | chapters/chapter-N.md, characters/protagonist.md, characters/major/*.md, truth/character_matrix.md, truth/emotional_arcs.md | audits/chapter-N-character.md | — |
| shenbi-review-continuity | report | chapters/chapter-N.md, truth/current_state.md, truth/chapter_summaries.md, world/rules.md | audits/chapter-N-continuity.md | — |
| shenbi-review-dialogue | report | chapters/chapter-N.md, characters/protagonist.md, characters/major/*.md, truth/character_matrix.md | audits/chapter-N-dialogue.md | — |
| shenbi-review-era | report | chapters/chapter-N.md, genre-config.json, era-reference.md | audits/chapter-N-era.md | — |
| shenbi-review-fanfic | report | chapters/chapter-N.md, novel.json, source_canon/* | audits/chapter-N-fanfic.md | — |
| shenbi-review-foreshadowing | report | chapters/chapter-N.md, truth/pending_hooks.md, plans/chapter-N-plan.md, truth/subplot_board.md | audits/chapter-N-foreshadowing.md | — |
| shenbi-review-highpoint | report | chapters/chapter-N.md, plans/chapter-N-plan.md, genre-config.json | audits/chapter-N-highpoint.md | — |
| shenbi-review-long-span | report | chapters/chapter-N.md, chapters/*.md, genre-config.json | audits/chapter-N-long-span.md | — |
| shenbi-review-memo-compliance | report | chapters/chapter-N.md, plans/chapter-N-plan.md, truth/pending_hooks.md | audits/chapter-N-memo-compliance.md | — |
| shenbi-review-motivation | report | chapters/chapter-N.md, characters/protagonist.md, characters/major/*.md, truth/character_matrix.md | audits/chapter-N-motivation.md | — |
| shenbi-review-pacing | report | chapters/chapter-N.md, genre-config.json, truth/chapter_summaries.md | audits/chapter-N-pacing.md | — |
| shenbi-review-pov | report | chapters/chapter-N.md, genre-config.json, truth/character_matrix.md, truth/current_state.md | audits/chapter-N-pov.md | — |
| shenbi-review-reader-pull | report | chapters/chapter-N.md, plans/chapter-N-plan.md, truth/pending_hooks.md | audits/chapter-N-reader-pull.md | — |
| shenbi-review-sensitivity | report | chapters/chapter-N.md, genre-config.json, novel.json | audits/chapter-N-sensitivity.md | — |
| shenbi-review-spinoff | report | chapters/chapter-N.md, truth/parent_canon.md, world/rules.md, truth/pending_hooks.md | audits/chapter-N-spinoff.md | — |
| shenbi-review-texture | report | chapters/chapter-N.md, genre-config.json, plans/chapter-N-plan.md | audits/chapter-N-texture.md | — |
| shenbi-review-world-rules | report | chapters/chapter-N.md, world/rules.md, world/power_system.md, world/locations.md, world/story_bible.md, truth/chapter_summaries.md, truth/current_state.md | audits/chapter-N-world-rules.md | — |
| shenbi-foundation-review | report | world/*.md, characters/**/*.md, outline/*.md, truth/current_state.md, truth/chapter_summaries.md | foundation/review_report.md | — |
| shenbi-drift-guidance | report | chapters/chapter-N.md, audits/chapter-N-*.md | truth/drift_guidance.md | truth/audit_drift.md |
| shenbi-chapter-pattern | report | chapters/*.md, truth/chapter_summaries.md, genre-config.json | outline/chapter_patterns.md | — |

(`—` means an empty list.)

- [ ] **Step 2: Implement the migrator**

`tools/migrate_contract_to_frontmatter.py`:

```python
#!/usr/bin/env python3
"""One-time migrator (spec §7.2): body 数据契约 -> frontmatter contract.

Reads the per-skill CLASSIFICATION table below, rewrites each SKILL.md's
frontmatter to add the `contract:` block, and strips the hand-written body
数据契约 block. Idempotent: re-running on already-migrated skills is a no-op.

Run once:  uv run python tools/migrate_contract_to_frontmatter.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"

# (kind, reads, writes, updates) — the authoritative table from Task 12 Step 1.
# Empty list = []. All paths MUST exist in truth-files.yaml (load_contract enforces).
CLASSIFICATION: dict[str, dict[str, object]] = {
    "shenbi-chapter-drafting": {"kind": "artifact", "reads": ["plans/chapter-N-plan.md", "style/style_profile.md", "genre-config.json", "truth/audit_drift.md"], "writes": ["chapters/chapter-N.md"], "updates": []},
    # ... (paste the FULL table from Step 1 here; one entry per skill) ...
}

# Each skill below is filled from Step 1's table at implementation time.
# (The implementer copies all 57 rows verbatim from the table above.)


def _yaml_list(items: list[str]) -> str:
    if not items:
        return " []"  # space before [] — `reads:[]` (no space) is not reliably parsed by PyYAML
    return "\n" + "\n".join(f"    - {i}" for i in items)


def _build_frontmatter(name: str, description: str, spec: dict[str, object]) -> str:
    reads = _yaml_list(spec["reads"])  # type: ignore[arg-type]
    writes = _yaml_list(spec["writes"])  # type: ignore[arg-type]
    updates = _yaml_list(spec["updates"])  # type: ignore[arg-type]
    contract = (
        "contract:\n"
        f"  kind: {spec['kind']}\n"
        f"  reads:{reads}\n"
        f"  writes:{writes}\n"
        f"  updates:{updates}\n"
    )
    return f"---\nname: {name}\ndescription: {description}\n{contract}---\n"


def _strip_body_contract(body: str) -> str:
    """Remove the hand-written ## 数据契约 ... (up to the next ## heading)."""
    return re.sub(r"## 数据契约.*?(?=^## |\Z)", "", body, count=1, flags=re.DOTALL | re.MULTILINE)


def migrate_skill(skill: str) -> bool:
    spec = CLASSIFICATION.get(skill)
    if spec is None:
        return False
    md_path = SKILLS / skill / "SKILL.md"
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.DOTALL)
    if not m:
        return False
    fm = m.group(1)
    name_m = re.search(r"^name:\s*(.+)$", fm, flags=re.MULTILINE)
    desc_m = re.search(r"^description:\s*(.+)$", fm, flags=re.MULTILINE)
    assert name_m and desc_m, skill
    new_fm = _build_frontmatter(name_m.group(1).strip(), desc_m.group(1).strip(), spec)
    new_body = _strip_body_contract(m.group(2))
    # The auto-generated body view is rendered by `just generate`, not here.
    md_path.write_text(new_fm + new_body.lstrip("\n"), encoding="utf-8")
    return True


def main() -> int:
    done = [s for s in CLASSIFICATION if migrate_skill(s)]
    print(f"migrated {len(done)} skills")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

> **Implementation note:** copy all 57 rows from the Step 1 table into `CLASSIFICATION` verbatim. Run `uv run python tools/migrate_contract_to_frontmatter.py`. Then run `uv run python tools/lint_contracts.py` — every skill must load (registry resolution). Fix any path not in the registry by adding it to `truth-files.yaml` (Task 5), not by editing the contract.

- [ ] **Step 3: Commit the migrator (not yet run)**

```bash
git add tools/migrate_contract_to_frontmatter.py
git commit -m "feat(migrate): one-time body->frontmatter contract migrator (spec §7.2)"
```

---

### Task 13: Run migration, rewrite tests, fix the test-input gap, enable lints

This is the merge checkpoint: after it, `just check` + all lints are green.

**Files:**
- Modify: all `skills/shenbi-*/SKILL.md` (via the migrator), `tests/unit/test_dispatcher_executor.py`, `tests/unit/test_phase_runner.py`
- Populate: `tests/fixtures/audits/`
- Modify: `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `justfile`

- [ ] **Step 1: Run the migrator**

Run: `uv run python tools/migrate_contract_to_frontmatter.py`
Expected: `migrated 57 skills`.

- [ ] **Step 2: Run `just generate` to render body views + regenerate deps.json**

Run: `just generate`
Expected: exit 0. `git status` shows modified `tests/tiers/deps.json` (regenerated `expected_outputs` — the stale `config/style_profile.md` / `volumes/volume-*-summary.md` / `world/faction-relations.md` entries are gone, replaced by member-derived globs), new `docs/framework/dependency-dag.json` and `docs/framework/truth-files.index.json`, and every `skills/*/SKILL.md` carrying the sentinel-delimited auto-generated `数据契约` block. (The bijection self-check inside the generator passes; if it raises, a member write was dropped — fix the contract, don't suppress.)

- [ ] **Step 3: Verify every contract loads**

Run: `uv run python tools/lint_contracts.py && echo CLEAN`
Expected: `CLEAN`. If a skill fails, fix the contract or registry — do not suppress.

- [ ] **Step 4: Rewrite the contract-format unit tests against `load_contract`**

In `tests/unit/test_dispatcher_executor.py`, the `derive_input_files`/`derive_output_files` tests now exercise real migrated skills — assert concrete expected values (e.g. `derive_input_files("shenbi-chapter-drafting")` returns exactly `["plans/chapter-N-plan.md", "style/style_profile.md", "genre-config.json", "truth/audit_drift.md"]`). In `tests/unit/test_phase_runner.py`, the `cmd_pre_skill` tests (already rewritten in Task 6 Step 5) now use frontmatter fixtures — confirm they pass against the real loader.

- [ ] **Step 5: Populate the empty audit-fixture gap (spec §7.6)**

`tests/fixtures/audits/` currently holds only `.gitkeep` but `shenbi-drift-guidance`'s scenario reads audit files from it. Add representative fixtures the scenario references:

```bash
for dim in anti-ai character continuity dialogue; do
  cat > "tests/fixtures/audits/chapter-1-${dim}.md" <<EOF
## ${dim} 审计报告

**章节**: 第1章
**结果**: 通过

### 检查结果
(none)
EOF
done
```

> The heredoc is **unquoted** (`<<EOF`, not `<<'EOF'`) so `${dim}` expands into both the filename and the report heading. First run `grep -rn "fixtures/audits\|audits/chapter" tests/skill-behavior/ tests/skill-triggering/ 2>/dev/null` (and the `shenbi-drift-guidance` scenario) to find the **exact** chapter index and dimension set the scenario actually reads, then match those filenames precisely — the goal is that every audit path the drift-guidance test opens exists.

- [ ] **Step 6: Normalize terminology + section-headers (Layer A/B)**

Run: `uv run python tools/lint_repo_consistency.py` — fix every reported violation:
- **Terminology:** `hook pool` → `hook ledger` (in `shenbi-review-foreshadowing`), `truth-files` → `truth files`, `the author` → `your human partner` (OD-3).
- **Section-headers:** the ~7 generative deviants normalize to `## 输出格式`; worldbuilding's `## 输出契约` → `## 输出格式`; remove ad-hoc `### Key Results` / `输出` headers or rename to `输出格式`.

- [ ] **Step 7: Enable all lints in pre-commit + CI**

In `.pre-commit-config.yaml` add (under `repo: local`):

```yaml
      - id: lint-contracts
        name: contract schema + completeness (spec §5.5 #1,#2)
        entry: uv run python tools/lint_contracts.py
        language: system
        pass_filenames: false
      - id: lint-repo-consistency
        name: body-ban + loader-uniqueness + terminology (spec §5.5 #3,#4,#7)
        entry: uv run python tools/lint_repo_consistency.py
        language: system
        pass_filenames: false
      - id: contract-sync-idempotency
        name: contract-sync idempotency (spec §5.5 #5)
        entry: bash -c 'uv run shenbi-sync-contracts >/dev/null && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/'
        language: system
        pass_filenames: false
```

In `.github/workflows/ci.yml`, add a dedicated `contract-sync` job (the generator only writes generated paths, so an unscoped `git diff` is exact) and a lint step in the `quality` job:

```yaml
      - name: Contract + repo-consistency lints
        run: |
          uv run python tools/lint_status_strings.py
          uv run python tools/lint_contracts.py
          uv run python tools/lint_repo_consistency.py
```

```yaml
  contract-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Regenerate contract-derived artifacts
        run: uv run shenbi-sync-contracts
      - name: Idempotency — generated artifacts (deps.json, docs/framework, skills body views) must match committed
        run: git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/
```

In `justfile`, extend `check`:

```makefile
check:
	uv run python tools/lint_status_strings.py
	uv run python tools/lint_contracts.py
	uv run python tools/lint_repo_consistency.py
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/shenbi/
	uv run basedpyright
	uv run shenbi-sync-contracts >/dev/null && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/
	uv run pytest -n auto -m "not last" --hypothesis-profile=ci
	uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci
```

- [ ] **Step 8: Full verification — `just check` must be green**

Run: `just check`
Expected: all green (lints, ruff, mypy, basedpyright, sync idempotency, tests). This is the merge gate: the prevention model is live — every audit class is now impossible-to-land (C/C-body/D2/D4/D3) or detected-at-CI (D1/A/B).

- [ ] **Step 9: Commit the migration**

```bash
git add -A
git commit -m "feat(contract): migrate 57 skills to frontmatter single-source; enable lints (spec §7)"
```

---

## Self-Review (spec coverage)

**1. Spec coverage — every requirement maps to a task:**

| Spec section | Audit class | Task(s) |
|---|---|---|
| §3.2 contract schema (OutputKind, typed lists) | C | 4 |
| §3.3 body-prose ban + auto-render | C/body | 7 (render), 10 (ban), 13 (run) |
| §4.2 honesty table (impossible vs detected) | all | 4,5,9,10,13 (mechanisms); A/B explicitly "detected" via Task 10/13 |
| §5.1 contract.py single loader | D2 | 4, 6 |
| §5.2 status.py typed enums + results | D3 | 1, 2, 3 |
| §5.3 truth-files.yaml registry | D1 | 5 |
| §5.4 generator (expected_outputs, DAG, index, body) | D4, OD-1 | 7, 8 |
| §5.5 lints #1–#7 | — | 9 (#1,#2), 10 (#3,#4,#7), 3 (#6), 8/13 (#5); #6 status-typing enforced by mypy+basedpyright (Task 1–3) |
| §6 audit→solution mapping | — | covered 1:1 above |
| §7 migration steps 1–7 | — | 5 (1), 12 (2), 6 (3), 13 Step 4 (4), 13 Step 1–2 (5), 13 Step 5 (6), 13 Step 1–9 (7) |
| §8 testing (business value) | — | every task is TDD; prevention tests assert the inconsistent form is rejected |
| OD-1 (auto body block) | — | 7 (render), 13 (run) |
| OD-2 (keep deps.json, generate expected_outputs) | — | 7 |
| OD-3 (hook ledger canonical) | B | 13 Step 6 |

No spec section is unaccounted for.

**2. Placeholder scan:** the only intentionally-truncated code is the migrator's `CLASSIFICATION` dict (Task 12), which is explicitly "paste all 57 rows from Step 1's table verbatim" — the full table is given in Step 1, so it is complete, not a placeholder. No `TBD`/`TODO`/"add error handling"/"similar to" anywhere.

**3. Type consistency:** `load_contract` returns `Contract` (used identically in Tasks 6, 7, 9); `OutputKind` members (`ARTIFACT`/`REPORT`/`EPHEMERAL`) match the migration table; status enum names (`GateStatus.PASS`, `CommandStatus.OK`, `PhaseState.CREATED`, `ScoringStatus.REJECT`, `ScoreClassification.PASS_EXCELLENT`) are consistent across Tasks 1–3 and drive `STATUS_STRING_LITERALS` consumed by the Task 3 lint; `STATUS_KEYS` (`status`/`state`/`classification`) covers all three D3 domains; generator functions `normalize_to_glob`/`dag_key`/`derive_expected_outputs`/`verify_bijection`/`build_dag(contracts, registry)`/`load_all_contracts` are defined in Task 7 and the signatures the Task 9 lint imports (`load_all_contracts`, `build_dag`, `dag_key`) match exactly; `find_completeness_violations(contracts, dag, registry)` is glob-aware.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-21-consistency-single-source.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. (Tasks 1–3 [Part I / D3] can be executed as a self-contained batch first.)

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
