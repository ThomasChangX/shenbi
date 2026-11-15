# Spec #92 test-ci-hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the dead `_tool_hashes` block (keeping the calibration half of the dual-role script), consolidate deps loading and REPO_ROOT, retire the `unit` marker, single-source the coverage threshold with just sub-recipes, purge test sediment, and add a dispatch-payload constructor.

**Architecture:** Eight tasks mapping 1:1 to spec T1-T6 plus a final verification task. All changes are test/CI infrastructure — no pipeline behavior changes. T1 is a same-commit surgical delete+rename; T2 introduces one typed loader consumed by six call sites; T3-T6 are mechanical sweeps; T8 runs the full acceptance battery.

**Tech Stack:** Python 3.11+ / pydantic v2 / pytest 9 / just / ruff / mypy / basedpyright / uv.

## Global Constraints

- Every commit lists explicit file paths (pathspec commit; `git add -A` forbidden — user unstaged docs changes must survive untouched).
- Before EVERY commit: `git branch --show-current` must print `chore/spec-92-test-ci-hygiene` (D-1 incident lesson).
- `just`/`uv run` only for verification (CI-isomorphic); system python results are not evidence.
- No `print()` in `src/shenbi/` (ruff T20); structlog for logging; pathlib for I/O.
- Spec acceptance criteria are the definition of done (spec §2, items 1-5).
- T1's data-key + schema-field deletion and the rename sweep land in ONE commit (extra:"forbid" makes split commits permanently red — spec §3).
- pytest-randomly stays installed; `just test` recipe gains `-p no:randomly` (T4); other legs' exposure is pre-existing (spec r3.2 note).

---

### Task 1: T1 — `_tool_hashes` deletion + dual-role script slim-down & rename

**Files:**
- Modify: `tests/lock-tool-hashes.sh` → **rename** to `tests/lock-calibration-hash.sh` (git mv), delete lines 1-32 (tool-hash half), keep :34-59 (calibration half)
- Modify: `tests/tiers/deps.json` (delete `"_tool_hashes"` key, lines 205-422, 217 entries)
- Modify: `src/shenbi/contracts/schemas/deps.py:62` (delete `tool_hashes` field) and `:7-11` docstring (remove `_tool_hashes` from keys enumeration)
- Modify: `tools/lint_registry_reconcile.py` (delete R3 face :420-437, docstring :23-25 R3 paragraph, main wiring :492)
- Modify: `src/shenbi/gates/g0.py` (:187 comment, :218/:232/:251 must_fix strings, :235 comment — name swap + wording)
- Modify: `tests/unit/test_lint_registry_reconcile.py` (delete two R3 cases :182-193 `test_r3_hash_byte_flip_fails`, :195-209 `test_r3_absent_targets_skipped`)
- Modify: `tests/unit/gates/test_g0_calibration_hash.py` (:14 docstring name, :37 fixture base, :86/:109 assertion strings)
- Modify: `tests/unit/contracts/schemas/test_deps.py` (:68, :106, :149 — tool_hashes assertions/roundtrip key)
- Modify: `justfile:56` (shellcheck list name swap)
- Modify: `goal-prompt.md:28/:88`, `command-to-give.md:24`, `tests/fixtures/calibration/README.md:61-65` (live docs)
- Test: existing `tests/unit/gates/test_g0_calibration_hash.py` (kept green = G0.14 survival proof)

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `tests/lock-calibration-hash.sh` (calibration-only re-lock script — referenced by g0.py must_fix strings and calibration README); deps.json without `_tool_hashes`; `DepsDoc` without `tool_hashes` field (Task 2's `load_deps` returns this shape)

- [ ] **Step 1: Characterize current G0.14 green baseline**

Run: `uv run pytest tests/unit/gates/test_g0_calibration_hash.py tests/unit/contracts/schemas/test_deps.py -q`
Expected: all PASS (baseline before surgery).

- [ ] **Step 2: Slim and rename the script**

```bash
git mv tests/lock-tool-hashes.sh tests/lock-calibration-hash.sh
```

Edit `tests/lock-calibration-hash.sh`: delete everything from the header comment "Lock current SHA256 hashes of tool scripts..." through the end of the first python3 block (original :1-32, including the `echo "=== Locking tool hashes ==="` line). New header:

```bash
#!/bin/bash
# Lock the combined SHA256 of calibration anchors into deps.json.
# Run after any intentional tests/fixtures/calibration change (G0.14 re-lock).
set -euo pipefail
```

Keep the second block (`echo "=== Locking calibration anchor hashes ==="` onward) unchanged.

- [ ] **Step 3: Delete the data key and schema field (same commit as Step 2-8)**

```bash
uv run python - << 'EOF'
import json
from pathlib import Path
p = Path("tests/tiers/deps.json")
d = json.loads(p.read_text(encoding="utf-8"))
del d["_tool_hashes"]
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
EOF
```

In `src/shenbi/contracts/schemas/deps.py`: delete line 62 (`tool_hashes: dict[str, str] = Field(default_factory=dict, alias="_tool_hashes")`); in the module docstring key enumeration replace `` (``t2-phases``, ``t3-pipelines``, ``_tool_hashes``, ``_out_of_pipeline``, `` `` with `` (``t2-phases``, ``t3-pipelines``, ``_out_of_pipeline``, ``_calibration_hashes`` `` (also add the calibration key — it IS stored and now the only underscored hash key).

- [ ] **Step 4: Delete R3 face in lint_registry_reconcile.py**

Delete function `_r3_hash_freshness` (:420-437), the R3 paragraph in module docstring (:23-25), and its `main()` wiring line (:492). Grep first to confirm exact current spans: `grep -n "_r3_hash_freshness\|R3 invariant" tools/lint_registry_reconcile.py`.

- [ ] **Step 5: g0.py name swap + comment wording**

- :187 `Mirrors the existing `_tool_hashes` integrity pattern.` → `Mirrors the calibration lock in tests/lock-calibration-hash.sh.`
- :218/:232/:251: `tests/lock-tool-hashes.sh` → `tests/lock-calibration-hash.sh` (three must_fix strings)
- :235 `# Accept both bare hex and the "sha256:<hex>" envelope used by _tool_hashes.` → `# Accept both bare hex and the "sha256:<hex>" envelope.`

- [ ] **Step 6: Test edits**

- `tests/unit/test_lint_registry_reconcile.py`: delete `test_r3_hash_byte_flip_fails` (:182-193) and `test_r3_absent_targets_skipped` (:195-209) — verify by function name, not line, before deleting.
- `tests/unit/gates/test_g0_calibration_hash.py`: :14 docstring `hint: run tests/lock-tool-hashes.sh` → new name; :37 `deps: dict[str, Any] = {"_tool_hashes": {}}` → `deps: dict[str, Any] = {}`; :86/:109 `"lock-tool-hashes.sh" in m` → `"lock-calibration-hash.sh" in m`.
- `tests/unit/contracts/schemas/test_deps.py`: delete `:68` (`assert d.tool_hashes` line — locate exact by grep `d.tool_hashes`), remove `"_tool_hashes": {...}` entry from the :106 roundtrip payload, delete `:149` `assert d.tool_hashes == {}`.

- [ ] **Step 7: justfile + live docs**

- `justfile:56`: `tests/lock-tool-hashes.sh` → `tests/lock-calibration-hash.sh` in the shellcheck list.
- `goal-prompt.md:28/:88`, `command-to-give.md:24`: replace instructions to run the old script with `tests/lock-calibration-hash.sh`; DELETE the false claims that G0.13/G7.17 verify tool hashes (G0.13 = independence markers; G7.17 does not exist); say G0.14 locks calibration anchors.
- `tests/fixtures/calibration/README.md:64`: `tests/lock-tool-hashes.sh` → `tests/lock-calibration-hash.sh`.

- [ ] **Step 8: Verify criteria + G0.14 survival**

Run:
```bash
git grep -n "_tool_hashes" -- src tools tests justfile goal-prompt.md command-to-give.md ':!tests/fixtures'; echo "rc=$?"
git grep -n "lock-tool-hashes" -- src tools tests justfile goal-prompt.md command-to-give.md ':!tests/fixtures'; echo "rc=$?"
uv run pytest tests/unit/gates/test_g0_calibration_hash.py tests/unit/contracts/schemas/test_deps.py tests/unit/test_lint_registry_reconcile.py -q
uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume
wc -l tests/tiers/deps.json
```
Expected: both greps rc=1 (zero hits); tests PASS; lint rc=0; deps.json <230 lines.

- [ ] **Step 9: Rehearsal acceptance (spec §2.1)**

```bash
printf '\n# rehearsal probe\n' >> src/shenbi/exceptions.py
uv run shenbi-sync-contracts >/dev/null && git diff --stat -- tests/tiers/deps.json; echo "diff-rc lines: $(git diff -- tests/tiers/deps.json | wc -l)"
git checkout -- src/shenbi/exceptions.py tests/tiers/deps.json
```
Expected: `git diff -- tests/tiers/deps.json` empty (0 lines) — post-R3-deletion, no src edit can dirty deps.json.

- [ ] **Step 10: Commit (single commit for the whole T1 surface)**

```bash
git branch --show-current   # MUST print chore/spec-92-test-ci-hygiene
git add tests/lock-calibration-hash.sh tests/tiers/deps.json src/shenbi/contracts/schemas/deps.py tools/lint_registry_reconcile.py src/shenbi/gates/g0.py tests/unit/test_lint_registry_reconcile.py tests/unit/gates/test_g0_calibration_hash.py tests/unit/contracts/schemas/test_deps.py justfile goal-prompt.md command-to-give.md tests/fixtures/calibration/README.md
git commit -m "chore: spec #92 T1 — delete _tool_hashes block, slim lock script to calibration-only (renamed lock-calibration-hash.sh)"
```

---

### Task 2: T2a — typed loader `load_deps` + six-reader conversion + thin wrapper

**Files:**
- Modify: `src/shenbi/contracts/schemas/deps.py` (add `load_deps`)
- Modify: `src/shenbi/phase_runner.py:38-54` (thin wrapper), `:295-305`, `:382-390` (attribute access)
- Modify: `src/shenbi/scoring.py:284-305` (loader + attribute access)
- Modify: `src/shenbi/gates/g5.py:82-90`, `src/shenbi/gates/g6.py:39-47` (loader + attribute access)
- Modify: `src/shenbi/gates/g0.py:210-221` (loader in check_calibration_integrity + attribute access)
- Modify: `tests/unit/test_phase_runner.py` (5 monkeypatch lambdas at :476/:492/:512/:529/:638)
- Test: `tests/unit/contracts/schemas/test_deps.py` (new loader tests)

**Interfaces:**
- Consumes: Task 1's `DepsDoc` (without `tool_hashes`)
- Produces: `def load_deps(deps_path: Path) -> DepsDoc` in `shenbi.contracts.schemas.deps` (raises `OSError`/`pydantic.ValidationError` — callers own error mapping; pydantic v2 wraps malformed JSON in ValidationError). NOTE: spec says `load_deps(repo_root)`; plan pins `load_deps(deps_path: Path)` taking the deps.json **file path** — all six call sites already hold/construct the full path (g0 receives it as a parameter), file-path is strictly more general. Recorded as deviation.

- [ ] **Step 1: Write failing loader tests**

Append to `tests/unit/contracts/schemas/test_deps.py`:

```python
def test_load_deps_roundtrip() -> None:
    """load_deps reads the real deps.json shape into DepsDoc."""
    from shenbi.contracts.schemas.deps import load_deps

    src = Path(__file__).resolve().parents[4] / "tests" / "tiers" / "deps.json"
    d = load_deps(src)
    assert isinstance(d, DepsDoc)
    assert d.calibration_hashes  # real file carries the G0.14 lock


def test_load_deps_corrupt_fails(tmp_path: Path) -> None:
    """Malformed JSON surfaces as pydantic ValidationError (v2 contract)."""
    from shenbi.contracts.schemas.deps import load_deps
    import pytest
    from pydantic import ValidationError

    bad = tmp_path / "deps.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_deps(bad)


def test_load_deps_extra_key_rejected(tmp_path: Path) -> None:
    from shenbi.contracts.schemas.deps import load_deps

    bad = tmp_path / "deps.json"
    bad.write_text('{"_tool_hashes": {}}', encoding="utf-8")
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        load_deps(bad)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/contracts/schemas/test_deps.py -q -k load_deps`
Expected: FAIL (ImportError: load_deps).

- [ ] **Step 3: Implement loader in deps.py**

```python
from pathlib import Path


def load_deps(deps_path: Path) -> DepsDoc:
    """Load and validate tests/tiers/deps.json as :class:`DepsDoc`.

    Raises OSError / pydantic.ValidationError — callers own the error
    surface (CLI exit, gate fail tuple, marker list). NOTE: pydantic v2
    ``model_validate_json`` raises ValidationError for malformed JSON too
    (repo precedent: state_settling.py:867 catches ValueError around it).
    """
    return DepsDoc.model_validate_json(deps_path.read_text(encoding="utf-8"))
```

Callers' catch-tuples become `(OSError, ValidationError)` — drop `json.JSONDecodeError` from new catch sites (ValidationError subsumes it for this loader).

- [ ] **Step 4: Convert the six readers**

For each reader: replace `json.loads(...)`/`jload(...)` with `from shenbi.contracts.schemas.deps import load_deps`, catch `(OSError, ValidationError)` (import ValidationError from pydantic — the 2-tuple is the loader's contract; see Step 3 note), and convert dict access to attribute access:

- `phase_runner.py:295-305` & `:382-390`: `deps.get("t2-phases", {}).get(phase, {})` → `deps.t2_phases.get(phase)`; `phase_data.get("prerequisites", [])` → `phase_data.prerequisites if phase_data else []`. Thin wrapper `:38-54`:

```python
def load_deps() -> DepsDoc:
    """Load tests/tiers/deps.json; exit structured on corruption (F145)."""
    try:
        return deps_load(TESTS / "tiers" / "deps.json")
    except (OSError, ValidationError) as exc:
        log.error("t2_deps_json_corrupt", path=str(TESTS / "tiers" / "deps.json"), error=str(exc))
        emit_json(
            {"status": CommandStatus.ERROR, "phase": None, "message": "t2 deps.json unreadable"}
        )
        sys.exit(1)
```

Keep the module-level name `load_deps` (monkeypatch target!) — i.e. rename existing `load_deps` body to call `deps_load` (alias import `from shenbi.contracts.schemas.deps import load_deps as deps_load`). Both `cmd_pre_score` and the `:384` site keep calling `load_deps()` with zero args.

- `scoring.py:284-305`: loader + `phase_name in deps.t2_phases` + `deps.t2_phases[phase_name].prerequisites`; keep the fail-closed `return [f"t2_deps_json_corrupt:..."]` on the same exception tuple. (The t3 branch :303-309 never reads deps — only the G6 marker file — so no t3 conversion exists; verified in plan review.)
- `g5.py:82-90`: `deps.t2_phases.get(phase_name)`; keep `fail("G5", ...)` mapping.
- `g6.py:39-47`: `deps.t3_pipelines.get(pipeline_name)` (drop the `, {}` default — attribute is a dict already); `min_ratio = pipe_data.min_chapter_ratio if pipe_data else 0.5` (preserve current default 0.5 exactly). Add one comment at the site: PipelineDeps.min_chapter_ratio schema default is 0.0 — a future hand-added pipeline entry omitting the key would silently get 0.0 (gate passes anything); all 3 real entries carry explicit values (long-form 0.5 / short-form 1.0 / import-form 1.0) — verified in plan review.
- `g0.py:210-221`: `deps = load_deps(deps_path)` inside the existing try; `deps.calibration_hashes.get("combined")`; keep the FAIL tuple mapping (except tuple becomes the 2-tuple `(OSError, ValidationError)`).

- [ ] **Step 5: Adapt the 5 monkeypatch lambdas**

In `tests/unit/test_phase_runner.py`, each `monkeypatch.setattr(phase_runner, "load_deps", lambda: deps)` where `deps` is a plain dict — convert the dict literal to `DepsDoc` construction. Read each site first; the canonical conversion:

```python
from shenbi.contracts.schemas.deps import DepsDoc, PhaseDeps

...
monkeypatch.setattr(
    phase_runner,
    "load_deps",
    lambda: DepsDoc(t2_phases={"pre-score": PhaseDeps(prerequisites=["shenbi-worldbuilding"])}),
)
```

(Match each dict's actual keys — use `PhaseDeps`/`PipelineDeps` per key; run the file and fix per AttributeError until green.)

- [ ] **Step 6: Run affected suites**

Run: `uv run pytest tests/unit/contracts/schemas/test_deps.py tests/unit/test_phase_runner.py tests/unit/test_scoring*.py tests/unit/gates/test_g5*.py tests/unit/gates/test_g6*.py tests/unit/gates/test_g0*.py -q`
Expected: all PASS (locate exact test files by `ls tests/unit/gates | grep -E "g0|g5|g6"` first).

- [ ] **Step 7: Loader-convergence criterion**

Run: `git grep -nE 'json\.loads\(.*deps_path|jload\(.*deps\.json|read_text.*deps\.json' -- src/shenbi/ | grep -v contracts/schemas/deps.py | grep -v sync_contracts.py`
Expected: zero hits (sync_contracts RMW excluded by design; log literals excluded — verify output manually).

- [ ] **Step 8: Commit**

```bash
git branch --show-current
git add src/shenbi/contracts/schemas/deps.py src/shenbi/phase_runner.py src/shenbi/scoring.py src/shenbi/gates/g5.py src/shenbi/gates/g6.py src/shenbi/gates/g0.py tests/unit/test_phase_runner.py tests/unit/contracts/schemas/test_deps.py
git commit -m "feat: spec #92 T2a — typed load_deps loader + six-reader conversion + phase_runner thin wrapper"
```

---

### Task 3: T2b — `REPO_ROOT` constant + parents[N] purge

**Files:**
- Modify: `src/shenbi/paths.py` (add constant)
- Modify: `src/shenbi/phase_runner.py:34`, `src/shenbi/scoring.py:286`, `src/shenbi/gates/shared.py:31`, `src/shenbi/gates/g0_purity.py:105`, `src/shenbi/pipeline/dispatch_helper.py:87`, `src/shenbi/plugins/generate.py:22`, `src/shenbi/dispatcher/modes/codex.py:282-283`
- Modify: `src/shenbi/sync_contracts.py:24` (importer — no PROJECT redefinition; stays via shared)
- Test: new `tests/unit/test_paths_repo_root.py`

**Interfaces:**
- Consumes: Task 2's loader (scoring.py site rewrite folds into its parents-purge)
- Produces: `REPO_ROOT: Final[Path]` in `shenbi.paths` — single definition; `gates.shared.PROJECT`, `dispatch_helper._PROJECT_ROOT`, `plugins.generate.REPO_ROOT` become aliases of it (keep the public names as `PROJECT = REPO_ROOT` re-exports to avoid touching their downstream consumers; the CODomain is the definitions count, not the names).

- [ ] **Step 1: Write failing test**

`tests/unit/test_paths_repo_root.py`:

```python
"""spec #92 T2b: REPO_ROOT single-source + parents[N] purge."""

import subprocess


def test_repo_root_points_at_repo() -> None:
    from shenbi.paths import REPO_ROOT

    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (REPO_ROOT / "justfile").exists()


def test_no_parents_magic_in_src() -> None:
    """parents[2|3|4] outside paths.py is forbidden (spec T2 criterion)."""
    result = subprocess.run(
        ["git", "grep", "-nE", r"parents\[[234]\]", "--", "src/shenbi/"],
        capture_output=True,
        text=True,
    )
    hits = [line for line in result.stdout.splitlines() if "paths.py" not in line]
    assert hits == [], f"parents[N] survivors: {hits}"
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/unit/test_paths_repo_root.py -q`
Expected: `test_no_parents_magic_in_src` FAIL with 8 survivors (7 code points + codex comment).

- [ ] **Step 3: Add the constant and convert the 7 sites + comment**

In `src/shenbi/paths.py` (top, after imports):

```python
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
"""Single source for the repository root (spec #92 T2b).

Replaces the four same-value definitions (gates.shared.PROJECT,
dispatch_helper._PROJECT_ROOT, plugins.generate.REPO_ROOT, codex local) and
the per-file parents[N] derivations. sync_contracts imports PROJECT from
gates.shared and stays a consumer, not a definer.
"""
```

Conversions (each file: `from shenbi.paths import REPO_ROOT` where needed; ANCHOR BY SYMBOL not line — Task 2 shifts scoring.py line numbers before Task 3 runs, so grep `parents\[[234]\]` per file first):
- `phase_runner.py:34`: `TESTS = REPO_ROOT / "tests"`
- `scoring.py:286`: fold into Task 2's rewrite — `deps_path = REPO_ROOT / "tests" / "tiers" / "deps.json"`
- `gates/shared.py:31`: `PROJECT = REPO_ROOT` (keep name PROJECT — downstream importers unchanged)
- `g0_purity.py:105`: `baseline_path = REPO_ROOT / "tests/fixtures/provenance-baseline.json"`
- `dispatch_helper.py:87`: `_PROJECT_ROOT = REPO_ROOT`
- `plugins/generate.py:22`: `REPO_ROOT = paths.REPO_ROOT` — import as `from shenbi.paths import REPO_ROOT as _ROOT` then `REPO_ROOT: Final[Path] = _ROOT` (or simply switch its internal uses to the import; keep the module attribute for its consumers — grep `from shenbi.plugins.generate import` first)
- `codex.py:282-283`: DELETE the comment line :282, change :283 to `repo_root = REPO_ROOT` (import)

- [ ] **Step 4: Verify**

Run: `uv run pytest tests/unit/test_paths_repo_root.py -q && uv run mypy src/shenbi/ && uv run basedpyright 2>&1 | tail -3`
Expected: 2 PASS; type checks clean.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/shenbi/paths.py src/shenbi/phase_runner.py src/shenbi/scoring.py src/shenbi/gates/shared.py src/shenbi/gates/g0_purity.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/plugins/generate.py src/shenbi/dispatcher/modes/codex.py tests/unit/test_paths_repo_root.py
git commit -m "feat: spec #92 T2b — REPO_ROOT single-source in paths.py, purge parents[N] magic (7 sites + comment)"
```

---

### Task 4: T3 — `unit` marker retirement (option b) + test/test-all merge

**Files:**
- Modify: `pyproject.toml:583-589` (markers: delete `unit` + `slow`), `justfile:72-78` (test recipe), `tests/test_justfile_injection.py:87-93`
- Modify: ~197 test files (sweep `@pytest.mark.unit` decorators + `pytestmark` entries)
- Modify: `AGENTS.md:36`, `goal-prompt.md`, `command-to-give.md` (just test description)
- Test: sweep verified by collection count + grep

**Interfaces:**
- Consumes: nothing
- Produces: `just test` = `-m "not last" --no-cov -p no:randomly` (merged fast path); markers registry without `unit`/`slow`

**Decision (plan-pinned): option (b)** — same-batch sweep of all 1,296 annotations (35 `pytestmark` form + ~1,261 decorator form). Rationale: spec-recommended; zero marker-count assertions exist in tests (verified); leaves no dead weight. Baseline: not-last collection = **6,396**; `-m unit` = 2,054 (fast path drops 67.9% today).

- [ ] **Step 1: Pin the baseline**

Run: `uv run pytest --collect-only -q -m "not last" 2>/dev/null | tail -1`
Expected: `6396/6399 tests collected (3 deselected)` — record exact number.

- [ ] **Step 2: Sweep script (one-shot, run via uv run python)**

```python
"""One-shot marker sweep (spec #92 T3b). Run once; verify with git diff."""

import re
from pathlib import Path

DECORATOR = re.compile(r"^\s*@pytest\.mark\.unit\s*$", re.M)
ASSIGN_FULL = re.compile(r"^pytestmark = pytest\.mark\.unit\s*$", re.M)
ASSIGN_LIST_ITEM = re.compile(
    r"^(\s*)pytestmark = \[\s*\n(?:\s*pytest\.mark\.unit,\s*\n)+\s*\]\s*$", re.M
)
IN_LIST = re.compile(r"^\s*pytest\.mark\.unit,?\s*$", re.M)

changed = 0
for p in Path("tests").rglob("test_*.py"):
    t = p.read_text(encoding="utf-8")
    orig = t
    t = ASSIGN_LIST_ITEM.sub("", t)
    t = ASSIGN_FULL.sub("", t)
    t = IN_LIST.sub("", t)  # unit inside pytestmark = [...] lists
    t = DECORATOR.sub("", t)  # standalone decorator lines
    if t != orig:
        p.write_text(t, encoding="utf-8")
        changed += 1
print(f"files changed: {changed}")
```

Then run `uv run ruff check --fix tests/ && uv run ruff format tests/` — the sweep strands ~110 files whose only remaining `pytest` reference was the marker (unused-import F401; NOT covered by the tests/** per-file-ignores amnesty), and re-format absorbs the blank lines the regex removal leaves behind. Then ALSO delete the dead marker smoke test `test_unit_marker_works` (tests/unit/test_pytest_framework.py:23-26 — its docstring carries the literal `@pytest.mark.unit`, which the grep would otherwise count; the marker's retirement makes the test meaningless). Then: `git diff --stat -- tests/ | tail -1` (expect ~197 files), `git grep -c "pytest.mark.unit" -- tests/ | wc -l` (expect 0 files).

- [ ] **Step 3: Delete marker registrations**

`pyproject.toml` markers list: delete the `unit` and `slow` lines (:584/:588-ish; locate by grep `markers =` then read the block).

- [ ] **Step 4: Merge recipes**

justfile:

```just
# Run the fast test suite (all not-last tests)
test *args:
    uv run pytest -n auto --dist loadscope -m "not last" --no-cov -p no:randomly "$@"
```

Delete the `test-all` recipe. In `tests/test_justfile_injection.py` EXPECTED_CALLS delete the `"test-all": [["-q"]],` line (:93).

- [ ] **Step 5: Doc sync**

- `AGENTS.md:36`: `- just test — Fast unit tests only` → `- just test — Fast suite (all \`not last\` tests, no coverage)`
- grep `just test` in goal-prompt.md / command-to-give.md and align wording.

- [ ] **Step 6: Verify (collection identity + strict markers + speed)**

Run:
```bash
uv run pytest --collect-only -q -m "not last" 2>/dev/null | tail -1   # == 6395 collected, ZERO errors
time just test -q 2>&1 | tail -3                                       # <60s, all pass
uv run pytest tests/test_justfile_injection.py -q
```
Expected: **6395/6398** collected (baseline 6396 minus the deleted dead `test_unit_marker_works` — the ONLY test removal in this spec, authorized by plan review I3); `just test` green <60s; injection test PASS.

- [ ] **Step 7: Full-suite sanity**

Run: `uv run pytest -n auto --dist loadscope -m "not last" --no-cov -q 2>&1 | tail -2`
Expected: 0 failed (same set as check's first leg minus coverage).

- [ ] **Step 8: Commit**

```bash
git branch --show-current
git add tests/ pyproject.toml justfile tests/test_justfile_injection.py AGENTS.md goal-prompt.md command-to-give.md
# NOTE: `git add tests/` is scoped to tests/ only (sweep touched ~197 files); all other paths explicit.
git commit -m "chore: spec #92 T3 — retire unit marker (sweep 1296 annotations), merge test/test-all, -p no:randomly pin"
```

---

### Task 5: T4 — threshold single-source + just lint/type/test-ci + hook constructive subset

**Files:**
- Modify: `justfile` (check recipe split; :61 cov flag; :63 last-leg timeout)
- Modify: `tools/pre-push-check.sh` (call just recipes; drop hand-copied flags)
- Modify: `.github/workflows/nightly.yml:43`
- Test: `tests/unit/test_hook_subset.py` (new)

**Interfaces:**
- Consumes: Task 4's merged test recipe shape
- Produces: `just lint` (28 lint tools + ruff check + ruff format --check), `just type` (mypy + basedpyright + shellcheck), `just test-ci` (two pytest legs + module-coverage); check = lockfile + `just lint` + `just type` + codegen face inline + `just test-ci`

- [ ] **Step 1: Write failing hook-subset test**

`tests/unit/test_hook_subset.py`:

```python
"""spec #92 T4: pre-push hook is a constructive subset of just check faces.

Asserts: (1) hook invokes the just sub-recipes (not hand-copied tool lines),
(2) no copy of the retired --cov-fail-under flag anywhere in the hook,
(3) the documented exception faces (pip-audit, mkdocs, dead-code warn)
appear in the hook and are absent from justfile.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = (REPO / "tools" / "pre-push-check.sh").read_text(encoding="utf-8")
JUST = (REPO / "justfile").read_text(encoding="utf-8")


def test_hook_calls_just_recipes() -> None:
    import re

    for recipe in ("lint", "type", "test-ci"):
        assert re.search(rf"^\s*just {recipe}\s*$", HOOK, re.M), (
            f"hook missing constructive call line: just {recipe}"
        )


def test_hook_has_no_copied_threshold_flag() -> None:
    assert "--cov-fail-under" not in HOOK


def test_exception_faces_are_hook_only() -> None:
    # "mkdocs build --strict" (not bare "mkdocs" — justfile's docs: serve
    # recipe legitimately contains that word)
    for face in ("pip-audit", "mkdocs build --strict", "dead code check"):
        assert face in HOOK
        assert face not in JUST, f"{face} leaked into justfile"
    # pip-audit/mkdocs/dead-code are hook(+CI security.yml)-only by design (spec exception table)


def test_justfile_has_sub_recipes() -> None:
    for recipe in ("^lint:", "^type:", "^test-ci:"):
        import re

        assert re.search(recipe, JUST, re.M), f"justfile missing recipe {recipe!r}"
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/unit/test_hook_subset.py -q`
Expected: FAIL (recipes don't exist; hook still hand-copies).

- [ ] **Step 3: Split justfile recipes**

Extract from `check:` into three recipes (copy the exact lines; check then references them):

```just
# Lint face: 28 lint tools + ruff (spec #92 T4)
# NOTE: spec #93 will later add --strict to lint_threshold_reconciliation here (batch-A re-anchor hook).
lint:
    uv run python tools/lint_status_strings.py
    <...the REMAINING 26 `uv run python tools/` lines + `just lint-contracts`, copied verbatim from the pre-split check recipe...>
    uv run ruff check .
    uv run ruff format --check .

# Type face (spec #92 T4)
type:
    uv run mypy src/shenbi/
    uv run basedpyright
    uv run shellcheck run_pipeline.sh tools/pre-push-check.sh tests/round-exec.sh tests/lock-calibration-hash.sh tests/test-gates.sh

# CI-shaped test face: two pytest legs + module coverage (spec #92 T4)
test-ci:
    uv run pytest -n auto --dist loadscope -m "not last" --hypothesis-profile=ci --timeout=120 --cov=shenbi --cov-branch --cov-report=json:coverage.json --cov-report=xml:tests/coverage/coverage.xml --cov-report=term-missing
    uv run python tools/check_module_coverage.py coverage.json
    uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci --timeout=60
```

`check` becomes:

```just
check:
    uv lock --check
    just lint
    just type
    uv run shenbi-sync-contracts >/dev/null
    uv run python tools/generate_autocheck_docs.py
    uv run shenbi-generate-plugins
    git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ .codex-plugin/
    just test-ci
```

Notes: `--cov-fail-under=85` is GONE from justfile (pyproject `[tool.coverage.report] fail_under = 85` at :601 is the single source); last leg gains `--timeout=60` (alignment, kills a diff source — redundant with addopts but harmless); shellcheck list uses the Task-1 renamed script.

Lossless-split check (M5 guard): before splitting, save the old check body (`git show HEAD:justfile | sed -n '/^check:/,/^[a-z]/p' > /tmp/check-before.txt`); after splitting, extract the union (`just -n check` plus the three recipe bodies) and diff the sorted non-echo command lines — expect zero lines lost (only reordering + the two intended deltas: cov flag drop, timeout add).

- [ ] **Step 4: Rewrite hook to constructive subset**

`tools/pre-push-check.sh` — replace sections 2/3/4/5 with:

```bash
# 2-4. Lint + type faces: constructive (just recipes, spec #92 T4)
just lint
just type
# 5. Tests: constructive (just test-ci = both legs + module coverage)
just test-ci
```

Keep: section 1 (lockfile), 4b pip-audit (exception face), 4c mkdocs conditional (exception face), 6 dead-code warn (exception face). DELETE section 7 outright (serial `-m last` leg — `just test-ci` already contains it; keeping it would run the leg twice). KEEP sections 8/9 (codegen/autocheck idempotency) but re-comment them as "command-level copies of check's inline codegen face (spec #92 T4 — constructive ⊆ check by identical commands)". Delete the `uv sync --frozen --group dev` restore dance ONLY if no remaining hook section needs the docs group (mkdocs section does its own sync/restore internally — verify by reading the full mkdocs block before deleting anything).

- [ ] **Step 5: nightly.yml**

Delete `--cov-fail-under=85` from `.github/workflows/nightly.yml:43` (keep the rest of the invocation; pyproject governs).

- [ ] **Step 6: Verify**

Run:
```bash
uv run pytest tests/unit/test_hook_subset.py -q
grep -rn "cov-fail-under" justfile tools/pre-push-check.sh .github/workflows/ pyproject.toml; echo "rc=$?"
time just lint 2>&1 | tail -2
uv run pytest tests/test_justfile_injection.py -q
```
Expected: 4 PASS; grep rc=1 (zero); `just lint` <3min; injection PASS.

- [ ] **Step 7: Commit**

```bash
git branch --show-current
git add justfile tools/pre-push-check.sh .github/workflows/nightly.yml tests/unit/test_hook_subset.py tests/test_justfile_injection.py
git commit -m "feat: spec #92 T4 — cov threshold single-source, just lint/type/test-ci split, hook constructive subset"
```

---

### Task 6: T5 — sediment purge

**Files:**
- Delete: `tests/skill-behavior/`, `tests/skill-triggering/` (git rm -r)
- Modify: `pyproject.toml:566-574` (norecursedirs), `pyproject.toml:123-504` (per-file-ignores consolidation)
- Move: `tests/unit/contract/*.py` → `tests/unit/contracts/` (git mv, 2 test files; delete the subdir + its `__init__.py`)
- Modify: moved `test_loader_extractors.py:3` path comment

**Interfaces:**
- Consumes: nothing
- Produces: consolidated per-file-ignores (directory-level where rule-sets are identical)

- [ ] **Step 1: Delete the two archive dirs + phantom norecursedirs**

```bash
git rm -r tests/skill-behavior tests/skill-triggering
```
pyproject norecursedirs: delete the `"tests/dispatcher"`, `"tests/skill-behavior"`, `"tests/skill-triggering"` lines.

- [ ] **Step 2: Merge contract twin dir**

```bash
git mv tests/unit/contract/test_dict_reads.py tests/unit/contracts/test_dict_reads.py
git mv tests/unit/contract/test_loader_extractors.py tests/unit/contracts/test_loader_extractors.py
git rm tests/unit/contract/__init__.py
```
Fix `test_loader_extractors.py:3` header comment (references `tests/unit/contract/test_dict_reads.py` → new path). Check `tests/unit/contracts/__init__.py` exists (create if missing — match sibling package convention; grep first).

- [ ] **Step 3: Analyze per-file-ignores for consolidation**

```bash
uv run python - << 'EOF'
import tomllib
from collections import defaultdict
from pathlib import Path
cfg = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
pfi = cfg["tool"]["ruff"]["lint"]["per-file-ignores"]
groups = defaultdict(list)
for k, v in pfi.items():
    groups[tuple(v)].append(k)
for rules, keys in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    if len(keys) > 1:
        print(f"{len(keys)} entries share {list(rules)}: {keys[:6]}{'...' if len(keys)>6 else ''}")
EOF
```

Consolidate: entries whose rule-sets are IDENTICAL and whose globs share a directory prefix become one directory glob. Entries with unique rules stay individual lines. Apply by hand with the analysis output as the guide; keep every comment that documents a specific entry (move it under the consolidated line when it covers the group, duplicate when it covers one file).

- [ ] **Step 4: Verify**

Run:
```bash
uv run ruff check . && uv run ruff format --check . ; echo rc=$?
uv run pytest tests/unit/contracts/ -q
uv run pytest --collect-only -q 2>/dev/null | tail -1
```
Expected: ruff clean (consolidation lost no exemption); contracts tests PASS; collection unchanged (6,399 total).

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add tests/skill-behavior tests/skill-triggering tests/unit/contract tests/unit/contracts pyproject.toml
git commit -m "chore: spec #92 T5 — purge sediment dirs, phantom norecursedirs, merge contract twin, consolidate per-file-ignores"
```

---

### Task 7: T6 — dispatch payload constructor + first-5 conversion

**Files:**
- Create: `tests/support/dispatch_payload.py`
- Modify (first-5 by combined score, tests/unit scope): `tests/unit/pipeline/test_scene_splitter.py` (10 `===` blocks), `tests/unit/gates/test_g4_decisions.py` (9 dispatch dicts), `tests/unit/tools/test_observe_report.py` (7), `tests/unit/gates/g4/test_g4_ss_facts.py` (7), `tests/unit/gates/g4/test_chapter_revision.py` (6)

**Interfaces:**
- Consumes: nothing
- Produces: `file_block(path: str, body: str) -> str` (renders `=== <path> ===\n<body>` block) and `payload(skill: str, files: dict[str, str], **extra) -> dict` (hand-written dispatch dict constructor)

- [ ] **Step 1: Create the constructor module**

`tests/support/dispatch_payload.py`:

```python
"""Dispatch payload constructors for tests (spec #92 T6).

Replaces hand-written ``=== path ===`` blocks and dispatch dicts. First
consumers: the five highest-frequency files (see spec); adopt gradually
elsewhere — do NOT mass-migrate.
"""

from __future__ import annotations
from typing import Any


def file_block(path: str, body: str) -> str:
    """Render one ``=== <path> ===`` file block as skills emit them."""
    return f"=== {path} ===\n{body}"


def payload(skill: str, files: dict[str, str], **extra: Any) -> dict[str, Any]:
    """Build a dispatch payload dict (``skill`` + file blocks + extras)."""
    p: dict[str, Any] = {"skill": skill, **extra}
    p.update(files)
    return p
```

(Read 2-3 real `===` blocks in `tests/unit/pipeline/test_scene_splitter.py` first and match the EXACT separator form — `===`, count, trailing newline — byte-for-byte; adjust `file_block` before converting.)

- [ ] **Step 2: Convert the five files**

In each: replace literal `=== ... ===\n...` strings with `file_block(...)` calls and literal `{"skill": "shenbi-...", ...}` dicts with `payload(...)`. Import: `from tests.support.dispatch_payload import file_block, payload`. Convert only mechanical literals; leave assertions untouched.

- [ ] **Step 3: Verify**

Run: `uv run pytest tests/unit/pipeline/test_scene_splitter.py tests/unit/gates/test_g4_decisions.py tests/unit/tools/test_observe_report.py tests/unit/gates/g4/test_g4_ss_facts.py tests/unit/gates/g4/test_chapter_revision.py -q`
Expected: all PASS (byte-identical rendering proven by existing assertions).

- [ ] **Step 4: Commit**

```bash
git branch --show-current
git add tests/support/dispatch_payload.py tests/unit/pipeline/test_scene_splitter.py tests/unit/gates/test_g4_decisions.py tests/unit/tools/test_observe_report.py tests/unit/gates/g4/test_g4_ss_facts.py tests/unit/gates/g4/test_chapter_revision.py
git commit -m "test: spec #92 T6 — dispatch_payload constructors + first-5 file conversion"
```

---

### Task 8: Final verification battery (spec §2 acceptance 1-5)

**Files:** none (verification only; fixes if any surface)

- [ ] **Step 1: Acceptance 1** — `git grep -n "_tool_hashes" -- src tools tests justfile goal-prompt.md command-to-give.md ':!tests/fixtures'` rc=1; `git grep -n "lock-tool-hashes" -- ...` rc=1; `uv run pytest tests/unit/gates/test_g0_calibration_hash.py -q` PASS; rehearsal diff=0 (repeat Task 1 Step 9).
- [ ] **Step 2: Acceptance 2** — `uv run pytest tests/unit/test_paths_repo_root.py -q` PASS; loader-convergence grep (Task 2 Step 7) zero.
- [ ] **Step 3: Acceptance 3** — `just test` collection == 6,395 not-last (6,396 baseline − 1 dead marker test, Task 4); <60s; `--strict-markers` collection zero errors (`uv run pytest --collect-only -q 2>&1 | grep -ci error` == 0); `grep -rn "cov-fail-under" justfile tools/pre-push-check.sh .github/workflows/ pyproject.toml` rc=1.
- [ ] **Step 4: Acceptance 4** — `uv run pytest tests/unit/test_hook_subset.py -q` PASS (exceptions annotated in-test).
- [ ] **Step 5: Acceptance 5** — `just check` exit 0; `time just lint` <3min.
- [ ] **Step 6: Record outputs** into `.superpowers/sdd/progress.md` 验收证据 section (full command + output per item).
- [ ] **Step 7: Commit progress** (working-state file, no repo commit needed — `.superpowers/` is gitignored).
