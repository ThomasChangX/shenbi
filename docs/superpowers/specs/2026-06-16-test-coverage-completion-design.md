# Test Coverage Completion Design

- Status: **accepted** (2026-06-16)
- Date: 2026-06-16
- Deciders: ThomasChangX
- Blocks: P0 (pipeline safety depends on tested gates)

## TL;DR

P-1.E's acceptance criteria require 80% branch coverage, 90% line coverage, and 0.10 test density on `src/shenbi/`. Current state: ~3% line coverage, 0.060 density, 380 tests. This spec delivers ~405 additional tests across 9 PRs in 3 phases: critical-path (pipeline safety), error-path (bug prevention), coverage-fill (hit spec numbers).

## Background

### How we got here

P-1.E Cluster 04 (PR-28 ~ PR-34) added tests for 4 modules: `scoring.py`, `phase_runner.py`, `update_progress.py`, `summarize_round.py`. These modules went from 0% to ~90% coverage. However, the gates (`src/shenbi/gates/`), dispatcher, plugins, and skill_utils remained minimally tested.

A coverage audit on 2026-06-16 found:

| Module group | Lines | Existing tests | Coverage |
|---|---|---|---|
| scoring + phase_runner + update_progress + summarize_round | ~1000 | ~200 | ~90% |
| gates/ (g0-g7 + shared + g4/* + helpers) | ~5000 | ~60 | ~3% |
| dispatcher/ | ~180 | ~6 | ~5% |
| plugins/ | ~130 | 0 | 0% |
| skill_utils/ | ~600 | 0 | 0% |
| **Total** | **~6232** | **~380** | **~3%** |

The `test_branch_coverage_meets_threshold` test is `@pytest.mark.xfail(strict=True)` with reason "Plan 4 PR-28~32 must raise branch coverage from current ~2% to 80%." `fail_under = 1` in `pyproject.toml` (set to current coverage to catch regressions without blocking merges).

### Why goal-prompt.md testing doesn't close this gap

The `goal-prompt.md` protocol runs integration-level T1/T2/T3 pipeline tests through CLI entry points. This exercises framework code functionally but doesn't produce `pytest --cov` measurable coverage. Even a full pipeline run with coverage instrumentation would hit only ~15-25% line coverage (happy-path branches only). The remaining branches — error handling, edge cases, alternative configurations — require dedicated unit tests.

## Goals

1. **Hit spec targets**: 80% branch, 90% line, 0.10 test density on `src/shenbi/`.
2. **Pipeline safety**: every gate function's happy-path tested so the goal-prompt.md pipeline can execute without hitting untested code.
3. **Bug prevention**: every error-handling branch tested to catch defensive-code regressions.
4. **Zero xfails**: remove the coverage and density xfail markers; enforce thresholds permanently.

## Non-Goals

1. **No integration test expansion**: the T1/T2/T3 pipeline tests (goal-prompt.md) are a separate concern. This spec covers unit tests only.
2. **No test framework changes**: pytest, hypothesis, coverage.py configs stay as-is. Only `fail_under` and xfail markers change.
3. **No gate logic changes**: tests pin current behavior. If tests reveal bugs, fix the bug in a separate PR, then update the test.
4. **No performance benchmarking**: test speed is monitored but not gated.

## Architecture

### Test file structure

```
tests/unit/gates/
├── conftest.py                  # Fixture factory (new)
├── test_g0.py                   # Expand existing (6→18 tests)
├── test_g0_purity.py            # New: G0.9/9c/9b purity checks
├── test_g1.py                   # Expand existing (3→8)
├── test_g2.py                   # Expand existing (9→14)
├── test_g3.py                   # Expand existing (4→9)
├── test_g5.py                   # Expand existing (11→16)
├── test_g6.py                   # Expand existing (6→14)
├── test_g6_checks.py            # New: G6.4/6.5/6.10 extracted helpers
├── test_g7.py                   # Expand existing (6→11)
├── test_g_dispatch.py           # Expand existing (6→8)
├── test_g_reconcile.py          # New
├── test_g_transition.py         # New
├── test_shared.py               # Expand existing (36→44)
├── g4/
│   ├── test_common.py           # Parametrized harness: 7 tests × 21 checkers = 147
│   ├── test_chapter_drafting.py # Bespoke: content uniqueness, scene concreteness
│   ├── test_worldbuilding.py    # Bespoke: story_bible structure
│   ├── test_foreshadowing_plant.py
│   ├── test_character_design.py
│   └── test_genre_config.py
tests/unit/
├── test_dispatcher_executor.py  # New
└── test_plugins_generate.py     # New
```

### Fixture factory pattern

`tests/unit/gates/conftest.py` provides a `make_project` fixture that builds parameterized project directory trees in `tmp_path`:

```python
@pytest.fixture
def make_project(tmp_path):
    """Factory: build a project directory tree for gate testing."""
    def _make(
        chapters: list[str] | None = None,
        novel_json: dict | None = None,
        genre_config: dict | None = None,
        pending_hooks: str | None = None,
        style_profile: str | None = None,
        volume_map: str | None = None,
        progress: dict | None = None,
        t1_reports: list[dict] | None = None,
    ) -> Path:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        if chapters:
            ch_dir = project_dir / "chapters"
            ch_dir.mkdir()
            for i, content in enumerate(chapters, 1):
                (ch_dir / f"chapter-{i:03d}.md").write_text(content, encoding="utf-8")
        if novel_json:
            (project_dir / "novel.json").write_text(json.dumps(novel_json))
        # ... other parameters
        return project_dir
    return _make
```

Each parameter is optional. Tests build exactly the project state they need. This avoids the boilerplate of every test creating its own directory tree, while maintaining full isolation (each test gets a fresh `tmp_path`).

### Parametrized G4 harness

One file (`g4/test_common.py`) tests the shared G4 checker pattern against all 21 checkers:

```python
ALL_G4_CHECKERS = [
    ("shenbi-worldbuilding", g4_worldbuilding),
    ("shenbi-character-design", g4_character_design),
    # ... 21 total
]

@pytest.mark.parametrize("skill_name,checker", ALL_G4_CHECKERS)
class TestG4Common:
    def test_empty_input(self, skill_name, checker): ...
    def test_missing_file(self, skill_name, checker, tmp_path): ...
    def test_valid_json_output(self, skill_name, checker): ...
    def test_malformed_utf8(self, skill_name, checker, tmp_path): ...
    def test_empty_file(self, skill_name, checker, tmp_path): ...
    def test_gate_id_in_output(self, skill_name, checker): ...
    def test_pass_includes_checks_list(self, skill_name, checker): ...
```

7 test functions × 21 checkers = 147 parametrized test cases from one file. The 5 bespoke test files add ~40 tests for complex checker-specific logic.

### Test invocation model

All tests use **direct import** (not subprocess), consistent with PR-32's pattern. Gates are called as Python functions: `gate_G0(seed_file=..., round_dir=...)`. Fast, debuggable, no subprocess overhead.

## Phase 1: Critical-Path Tests (PR-48 ~ PR-51)

**Goal**: Test the happy-path through every gate function + dispatcher + plugins. After Phase 1, the goal-prompt.md pipeline can execute T1→T2→T3 without hitting untested code paths.

### PR-48: Fixture factory + gate happy-path tests (~45 tests)

`conftest.py` with `make_project` factory, plus happy-path tests for every gate:

| Module | Tests | What's covered |
|---|---|---|
| `g0.py` + `g0_purity.py` | 12 | G0.1-G0.12 happy path: valid seed, skill dirs, fixtures, scenario purity |
| `g1.py` | 5 | Valid input files (JSON, YAML, markdown), `.bak` creation for in-place skills |
| `g2.py` | 5 | Valid output files, word count within range |
| `g3.py` | 5 | Prerequisites met, scores at threshold, agent isolation |
| `g5.py` | 5 | Phase data with prerequisites, handoff integrity |
| `g6.py` + `g6_checks.py` | 8 | Sufficient chapters, no continuity violations, valid pacing, hook density |
| `g7.py` | 5 | Valid summary, truth files OK, changelog writable |
| `g_dispatch.py` | 2 | Progress.json valid, queue ready |
| `g_reconcile.py` | 3 | All T1 reports present, scores consistent |
| `g_transition.py` | 3 | Phase transition with empty queue, no blockers |
| `shared.py` | 2 | `write_gate_marker` + `read_genre_config` happy path |

**Done criteria**: `just gate G0` through `G7` can run against a valid project without any gate function raising an untested-code-path exception.

### PR-49: G4 parametrized common harness (147 tests)

`g4/test_common.py`: 7 test functions × 21 checkers = 147 parametrized tests.

Tests the shared pattern every G4 checker follows:
1. Empty input → valid JSON with status
2. Missing file → FAIL with file_not_found
3. Empty file → FAIL or WARN (not crash)
4. Malformed UTF-8 → handled gracefully
5. Valid output → JSON parseable with `gate` field
6. PASS includes `checks` list
7. FAIL includes `must_fix` list

**Done criteria**: every G4 checker handles the 7 common input patterns without crashing.

### PR-50: Dispatcher + plugins (~13 tests)

| Module | Tests | What's covered |
|---|---|---|
| `dispatcher/executor.py` | 8 | `derive_input_files`, `derive_output_files`, dispatch flow, skill lookup |
| `plugins/generate.py` | 5 | `load_master`, `generate_all`, output matches committed manifests, JS escaping |

**Done criteria**: `shenbi-dispatch` and `shenbi-generate-plugins` are fully tested for happy-path operation.

### PR-51: Threshold bump

- `fail_under`: 1 → 30
- Branch coverage xfail reason updated to "Phase 2 will raise to 60"
- Verify full suite passes at new threshold

### Phase 1 totals

| Metric | Before | After Phase 1 |
|---|---|---|
| Test count | 380 | ~580 |
| Test density | 0.060 | ~0.093 |
| Line coverage (est.) | ~3% | ~35-40% |
| Pipeline safety | Untested gates | All gate happy paths covered |

## Phase 2: Error-Path Tests (PR-52 ~ PR-54)

**Goal**: Test every error-handling branch, edge case, and defensive code path. This is where hidden bugs live — the `except` blocks, the `if not exists` guards, the validation failures.

### PR-52: Gate error paths (~90 tests)

| Module | Tests | Error paths covered |
|---|---|---|
| `g0.py` + `g0_purity.py` | 15 | Missing seed, no target_words, missing skill dirs, skill-output not writable, missing fixtures, G0.9 non-fixture paths (FAIL), G0.9c project dirs (WARN), G0.9b SKILL.md leak (FAIL), stale mirror, <59 generative tests |
| `g1.py` | 6 | Non-existent file, empty file, corrupt JSON, corrupt YAML, `.bak` failure, lock active |
| `g2.py` | 6 | Missing output, below word count, above word count, placeholder content, non-UTF-8 |
| `g3.py` | 6 | Missing deps.json, missing prerequisite report, score < threshold, scorer=generator, scorer in history |
| `g5.py` | 7 | Unknown phase, prereq score < threshold, missing report, handoff mismatch, cross-skill conflict (char role, numeric, terminology), output pattern not found |
| `g6.py` + `g6_checks.py` | 20 | No chapters dir, below min count, chapter gaps, G4 fail on chapter, timeline regression, future knowledge, 4+ consecutive same type, no action peaks, hook density high/low, max distance exceeded, unresolved hooks, volume mismatch, ghost character, sensitive words, style range violation |
| `g7.py` | 10 | Hallucinated skills, missing coverage, template placeholders, pending truth, changelog not writable, marker re-run mismatch, score vector duplication |
| `g_dispatch.py` | 3 | Missing progress.json, invalid JSON, queue not empty |
| `g_reconcile.py` | 3 | Missing report, status mismatch |
| `g_transition.py` | 4 | Missing progress.json, remaining queue not empty, gate blockers present |
| `shared.py` | 8 | jload non-dict JSON, yload non-dict YAML, yload empty, find_report missing, normalize_file_paths edge inputs, write_gate_marker no round_dir, read_genre_config missing file |

### PR-53: G4 bespoke checker error paths (~25 tests)

Dedicated error-path tests for the 5 checkers with complex bespoke logic:

| Checker | Tests | Error paths |
|---|---|---|
| `chapter_drafting` | 7 | Content overlap >40%, no visual scene, no chapter-end hook, PRE_WRITE_CHECK missing, POST_WRITE_CHECK missing, transition density too high, fatigue words exceeded |
| `worldbuilding` | 5 | Story structure issues, missing required sections, template placeholders |
| `foreshadowing_plant` | 5 | Hook metadata missing, max_distance exceeded, ops >8, SMOKESCREEN detected, hooks section with non-list YAML |
| `character_design` | 4 | Voice not distinct, protagonist missing, YAML parse error |
| `genre_config` | 4 | Invalid config values, missing chapter_word, missing fatigue_words |

### PR-54: Dispatcher + plugins error paths + threshold bump (~10 tests)

| Module | Tests | Error paths |
|---|---|---|
| `dispatcher/executor.py` | 5 | Skill not found, missing Reads section, missing Writes section, invalid skill name |
| `plugins/generate.py` | 5 | Missing master.json, malformed master.json (missing fields), unknown platform format, apostrophe escaping verification |

**Threshold**: `fail_under`: 30 → 60. Branch coverage xfail reason updated to "Phase 3 will raise to 80%+".

### Phase 2 totals

| Metric | After Phase 1 | After Phase 2 |
|---|---|---|
| Test count | ~580 | ~705 |
| Test density | ~0.093 | ~0.113 |
| Line coverage (est.) | ~35-40% | ~65-70% |
| Error-path coverage | Untested | All defensive branches covered |

## Phase 3: Coverage Fill + Threshold Enforcement (PR-55 ~ PR-56)

**Goal**: Close the remaining 20-25% coverage gap to hit spec targets (90% line, 80% branch, 0.10 density).

### Why Phase 3 is data-driven

Phases 1+2 cover business logic paths. Phase 3 targets the long tail — rare conditionals, boundary conditions, uncovered branches identified by coverage analysis. The exact test count depends on what the coverage report reveals after Phase 2 lands.

### PR-55: Coverage gap analysis + targeted fill (~50 tests)

**Step 1**: Generate detailed coverage report after Phase 2 merge:
```bash
uv run pytest --cov=src/shenbi --cov-branch --cov-report=html:tests/coverage
uv run pytest --cov=src/shenbi --cov-branch --cov-report=term-missing
```

**Step 2**: For each module below 90% line / 80% branch, write targeted tests:

| Category | Est. tests | Typical gaps |
|---|---|---|
| Gate regex branches | ~15 | Specific patterns in G0.5b rubric parsing, G6.4 entity/knowledge regexes, G6.8 voice profile parsing |
| G4 checker long tail | ~15 | The 15 non-bespoke checkers each have 1-3 unique branches not covered by the common harness |
| Shared helper boundaries | ~8 | `jload`/`yload` with empty files, `word_count_md` with various content types, `write_gate_marker` error paths |
| Dispatcher internals | ~7 | Dispatch loop branches, error recovery, state transitions |
| Plugin generator | ~5 | Codex/cursor/opencode format-specific branches, field extraction edge cases |

**Done criteria**: every module at ≥85% line / ≥75% branch.

### PR-56: Final fill + threshold enforcement (~25 tests)

**Step 1**: Second coverage analysis. Fill remaining gaps to hit ≥90% line / ≥80% branch.

**Step 2**: Enforce thresholds permanently — remove xfail from branch coverage test, raise `fail_under` to 90.

**Done criteria**: `just check` passes with `fail_under=90`, branch coverage test passes (no xfail), density test passes.

### Phase 3 totals

| Metric | After Phase 2 | After Phase 3 |
|---|---|---|
| Test count | ~705 | ~780 |
| Test density | ~0.113 | ~0.125 |
| Line coverage | ~65-70% | ≥90% |
| Branch coverage | ~55-60% | ≥80% |
| xfail count | 2 | 0 |
| `fail_under` | 60 | 90 |

## PR Dependency Graph

```
PR-48 (fixture factory + gate happy paths)
  │
  ├── PR-49 (G4 parametrized harness, 147 tests)
  │
  ├── PR-50 (dispatcher + plugins happy paths)
  │
  └── PR-51 (threshold bump: fail_under 1→30)
        │
        ├── PR-52 (gate error paths, ~90 tests)
        │
        ├── PR-53 (G4 bespoke error paths, ~25)
        │
        └── PR-54 (dispatcher+plugins errors + threshold 30→60)
              │
              ├── PR-55 (coverage gap analysis + targeted fill, ~50)
              │
              └── PR-56 (final fill + threshold 60→90, remove xfail)
```

PRs within each phase can be parallelized across subagents. Cross-phase PRs are sequential.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Phase 3 test count estimate (75) is wrong | Phase 3 is explicitly data-driven. PR-55 starts with coverage analysis. If gaps need 100+ tests, split PR-55. If only 40 needed, merge PR-55+56. |
| G4 parametrized harness (147 tests) is slow | All tests are direct-import (no subprocess). 147 tests should run in <2 seconds. Monitor in CI. |
| Coverage plateaus at ~85% due to unreachable error paths | Accept `# pragma: no cover` for genuinely unreachable code. Document each exclusion with a reason. Target: ≤3% excluded lines. |
| Gate logic changes during test-writing | Each PR's tests pin current behavior. If gate logic changes, the test fails and forces conscious update. |
| Branch coverage harder to hit than line coverage | Phase 3 PR-55 specifically targets branch gaps via `--cov-report=term-missing`. Each missed branch gets a targeted test. |

## Acceptance Criteria

After PR-56 merges:

1. **`fail_under = 90`** in `pyproject.toml` and CI passes
2. **`BRANCH_THRESHOLD_PCT = 80`** test passes without xfail
3. **Test density ≥ 0.10** (780+ tests / 6232 LOC)
4. **Zero xfail tests** in the coverage/density suite
5. **Every `src/shenbi/*.py` module** has ≥1 test file covering it
6. **G4 parametrized harness** covers all 21 checkers for 7 common patterns
7. **`just check` passes** including the coverage threshold test
8. **No `# pragma: no cover`** without an inline reason comment

## Estimated Effort

| Phase | PRs | Tests | Est. effort |
|---|---|---|---|
| Phase 1 | PR-48 ~ PR-51 | ~205 | 2-3 days |
| Phase 2 | PR-52 ~ PR-54 | ~125 | 2-3 days |
| Phase 3 | PR-55 ~ PR-56 | ~75 | 1-2 days |
| **Total** | **9 PRs** | **~405** | **5-8 days** |

## References

- P-1.E spec acceptance criteria: `docs/superpowers/specs/2026-06-15-p-1.e-foundation-completion/README.md`
- Threshold justification: same spec, §"Threshold Justification"
- Current coverage state: `pyproject.toml` (`fail_under = 1`), `tests/unit/test_coverage_thresholds.py` (xfail)
