# Cluster 04: Testing Foundation

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F15–F18

## Problem Statement

The Shenbi framework has **43 test functions for 5,921 lines of framework
code** (`src/shenbi/` scope per [README Metric Definitions](README.md#metric-definitions-canonical))
— a test density of **0.0073 test functions per LOC**. Industry baseline
for Python frameworks is **0.05–0.15** (per [README Threshold Justification](README.md#threshold-justification)).
The current density is **~7–20× below baseline**.

(An earlier draft cited 7,474 LOC; that figure included skill Python
scripts not in `src/shenbi/`. The canonical `framework_loc` definition
excludes skills. See [README Metric Definitions](README.md#metric-definitions-canonical).)

### Evidence

#### F15: Test density critically low

```
validate-gate.py    : 4318 lines — 18 tests (all subprocess-based)
scoring.py          : 384 lines  — 0 tests
phase-runner.py     : 314 lines  — 0 tests
update-progress.py  : 324 lines  — 0 tests
summarize-round.py  : 182 lines  — 0 tests
dispatch-subagent.sh: 203 lines  — 0 tests
exceptions.py       : 153 lines  — 14 tests
logging.py          : 43 lines   — 4 tests

Total framework LOC: 5921 (excluding skills, fixtures, rounds)
Total tests: 43
Tests/LOC: 0.0073
```

5 of 8 framework modules have **zero direct tests**.

#### F16: Tests use subprocess, not direct imports

`tests/unit/test_gates_integrity.py` is the only file testing
`validate-gate.py`. It uses:

```python
def _run_vg(self, *args):
    result = subprocess.run(
        [os.environ.get("PYTHON", "python3"), str(VG)] + list(args),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode
```

Every test starts a Python subprocess, imports validate-gate.py from scratch,
runs it, captures stdout, parses JSON. This is **integration testing masquerading
as unit testing**:

- Each test takes 200-500ms instead of <1ms
- Cannot test internal functions directly (e.g., `jload`, `yload`, `_normalize_file_paths`)
- Cannot mock filesystem operations
- Cannot test edge cases without setting up full filesystem fixtures
- No coverage of internal logic — only black-box behavior

Industry standard: subprocess testing for CLI smoke tests (~5% of test suite);
direct imports + pytest fixtures for everything else.

#### F17: `.hypothesis/` failure cases not committed

```
.hypothesis/.gitignore    # exists
.hypothesis/examples/     # not committed
.hypothesis/cache/        # not committed
```

Hypothesis can persist discovered counterexamples via
`.hypothesis/examples/`. Running `pytest` again replays them first, ensuring
regressions are caught even if the random seed differs. **Without committing
these, transient CI failures can't reproduce locally.**

Currently only `tests/conftest.py` and `tests/unit/test_pytest_framework.py`
use Hypothesis. So the examples database is tiny. But this will grow as
property-based testing expands.

#### F18: `pytest.ini_options.testpaths` implicitly excludes rounds

```toml
testpaths = ["tests/unit", "tests/integration", "tests/property", "tests/benchmark"]
```

`tests/rounds/`, `tests/fixtures/`, `tests/baselines/` are not in the list,
so pytest doesn't collect from them. This is **implicit** behavior — adding
a new test directory like `tests/e2e/` would silently not collect unless
added to `testpaths`.

Industry standard: explicit `--ignore` rules in pytest config, OR
`conftest.py` `collect_ignore` list.

## Root Cause Analysis

### Root cause 1: Tests were an afterthought

The framework evolved from shell scripts and Python helpers. Tests were
added when P-1 introduced pytest (PR-5, PR-6). Before P-1, the only tests
were `test_integrity.py` (now `test_gates_integrity.py`), which used
subprocess because it was originally a unittest that invoked the script.

**Fix**: P-1.E adds direct-import unit tests for every framework module
with **≥ 90% line AND ≥ 80% branch coverage** targets per
[README Threshold Justification](README.md#threshold-justification).

### Root cause 2: Subprocess testing was easy, real unit testing was hard

`subprocess.run([VG, ...])` works regardless of how validate-gate.py is
structured. Writing real unit tests requires understanding the module's
internal functions, designing fixtures, mocking filesystem operations.
The path of least resistance produced the current subprocess-heavy suite.

**Fix**: PR-19 (Cluster 01) modularizes validate-gate.py, making its
internals importable. PR-26 (Cluster 03) enforces test density. Combined,
these force real unit tests.

### Root cause 3: No property-based testing culture

Only `tests/unit/test_pytest_framework.py` uses Hypothesis. The framework
has many pure functions (`jload`, `yload`, `word_count_md`,
`count_transition_words`, `_normalize_file_paths`) that are perfect targets
for property-based testing, but no one wrote the tests.

**Fix**: Add a "Property Tests" subdirectory under each module's tests, with
at least one property test per pure function.

### Root cause 4: Hidden exclusions instead of explicit ones

`testpaths` inclusion is implicit exclusion. Industry standard is the
opposite: collect everything by default, explicitly ignore what shouldn't
collect. This catches mistakes like accidentally putting a `test_foo.py`
in `tests/fixtures/`.

**Fix**: Canonical PR-34 (this cluster) changes pytest config to use explicit
`--ignore` rules.

## Target State

After P-1.E Cluster 04 completes:

| Metric | Pre-P-1.E | Post-P-1.E | Industry baseline |
|--------|-----------|------------|-------------------|
| Total tests | 43 | **≥ 600** | per [README Threshold Justification](README.md#threshold-justification): ≥ 0.10 tests/LOC × 5921 LOC ≈ 593 tests |
| Test density (test functions / framework LOC) | 0.007 | **≥ 0.10** | 0.05 floor; 0.10 typical; 0.15+ rigorous |
| Direct-import unit tests | 5 | **≥ 500** | majority |
| Subprocess integration tests | 18 | ≤ 20 | small minority |
| Property-based tests | 1 | **≥ 60** | grow with pure functions; 1+ per pure function |
| `.hypothesis/examples/` committed | No | Yes | Yes |
| pytest collection explicit | Implicit via testpaths | Explicit via `--ignore` | Explicit |

## Components (PRs)

### PR-28: unit tests for scoring.py

`scoring.py` has 0 tests and is one of the most critical framework modules
(it computes final scores; bugs here invalidate entire rounds).

**Test files**:

```
tests/unit/
├── test_scoring.py             # NEW: ~60 tests (target ≥ 0.10 density × 384 LOC ≈ 40 floor, expanded for branch coverage)
└── test_scoring_property.py    # NEW: ~10 property-based tests
```

**Coverage target**: 90% line, 80% branch.

**Test categories**:

1. **Rubric parsing**: parse various rubric.md formats; verify dimension
   extraction
2. **Score normalization**: normalize scores per dimension; verify renormalization
3. **Test-type filtering**: `--test-type generative|bug-hunt|clean` selects
   correct dimensions
4. **Gate marker enforcement**: scoring rejects if markers missing; accepts
   when present
5. **REJECT behavior**: scores below threshold produce exit code 2 with
   structured error
6. **Subagent flag**: `--subagent` mode behaves differently
7. **Property tests**: random score combinations always produce scores in
   [0, 100]; renormalization is idempotent; round-trip parsing preserves
   dimensions

### PR-29: unit tests for phase_runner.py

`phase_runner.py` has 0 tests. It implements the T2/T3 phase state machine.

**Test files**:

```
tests/unit/
├── test_phase_runner.py             # NEW: ~50 tests (target ≥ 0.10 density × 314 LOC ≈ 32 floor, expanded for branch coverage)
└── test_phase_runner_property.py    # NEW: ~8 property tests
```

**Test categories**:

1. **State machine transitions**: valid transitions succeed; invalid ones
   rejected with `GateError`
2. **Pre-skill / post-skill / finalize markers**: correct sequence enforced
3. **Phase close**: G7.16 logic; incomplete phase detection
4. **Property tests**: state machine is acyclic; every reachable state has
   a valid next transition (unless terminal)

### PR-30: unit tests for update_progress.py

`update_progress.py` has 0 tests.

**Test files**:

```
tests/unit/test_update_progress.py    # NEW: ~50 tests (target ≥ 0.10 density × 324 LOC ≈ 32 floor, expanded for branch coverage)
```

**Test categories**:

1. **mark-done**: writes correct progress.json structure
2. **mark-failed**: error states recorded correctly
3. **Concurrent writes**: file locking behavior
4. **Idempotency**: marking the same skill/test_type twice doesn't duplicate

### PR-31: unit tests for summarize_round.py

`summarize_round.py` has 0 tests.

**Test files**:

```
tests/unit/test_summarize_round.py    # NEW: ~40 tests (target ≥ 0.10 density × 182 LOC ≈ 18 floor, expanded for branch coverage)
```

**Test categories**:

1. **Aggregation**: correct mean/median/p90 computation across skill scores
2. **G7 close validation**: detects incomplete phases
3. **Report generation**: markdown output format
4. **Error recovery**: handles partial round data

### PR-32: real unit tests for gates (replace subprocess tests)

After PR-19 modularizes validate-gate.py, write direct-import unit tests:

**Test files**:

```
tests/unit/gates/
├── test_shared.py             # NEW: jload, yload, passed, fail, write_gate_marker
├── test_g0.py                 # NEW: G0 + G0.x sub-checks
├── test_g1.py
├── test_g2.py
├── test_g3.py
├── test_g4/
│   ├── test_generic.py        # g4_generic_generative / bughunt / clean
│   ├── test_worldbuilding.py
│   ├── test_character_design.py
│   └── ... (one per skill with a G4 checker)
├── test_g5.py
├── test_g6.py
└── test_g7.py
```

**Approach**: Each test imports the module directly:

```python
from shenbi.gates.shared import jload, yload
from shenbi.gates.g4.worldbuilding import g4_worldbuilding

def test_g4_worldbuilding_valid_output(tmp_project_dir):
    # Set up minimal valid worldbuilding output
    ...
    result = g4_worldbuilding([str(world_bible_path)], rd=tmp_project_dir)
    assert result["status"] == "PASS"
```

**Migration plan for `test_gates_integrity.py`**: The existing 18 subprocess
tests are valuable as integration tests. Move them to
`tests/integration/test_gate_cli.py` and keep them. The new direct-import
tests in `tests/unit/gates/` replace them as the primary test surface.

**Coverage target**: 90% line, 80% branch per gate module (matches canonical thresholds).

### PR-33: hypothesis failure case persistence

**Files**:

```
.hypothesis/
├── .gitignore                 # MODIFY: ignore only caches, not examples
└── examples/                  # COMMITTED: discovered counterexamples
```

**`.hypothesis/.gitignore` (new content)**:

```
# Hypothesis caches are machine-specific
cache/

# Examples are committed — they capture discovered counterexamples
# and replay them on every run, ensuring regression detection.
!examples/
```

**Acceptance**:

- [ ] `.hypothesis/examples/` exists with at least 1 committed counterexample
- [ ] `.hypothesis/.gitignore` configured to track examples
- [ ] CI verifies that committed examples still reproduce (no stale entries)

### PR-34: explicit pytest collection rules

**`pyproject.toml` changes**:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]   # was: specific subdirs — collect everything under tests/
norecursedirs = [
    "tests/rounds",
    "tests/fixtures",
    "tests/baselines",
    "tests/coverage",
]
addopts = [
    ...
]
```

**Acceptance**:

- [ ] `testpaths = ["tests"]` (single root)
- [ ] `norecursedirs` lists every excluded subdirectory explicitly
- [ ] `pytest --collect-only` shows expected count
- [ ] Adding a new `test_xxx.py` anywhere under `tests/` (not in norecursedirs)
      automatically collects

## Cross-cluster Dependencies

- **PR-32 depends on PR-18**: requires modularized gates.
- **PR-28, PR-29, PR-30, PR-31 depend on PR-18**: requires `src/shenbi/`
  layout for direct imports.
- **PR-33 is independent**.
- **PR-34 is independent**.

## Risks

| Risk | Mitigation |
|------|------------|
| Writing 200+ tests takes longer than expected | Parallelize: assign one module per contributor/agent session |
| Direct-import tests reveal hidden coupling (e.g., scoring.py imports from validate-gate.py via sys.path hacks) | Refactor as discovered; PR-18 should have decoupled |
| Property-based tests find counterexamples that reveal real bugs | This is the goal — fix bugs as found, commit the counterexample |
| Test suite runtime exceeds 30s | Use `-n auto` (already configured); mark long tests with `@pytest.mark.slow` |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Add `pytest-bdd` for BDD-style scoring tests? | **No.** | pytest-bdd adds Gherkin ceremony (.feature files, step definitions) without proportionate value for a Python-internal framework. The audience (Shenbi contributors) writes Python; BDD is for cross-stakeholder communication. Standard pytest functions with descriptive names achieve the same clarity. |
| 2 | Run actual skill dispatches in `tests/integration/`? | **No — separate `tests/e2e/` dir, `@pytest.mark.e2e`, skipped in CI.** | E2E tests require API keys, network, and 5-30 min per skill. Mixing them with integration tests makes the suite non-deterministic. `tests/e2e/` with explicit marker lets devs opt-in via `pytest -m e2e`. CI runs `pytest -m "not e2e"` by default. |
| 3 | Use `pytest-randomly` for order-dependence detection? | **Yes — add to dev deps, fixed seed in CI for reproducibility.** | Catches hidden test-order dependencies (common when tests share module state). CI uses `--randomly-seed=42` for reproducibility; local dev gets random seeds. Standard practice in mature Python projects (pytest-dev, FastAPI). |
