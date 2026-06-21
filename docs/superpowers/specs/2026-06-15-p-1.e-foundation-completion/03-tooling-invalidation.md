# Cluster 03: Tooling Configuration Invalidation

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F10–F14

## Problem Statement

P-1 added four quality tools (structlog, mypy strict, basedpyright strict,
coverage threshold). Audit found that **all four are configured but
ineffective**: each has a systematic escape hatch that lets non-compliant
code pass.

### Evidence

#### F10: structlog integration is decorative

```
tests/logging.py                    : 43 lines (config only)
structlog uses in framework code    : 4
print() calls in tests/*.py         : 92
validate-gate.py                    : 30 print, 0 structlog
scoring.py                          : 23 print, 0 structlog
phase-runner.py                     : 20 print
summarize-round.py                  : 7 print
update-progress.py                  : 12 print
```

PR-9 promised: *"替换所有 print() in framework code with structlog calls"*.
Reality: only `tests/logging.py` and a few tests reference structlog. All
production code uses `print()`.

#### F11: mypy `strict = true` is overridden into nothing

`pyproject.toml:118-145`:

```toml
[tool.mypy]
strict = true
warn_return_any = true
... (10+ strict flags)

# P-1.A temporary overrides: legacy untyped code in tests/*.py
# PR-12 (P-1.E) will add type hints and remove these overrides.
[[tool.mypy.overrides]]
module = [
    "tests.validate-gate",          # 4318 lines — exempt
    "tests.scoring",                # 384 lines — exempt
    "tests.phase-runner",           # 314 lines — exempt
    "tests.summarize-round",        # 182 lines — exempt
    "tests.update-progress",        # 324 lines — exempt
    "tests.unit.test_gates_integrity",
]
ignore_errors = true                # <- all errors suppressed
```

**5 of 7 framework modules are exempt from type checking.** Plus
`tests.unit.test_gates_integrity`. Effective coverage: `exceptions.py`,
`logging.py`, and 4 stub modules. The "strict" claim is a façade.

#### F12: basedpyright `strict` mode excludes the same files

`pyproject.toml:157-170`:

```toml
[tool.basedpyright]
include = ["tests"]
exclude = [
    ...
    "tests/validate-gate.py",
    "tests/scoring.py",
    "tests/phase-runner.py",
    "tests/summarize-round.py",
    "tests/update-progress.py",
    "tests/unit/test_gates_integrity.py",
]
typeCheckingMode = "strict"
```

Same 6 files exempt. Same façade.

#### F13: coverage threshold = 0.5%

`pyproject.toml:209`:

```toml
[tool.coverage.report]
# Staged ramp-up. Current line coverage ~10% ...
# Target: 30% after P-1.E, 60% after P-2, 90% after P-3.
fail_under = 8
```

Plus `tests/unit/test_coverage_thresholds.py:25`:

```python
BRANCH_THRESHOLD_PCT = 0.5
```

Two thresholds, both near zero. Branch coverage 0.5% means a single
`if/else` passing tests satisfies the gate. **The threshold is decorative.**

The comment claims ramp-up targets but **the threshold itself was never
bumped**. Without enforcement, the ramp-up is aspirational.

#### F14: `skills/*.py` excluded from all tooling

`pyproject.toml:70-76`:

```toml
[tool.ruff]
extend-exclude = [
    "tests/rounds/archived",
    "tests/rounds/round-[0-9][0-9][0-9]-*",
    # Skill-level Python utility scripts are governed by skill conventions, not
    # the framework's tooling contract. Refactoring them is out of P-1 scope.
    "skills",
]
```

But `skills/shenbi-chapter-pattern/compute_pattern.py` (176 lines) and
`skills/shenbi-style-learning/compute_stats.py` (392 lines) are **real
framework Python code** that ships in the repo. They compute chapter
patterns and style statistics — substantive logic.

**568 lines of production code are silently exempt from ruff, mypy,
basedpyright, and pytest.** The comment justifies this as "skill
conventions", but these aren't skills — they're Python helpers bundled
inside skill directories.

## Root Cause Analysis

### Root cause 1: Tools were added before the code was ready

P-1.B added ruff/mypy/basedpyright configs. P-1.C added structlog +
exceptions. P-1.D was supposed to integrate these tools into the legacy
code (PR-9 said "替换所有 print", PR-12 was supposed to remove the mypy
overrides). But P-1.D delivered stubs (Cluster 01). So the configs exist,
the integration didn't happen, and the configs have escape hatches to
avoid failing.

**Fix**: Remove all escape hatches in P-1.E. Either the code passes
strict, or it's not in the codebase.

### Root cause 2: "Staged ramp-up" became "permanently low"

The coverage threshold comment says "staged ramp-up. Target: 30% after
P-1.E, 60% after P-2, 90% after P-3." But P-1.E never came. So the
threshold stayed at 0.5% (test) / 8% (pyproject) forever.

**Fix**: P-1.E sets thresholds at canonical values (branch 80%, line 90%)
per [README Threshold Justification](README.md#threshold-justification).
No weekly ramp — Cluster 04 PR-28 ~ PR-32 are scoped to deliver ~600 tests
achieving these thresholds directly. The "30% then ramp" framing from earlier
drafts was a cost compromise inconsistent with the user's directive; it has
been removed.

### Root cause 3: `ignore_errors` was used instead of `untyped_def_behavior`

mypy offers graduated strictness levels for partial migrations:
- `disallow_untyped_defs = false` (allows untyped functions)
- `disallow_incomplete_defs = false` (allows partially typed)
- `ignore_errors = true` (suppresses everything)

P-1.A used `ignore_errors = true` — the most aggressive suppression. A
more honest config would have been per-file `disallow_untyped_defs = false`,
which still catches type errors in already-typed code.

**Fix**: All overrides use the minimum-necessary suppression. Document
each suppression's exit criteria.

### Root cause 4: `extend-exclude = ["skills"]` was over-broad

The intent was "don't lint the prose content of SKILL.md files". But
`extend-exclude` operates on directories, not file types. Excluding
`skills/` also excludes any `.py` files inside skill directories.

**Fix**: Use `[tool.ruff.lint.per-file-ignores]` with explicit patterns
to exclude only `*.md` files in skills, not all files.

## Target State

After P-1.E Cluster 03 completes:

| Tool | Pre-P-1.E | Post-P-1.E |
|------|-----------|------------|
| structlog | 4 calls / 92 print | 0 print in framework code |
| mypy strict | 6 modules exempt | 0 modules exempt |
| basedpyright strict | 6 modules excluded | 0 modules excluded |
| Coverage (branch) | 0.5% threshold | **80%** threshold immediately post-P-1.E merge (SonarSource new-code standard) |
| Coverage (line) | 8% threshold | **90%** threshold immediately post-P-1.E merge (industry rigorous-tested standard) |
| Test density | 0.007 tests/LOC (43 tests / 5921 LOC) | **0.10 tests/LOC** (≥ 1 test function per 10 framework LOC; ~600 tests delivered by Cluster 04 expanded scope) |
| ruff scope | skills/ excluded | only `skills/**/*.md` excluded |
| mypy scope | skills/ excluded | only `skills/**/*.md` excluded |
| skills Python scripts | untyped, untested | typed, tested, linted |

**All thresholds above are the canonical values per [README Threshold Justification](README.md#threshold-justification). Cluster files must not introduce conflicting numbers. No weekly ramp — P-1.E delivers final thresholds directly.**

## Components (PRs)

### PR-24: structlog true integration

**Approach**: Mechanical replacement of `print()` calls with structured
logging. Each `print()` is categorized:

| print() pattern | Replacement |
|-----------------|-------------|
| `print("=== G1: Input Validation ===")` (section header) | `log.info("gate_section", gate="G1", phase="input_validation")` |
| `print(f"G1 FAILED: {msg}")` (error) | `log.error("gate_failed", gate="G1", reason=msg)` |
| `print(f"G1 PASSED")` (success) | `log.info("gate_passed", gate="G1")` |
| `print(f"Agent ID: {id}")` (info) | `log.info("dispatch_start", agent_id=id)` |
| `print(json.dumps(result))` (data to stdout) | **KEEP** — this is stdout-as-data, not logging. Move to explicit `_emit_data()` function with comment. |

**Rule**: any `print()` that goes to stdout AND is parsed by downstream
consumers (e.g., dispatcher's JSON parsing) is **data emission**, not
logging. These stay as `print()` or move to a dedicated `emit_json()`
function. They are explicitly marked with a comment.

Any `print()` to stderr or for human-readable status messages becomes
`log.info/error/warning`.

**Files modified**:

- `src/shenbi/gates/cli.py` — `configure_logging()` called at start of `main()`
- `src/shenbi/gates/{g0..g7}.py` — each gate function logs entry, exit, failures
- `src/shenbi/gates/shared.py` — `passed()` and `fail()` emit logs (in addition
  to returning JSON; logs go to stderr, JSON to stdout)
- `src/shenbi/dispatcher/executor.py` — same
- `src/shenbi/scoring.py` — same
- `src/shenbi/phase_runner.py` — same
- `src/shenbi/summarize_round.py` — same
- `src/shenbi/update_progress.py` — same

**Acceptance**:

- [ ] `grep -rn "print(" src/shenbi/ --include='*.py' | grep -v "emit_data\|emit_json"` returns 0 matches
- [ ] `grep -rn "structlog\|get_logger" src/shenbi/ --include='*.py'` returns ≥ 50 matches
- [ ] Each framework CLI tool's `main()` calls `configure_logging()` first
- [ ] `SHENBI_LOG_FORMAT=json uv run shenbi-validate G0 ...` produces JSON log lines on stderr
- [ ] Tests in `tests/unit/test_logging.py` cover at least 5 framework module's logging output

### PR-25: mypy / basedpyright de-ignore

**Approach**: Remove all `ignore_errors = true` and `exclude` overrides.
Add type annotations to legacy code module-by-module. Run mypy and
basedpyright after each module; commit when green.

**Order of de-ignoring** (easiest first):

1. `tests/scoring.py` → `src/shenbi/scoring.py` (PR-18 must merge first)
2. `tests/summarize-round.py` → `src/shenbi/summarize_round.py`
3. `tests/update-progress.py` → `src/shenbi/update_progress.py`
4. `tests/phase-runner.py` → `src/shenbi/phase_runner.py`
5. `tests/validate-gate.py` → `src/shenbi/gates/*` (after PR-18)
6. `tests/unit/test_gates_integrity.py` (last — tests can have looser typing)

For each module:

1. Add type annotations to all function signatures.
2. Run `uv run mypy src/shenbi/<module>.py` — fix errors.
3. Run `uv run basedpyright src/shenbi/<module>.py` — fix errors.
4. Remove the override line from `pyproject.toml`.
5. Commit.

**Acceptance**:

- [ ] Zero `ignore_errors` lines in `pyproject.toml` mypy section
- [ ] Zero `exclude` lines in `pyproject.toml` basedpyright section (beyond `__pycache__`, archived rounds)
- [ ] `uv run mypy src/shenbi/` exits 0
- [ ] `uv run basedpyright` exits 0
- [ ] All public functions in `src/shenbi/` have complete type annotations

### PR-26: coverage threshold enforcement + test density enforcement

**Approach**: Set thresholds at canonical values (no ramp), enforce via CI.
Cluster 04 PR-28 ~ PR-32 deliver the test volume needed to meet these targets.

**Step 1**: After PR-25, measure actual coverage to confirm Cluster 04 scope:

```bash
uv run pytest --cov=src/shenbi --cov-report=term-missing --cov-branch
# Expected starting point: line ~10%, branch ~1% (per current pyproject comment)
# After Cluster 04 PR-28 ~ PR-32 (expanded scope): line ~90%, branch ~80%
```

**Step 2**: Set thresholds at canonical values (no ramp):

| Threshold | Value (post-P-1.E) | Where configured |
|-----------|-------------------|------------------|
| Branch coverage floor | **80%** | `tests/unit/test_coverage_thresholds.py:BRANCH_THRESHOLD_PCT = 80` |
| Line coverage floor | **90%** | `pyproject.toml:[tool.coverage.report].fail_under = 90` |

These are the targets Cluster 04 PR-28 ~ PR-32 must deliver. If post-PR-32
measurement falls short, **add tests to Cluster 04 scope** rather than lowering
thresholds.

**Step 3**: Test density enforcement using the canonical metric definition
(see README Threshold Justification "Metric definitions"):

```python
# tests/unit/test_test_density.py
"""Enforce test density floor per README Threshold Justification.

Metric: test_function_count / framework_loc
Target: ≥ 0.10 (i.e., ≥ 1 test function per 10 LOC of framework code)
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_DIR = REPO_ROOT / "src" / "shenbi"
TEST_DIRS = [REPO_ROOT / "tests" / sub for sub in ("unit", "integration", "property", "benchmark")]

def count_framework_loc() -> int:
    """Count non-blank, non-comment Python LOC in src/shenbi/."""
    total = 0
    for py_file in FRAMEWORK_DIR.rglob("*.py"):
        for line in py_file.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                total += 1
    return total

def count_test_functions() -> int:
    """Count `def test_*` functions across all test directories."""
    total = 0
    for test_dir in TEST_DIRS:
        if not test_dir.exists():
            continue
        for py_file in test_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    total += 1
    return total

def test_density_meets_minimum():
    framework_loc = count_framework_loc()
    test_count = count_test_functions()
    density = test_count / framework_loc if framework_loc else 0
    assert density >= 0.10, (
        f"Test density {density:.4f} below 0.10 floor "
        f"({test_count} tests / {framework_loc} framework LOC). "
        f"Add ~{int(0.10 * framework_loc - test_count)} more tests."
    )
```

**Files modified**:

- `pyproject.toml`: `fail_under = 90` (was 8)
- `tests/unit/test_coverage_thresholds.py`: `BRANCH_THRESHOLD_PCT = 80` (was 0.5)
- `tests/unit/test_test_density.py`: NEW (above implementation)

**Note**: The earlier "coverage-bump.yml" weekly ramp workflow has been removed
from this spec. Per the user's "no cost compromise" directive, P-1.E delivers
the final thresholds directly via expanded Cluster 04 test scope. If post-merge
measurement reveals a gap, the gap is fixed by adding tests in a follow-up PR,
not by lowering thresholds via automation.

**Acceptance**:

- [ ] `pyproject.toml` `fail_under == 90` (exactly)
- [ ] `BRANCH_THRESHOLD_PCT == 80` in `test_coverage_thresholds.py`
- [ ] `test_test_density.py` exists, uses the canonical metric definition (≥ 0.10), passes
- [ ] Coverage badge in README points to actual coverage
- [ ] If post-PR-32 measurement falls below these targets, **add tests in Cluster 04 PR-32** to meet them (do NOT lower thresholds, do NOT introduce a ramp)

### PR-27: skill Python scripts lint/type scope

**Approach**: Move skill Python scripts under tooling scope. Two options:

**Option A** (preferred): Move skill Python scripts to `src/shenbi/skill_utils/<skill>/`.

```
src/shenbi/skill_utils/
├── __init__.py
├── chapter_pattern/
│   └── compute_pattern.py    # MOVED from skills/shenbi-chapter-pattern/
└── style_learning/
    └── compute_stats.py      # MOVED from skills/shenbi-style-learning/
```

Skill SKILL.md files reference the script path:
```markdown
# skills/shenbi-chapter-pattern/SKILL.md
...
Run: `python -m shenbi.skill_utils.chapter_pattern.compute_pattern ...`
```

**Option B** (fallback): Keep scripts in skill directories but remove
`extend-exclude = ["skills"]` and use per-file ignore patterns:

```toml
[tool.ruff]
# Don't exclude skills/ entirely — only the markdown files
extend-exclude = [
    "tests/rounds/archived",
    "tests/rounds/round-[0-9][0-9][0-9]-*",
]

[tool.ruff.lint.per-file-ignores]
# Skill markdown files aren't Python — ruff shouldn't try to lint them
"skills/**/*.md" = ["*"]
```

**Recommendation**: Option A. Skill Python scripts are framework code
distributed with the wheel; they should be in `src/shenbi/`. The skill
directory contains prose and data references; code lives with code.

**Files modified**:

- Move `skills/shenbi-chapter-pattern/compute_pattern.py` → `src/shenbi/skill_utils/chapter_pattern/compute_pattern.py`
- Move `skills/shenbi-style-learning/compute_stats.py` → `src/shenbi/skill_utils/style_learning/compute_stats.py`
- Update SKILL.md files to reference new paths
- Add `__init__.py` files
- Add type annotations to both scripts (in scope of PR-25)
- Add unit tests for both scripts

**Acceptance**:

- [ ] Both scripts have type annotations and pass mypy strict
- [ ] Both scripts have unit tests with ≥ 90% line AND ≥ 80% branch coverage (per canonical thresholds)
- [ ] `extend-exclude` in `pyproject.toml` no longer contains `"skills"`
- [ ] `[tool.ruff.lint.per-file-ignores]` has explicit `skills/**/*.md` ignore
- [ ] Skill SKILL.md files updated to reference new Python module paths

## Cross-cluster Dependencies

- **PR-24 depends on PR-18 + PR-19 + PR-20**: structlog integration requires
  modular gates + dispatcher in their final src/ locations.
- **PR-25 depends on PR-18 + PR-19**: type annotation requires final file
  locations.
- **PR-26 depends on PR-25**: thresholds can only be enforced after baseline
  measurement on the typed codebase confirms starting point.
- **PR-27 depends on PR-18**: skill_utils/ lives under src/shenbi/.

## Risks

| Risk | Mitigation |
|------|------------|
| Structlog integration surfaces hidden bugs (e.g., a `print()` was actually being parsed by downstream) | Categorize each print() before replacing; keep data-emitting prints |
| Removing mypy overrides reveals hundreds of type errors | Triage by file; fix incrementally; document any intentional `# type: ignore` with reason |
| Coverage threshold (80%/90%) requires substantial test additions; if PR-32 cannot deliver enough tests in one PR, split into PR-32a / PR-32b | Track per-module coverage in CI artifacts; if a module falls short, the PR adds more tests for that module (no threshold lowering) |
| Moving skill scripts breaks agent prompts that hardcode the path | Update SKILL.md in same PR; document in CHANGELOG |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | structlog + OpenTelemetry integration? | **Defer OTLP exporter to P3; P-1.E defines metrics schema only.** | structlog is the local sink (JSON to stderr). OTLP exporter requires running a collector (Jaeger/Tempo/Honeycomb), which is post-MVP infrastructure. Defining the metrics schema now (Pydantic models in `src/shenbi/observability/metrics.py`) locks the contract without operational cost. |
| 2 | Different coverage thresholds for `src/shenbi/` vs `tests/`? | **Enforce on `src/shenbi/` only.** | Test code is exercised by running; measuring test coverage of tests is meta and not actionable. `[tool.coverage.run].source = ["src/shenbi"]` already excludes tests. |
| 3 | Skill Python scripts standalone (`python compute_pattern.py`)? | **Yes — provide `__main__.py` per skill_utils subdir.** | Skill authors may want to iterate on a script without `uv sync` overhead. `python -m shenbi.skill_utils.chapter_pattern` works after the module is on `sys.path` (e.g., editable install via `uv sync`). For pure-standalone use, document a one-line `python -m` invocation in each skill's SKILL.md. |
