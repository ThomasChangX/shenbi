# Test Coverage Completion Design

- Status: **accepted** (2026-06-16, post-Round-1 review)
- Date: 2026-06-16
- Deciders: ThomasChangX
- Blocks: P0 (pipeline safety depends on tested gates)

## TL;DR

P-1.E's acceptance criteria require 80% branch coverage, 90% line coverage, and 0.10 test density on `src/shenbi/`. Current state: ~3% line coverage, 0.061 density (380 test functions / 6232 LOC), 2 xfail tests. This spec delivers ~260 additional **test functions** across 10 PRs in 3 phases, reaching 640+ functions (density ≥0.10) and 90%/80% coverage. Includes previously-missed `skill_utils/` module (553 LOC, 0 tests) whose coverage is mathematically required to hit 90%.

## Background

### How we got here

P-1.E Cluster 04 (PR-28 ~ PR-34) added tests for 4 modules: `scoring.py`, `phase_runner.py`, `update_progress.py`, `summarize_round.py`. These went from 0% to ~90% coverage. However, gates, dispatcher, plugins, and skill_utils remained minimally tested.

A coverage audit on 2026-06-16 found:

| Module group | LOC | Test functions | Coverage |
|---|---|---|---|
| scoring + phase_runner + update_progress + summarize_round | ~1000 | ~200 | ~90% |
| gates/ (g0-g7 + shared + g4/* + helpers) | ~4480 | ~80 | ~3% |
| dispatcher/ | ~180 | ~6 | ~5% |
| plugins/ | ~130 | 0 | 0% |
| skill_utils/ | ~553 | 0 | 0% |
| **Total** | **~6232** | **~380** | **~3%** |

Two xfail tests gate the thresholds:
- `test_branch_coverage_meets_threshold` — branch coverage ≥80% (xfail strict)
- `test_density_meets_threshold` (in `test_test_density.py`) — density ≥0.10 (xfail strict)

`fail_under = 1` in `pyproject.toml` (regression-only, not enforcement).

### Why goal-prompt.md testing doesn't close this gap

The `goal-prompt.md` protocol runs integration-level T1/T2/T3 pipeline tests through CLI entry points. This exercises framework code functionally but doesn't produce `pytest --cov` measurable coverage. Even a full pipeline run with coverage instrumentation would hit only ~15-25% line coverage (happy-path branches only). The remaining branches — error handling, edge cases, alternative configurations — require dedicated unit tests.

### Critical math constraints

**Density**: defined as `test_function_count / framework_loc`. A parametrized `def test_foo(self, param)` counts as **1 function** regardless of parametrize case count. Current: 380 functions → need 624 for 0.10 density. Spec delivers 640+.

**Coverage ceiling without skill_utils**: skill_utils is 553/6232 = 8.9% of codebase. If it stays at 0% coverage, maximum overall line coverage = 91.1% — only if everything else hits 100% (impossible due to unreachable branches). **Therefore skill_utils MUST have tests to achieve the 90% target.** This was missed in the original draft and is now PR-50b.

## Goals

1. **Hit spec targets**: 80% branch, 90% line, ≥0.10 test density on `src/shenbi/`.
2. **Pipeline safety**: every gate function's happy-path tested so the goal-prompt.md pipeline can execute without hitting untested code.
3. **Bug prevention**: every error-handling branch tested to catch defensive-code regressions.
4. **Zero xfails**: remove both coverage and density xfail markers; enforce thresholds permanently.

## Non-Goals

1. **No integration test expansion**: T1/T2/T3 pipeline tests are a separate concern.
2. **No test framework changes**: pytest, hypothesis, coverage.py configs stay as-is.
3. **No gate logic changes**: tests pin current behavior. If tests reveal bugs, fix in a separate PR.
4. **No performance benchmarking**: test speed monitored but not gated.

## Architecture

### Test file structure

```
tests/unit/gates/
├── conftest.py                  # Fixture factory (new) — supports project_dir + round_dir
├── test_g0.py                   # Expand (6→18 functions)
├── test_g0_purity.py            # New (5 functions)
├── test_g1.py                   # Expand (3→8)
├── test_g2.py                   # Expand (9→15)
├── test_g3.py                   # Expand (4→10)
├── test_g5.py                   # Expand (11→18)
├── test_g6.py                   # Expand (6→14)
├── test_g6_checks.py            # New (8 functions)
├── test_g7.py                   # Expand (6→16)
├── test_g_dispatch.py           # Expand (6→9)
├── test_g_reconcile.py          # New (5 functions)
├── test_g_transition.py         # New (4 functions)
├── test_shared.py               # Expand (36→48)
├── g4/
│   ├── conftest.py              # G4-specific fixtures (skill output samples)
│   ├── test_common.py           # Parametrized harness: 7 functions × 21 = 147 cases
│   ├── test_chapter_drafting.py # Bespoke: 7 functions
│   ├── test_worldbuilding.py    # Bespoke: 5 functions
│   ├── test_foreshadowing_plant.py  # 5 functions
│   ├── test_character_design.py # 4 functions
│   └── test_genre_config.py     # 4 functions
tests/unit/
├── test_dispatcher_executor.py  # New (13 functions)
└── test_plugins_generate.py     # New (10 functions)
tests/unit/skill_utils/
├── test_compute_pattern.py      # New (15 functions)
└── test_compute_stats.py        # New (20 functions)
tests/property/gates/
├── test_gate_invariants.py      # New (5 property functions)
```

### Fixture factory pattern (revised)

The factory creates **both** `project_dir` (for project state: chapters, novel.json, etc.) and `round_dir` (for round state: t1-reports, summary.json, progress.json, gate-markers). This matches the actual gate function signatures.

```python
# tests/unit/gates/conftest.py

@pytest.fixture
def make_project(tmp_path):
    """Factory: build project_dir + round_dir for gate testing.

    Returns (project_dir, round_dir) tuple. Gates that need both
    (gate_G6) receive both; gates that need only round_dir
    (gate_G7) receive just round_dir.
    """
    def _make(
        *,
        chapters: list[str] | None = None,
        novel_json: dict | None = None,
        genre_config: dict | None = None,
        pending_hooks: str | None = None,
        style_profile: str | None = None,
        volume_map: str | None = None,
        progress: dict | None = None,
        summary: dict | None = None,
        t1_reports: dict[str, dict] | None = None,
        gate_markers: list[dict] | None = None,
        seed_file: str | None = None,
    ) -> tuple[Path, Path]:
        project_dir = tmp_path / "project"
        round_dir = tmp_path / "round"
        project_dir.mkdir()
        round_dir.mkdir()

        # Project-level files
        if seed_file:
            (project_dir / "seed.md").write_text(seed_file)
        if chapters:
            ch_dir = project_dir / "chapters"
            ch_dir.mkdir()
            for i, content in enumerate(chapters, 1):
                (ch_dir / f"chapter-{i:03d}.md").write_text(content, encoding="utf-8")
        if novel_json is not None:
            (project_dir / "novel.json").write_text(json.dumps(novel_json))
        if genre_config is not None:
            (project_dir / "genre-config.json").write_text(json.dumps(genre_config))
        if pending_hooks is not None:
            truth = project_dir / "truth"
            truth.mkdir(exist_ok=True)
            (truth / "pending_hooks.md").write_text(pending_hooks)
        if style_profile is not None:
            config = project_dir / "config"
            config.mkdir(exist_ok=True)
            (config / "style_profile.md").write_text(style_profile)
        if volume_map is not None:
            outline = project_dir / "outline"
            outline.mkdir(exist_ok=True)
            (outline / "volume_map.md").write_text(volume_map)

        # Round-level files
        if progress is not None:
            (round_dir / "progress.json").write_text(json.dumps(progress))
        if summary is not None:
            (round_dir / "summary.json").write_text(json.dumps(summary))
        if t1_reports:
            reports_dir = round_dir / "t1-reports"
            reports_dir.mkdir()
            for skill_name, report_data in t1_reports.items():
                (reports_dir / f"{skill_name}-generative-scores.json").write_text(
                    json.dumps(report_data)
                )
        if gate_markers:
            marker_dir = round_dir / "gate-markers"
            marker_dir.mkdir()
            for i, marker in enumerate(gate_markers):
                (marker_dir / f"marker-{i}.json").write_text(json.dumps(marker))

        return project_dir, round_dir
    return _make
```

### G4 checker contract

Before writing the parametrized harness, document the shared contract every G4 checker must satisfy. Any checker that violates the contract is fixed first (not worked around in the harness):

```
Contract: every g4_<skill>() function:
1. Accepts fps: list[str] (file paths) and optional rd: str | None (round dir)
2. Returns a JSON string (never raises for any input)
3. Output JSON has keys: "gate", "status", "checks"
4. status ∈ {"PASS", "FAIL"}
5. Empty fps → status="FAIL" or "PASS" with WARN check (never crash)
6. Non-existent file in fps → status="FAIL" with descriptive "r" field
```

If any checker violates the contract (e.g., raises on empty input), PR-49 fixes the checker code first, then the harness test passes.

### Test invocation model

All tests use **direct import** (not subprocess), consistent with PR-32's pattern. Fast, debuggable, no subprocess overhead.

**Test markers**: all new test functions must be decorated with `@pytest.mark.unit` so they're included in `just test` (which runs `-m "unit"`). Test classes can use `@pytest.mark.unit` at class level.

**Note on `test_doc_links.py`**: this existing test parametrizes over all `*.md` files, producing hundreds of test cases when `markdown-link-check` is installed (CI only). These cases count as 1 test function toward the density metric (density counts `def test_*` functions, not parametrized cases). No changes needed to this test.

**G4 checker import pattern**: the parametrized harness imports all 21 checkers explicitly (not dynamically). Each import is a single line: `from shenbi.gates.g4.worldbuilding import g4_worldbuilding`. Explicit imports enable IDE navigation and catch import errors at collection time.

## Phase 1: Critical-Path Tests (PR-48 ~ PR-51)

**Goal**: Every gate function, dispatcher, plugin generator, and skill_utils module has happy-path test coverage. After Phase 1, the goal-prompt.md pipeline exercises only tested code paths.

### PR-48: Fixture factory + gate happy-path tests (~55 new functions)

`conftest.py` with `make_project` factory, plus happy-path tests for every gate:

| Module | New functions | What's covered |
|---|---|---|
| `g0.py` + `g0_purity.py` | 12 | G0.1-G0.12 happy path: valid seed, skill dirs, fixtures, scenario purity PASS |
| `g1.py` | 5 | Valid input files (JSON, YAML, markdown), `.bak` creation for in-place skills |
| `g2.py` | 6 | Valid output files, word count within range, all file types |
| `g3.py` | 6 | Prerequisites met, scores at threshold, agent isolation pass |
| `g5.py` | 7 | Phase data with prerequisites, handoff integrity pass, no conflicts |
| `g6.py` + `g6_checks.py` | 8 | Sufficient chapters, no continuity violations, valid pacing, hook density OK |
| `g7.py` | 10 | Valid summary, truth files OK, changelog writable, markers consistent |
| `g_dispatch.py` | 3 | Progress.json valid, queue ready, phase dispatchable |
| `g_reconcile.py` | 5 | All T1 reports present, scores consistent, no mismatches |
| `g_transition.py` | 4 | Phase transition with empty queue, no blockers, GT.1-GT.5 |
| `shared.py` | 4 | `write_gate_marker` + `read_genre_config` + `find_report` + `normalize_file_paths` happy path |

**Done criteria**: each gate function (`gate_G0` through `gate_G_TRANSITION`) returns valid JSON (parseable, has `status` key) when called with valid inputs from the `make_project` factory. Verified by `pytest tests/unit/gates/ -m "not error_path"` passing.

### PR-49: G4 parametrized common harness (7 new functions, 147 cases)

`g4/test_common.py`: 7 test functions × 21 checkers = 147 parametrized cases.

Before writing tests, verify the G4 checker contract (see Architecture §G4 checker contract). Fix any violating checker.

Tests:
1. `test_empty_input_returns_valid_json` — empty `fps` list → JSON with status
2. `test_missing_file_returns_fail` — non-existent path → FAIL with descriptive reason
3. `test_empty_file_handled` — zero-byte file → FAIL or WARN (not crash)
4. `test_malformed_utf8_handled` — invalid UTF-8 bytes → no crash
5. `test_output_has_gate_field` — output JSON contains correct `gate` ID
6. `test_pass_includes_checks_list` — PASS output has non-empty `checks` list
7. `test_fail_includes_must_fix` — FAIL output has non-empty `must_fix` list (if applicable — some checkers may not use must_fix; this test uses `pytest.skip` for those)

**Done criteria**: all 147 parametrized cases pass. Every G4 checker satisfies the documented contract.

### PR-50: Dispatcher + plugins happy paths (~13 new functions)

| Module | New functions | What's covered |
|---|---|---|
| `dispatcher/executor.py` | 8 | `derive_input_files`, `derive_output_files`, dispatch flow, skill lookup, input normalization |
| `plugins/generate.py` | 5 | `load_master`, `generate_all`, output matches committed manifests, all 4 platform formats |

### PR-50b: skill_utils happy-path tests (~35 new functions) — NEW

**This PR was missing from the original draft. skill_utils (553 LOC, 0 tests) is required to hit 90% coverage.**

| Module | New functions | What's covered |
|---|---|---|
| `compute_pattern.py` | 15 | `compute_consecutive`, `compute_entropy`, `classify_entropy`, `check_distribution`, `check_consecutive_warnings`, `compute_transition_matrix`, `main` with sample data |
| `compute_stats.py` | 20 | `segment_sentences`, `segment_paragraphs`, `compute_percentiles`, `compute_sentence_stats`, `compute_paragraph_stats`, `compute_ttr`, `compute_ngrams`, `compute_punctuation`, `compute_connectives`, `detect_rhetoric`, `count_ai_markers`, `count_transition_words`, `read_chapters`, `compute_all_stats`, `main` with sample chapters |

**Done criteria**: every public function in skill_utils has at least one test calling it with realistic chapter data and verifying the return type.

### PR-51: Threshold bump + xfail strict relaxation (no new tests)

- `fail_under`: 1 → 25
- **Change both xfails from `strict=True` to `strict=False`** — prevents XPASS failures when Phase 3 gradually crosses thresholds
- Branch coverage xfail reason updated: "Phase 2 will raise to 50"
- Density xfail reason updated: "Phase 2 will deliver remaining functions to hit 0.10"
- Verify full suite passes at new threshold
- **If suite fails at fail_under=25**: do NOT lower the threshold. Instead, add tests to the modules dragging coverage down. The threshold is a ratchet, not a suggestion.

**Why strict→non-strict now**: both `test_branch_coverage_meets_threshold` and `test_density_meets_threshold` currently use `strict=True`. With strict mode, the moment Phase 3 tests push density past 0.10 or branch coverage past 80%, the xfail test XPASSES → CI red → merge blocked. Switching to `strict=False` allows gradual approach. PR-56 removes both xfails entirely once thresholds are genuinely met.

### Phase 1 totals

| Metric | Before | After Phase 1 |
|---|---|---|
| Test functions | 380 | ~490 |
| Test density | 0.061 | ~0.079 |
| Line coverage (est.) | ~3% | ~35-40% |
| Pipeline safety | Gates untested | All happy paths covered |

## Phase 2: Error-Path Tests (PR-52 ~ PR-54)

**Goal**: Every error-handling branch, edge case, and defensive code path tested.

### PR-52: Gate error paths (~94 new functions)

| Module | New functions | Error paths covered |
|---|---|---|
| `g0.py` + `g0_purity.py` | 15 | Missing seed, no target_words, missing skill dirs, skill-output not writable, missing fixtures, G0.9 non-fixture paths (FAIL), G0.9c project dirs (WARN), G0.9b SKILL.md leak (FAIL), stale mirror, <59 generative tests |
| `g1.py` | 6 | Non-existent file, empty file, corrupt JSON, corrupt YAML, `.bak` failure, lock active |
| `g2.py` | 6 | Missing output, below word count, above word count, placeholder content, non-UTF-8 |
| `g3.py` | 6 | Missing deps.json, missing prerequisite report, score < threshold, scorer=generator, scorer in history |
| `g5.py` | 7 | Unknown phase, prereq score < threshold, missing report, handoff mismatch, cross-skill conflict (char role, numeric, terminology), output pattern not found |
| `g6.py` + `g6_checks.py` | 20 | No chapters dir, below min count, chapter gaps, G4 fail on chapter, timeline regression, future knowledge, 4+ consecutive same type, no action peaks, hook density high/low, max distance exceeded, unresolved hooks, volume mismatch, ghost character, sensitive words, style range violation |
| `g7.py` | 6 | Hallucinated skills, missing coverage, template placeholders, pending truth, changelog not writable, marker re-run mismatch |
| `g_dispatch.py` | 3 | Missing progress.json, invalid JSON, queue not empty |
| `g_reconcile.py` | 3 | Missing report, status mismatch |
| `g_transition.py` | 4 | Missing progress.json, remaining queue not empty, gate blockers present |
| `shared.py` | 8 | jload non-dict JSON, yload non-dict YAML, yload empty, find_report missing, normalize_file_paths edge inputs, write_gate_marker no round_dir, read_genre_config missing file, unimplemented stub |
| skill_utils error paths | 10 | Empty input to compute_* functions, invalid chapter data, missing files in read_chapters, ngram edge cases |

### PR-53: G4 bespoke checker error paths (~25 new functions)

| Checker | New functions | Error paths |
|---|---|---|
| `chapter_drafting` | 7 | Content overlap >40%, no visual scene, no chapter-end hook, PRE_WRITE_CHECK missing, POST_WRITE_CHECK missing, transition density too high, fatigue words exceeded |
| `worldbuilding` | 5 | Story structure issues, missing required sections, template placeholders |
| `foreshadowing_plant` | 5 | Hook metadata missing, max_distance exceeded, ops >8, SMOKESCREEN detected, hooks section with non-list YAML |
| `character_design` | 4 | Voice not distinct, protagonist missing, YAML parse error |
| `genre_config` | 4 | Invalid config values, missing chapter_word, missing fatigue_words |

### PR-54: Dispatcher + plugins error paths + threshold bump (~10 new functions)

| Module | New functions | Error paths |
|---|---|---|
| `dispatcher/executor.py` | 5 | Skill not found, missing Reads section, missing Writes section, invalid skill name |
| `plugins/generate.py` | 5 | Missing master.json, malformed master.json (missing fields), unknown platform format, apostrophe escaping verification, `load_master` with non-dict JSON |

**Threshold**: `fail_under`: 25 → 55. Branch coverage xfail updated. Density xfail updated.

### Phase 2 totals

| Metric | After Phase 1 | After Phase 2 |
|---|---|---|
| Test functions | ~490 | ~619 |
| Test density | ~0.079 | ~0.099 |
| Line coverage (est.) | ~35-40% | ~70-75% |
| Branch coverage (est.) | ~25% | ~60-65% |

**Note**: density 0.098 is close to but below 0.10. Phase 3 must deliver ≥11 more functions to cross the threshold.

## Phase 3: Coverage Fill + Threshold Enforcement (PR-55 ~ PR-56)

**Goal**: Close the remaining coverage gap. Hit 90% line, 80% branch, ≥0.10 density. Remove all xfails.

### Why Phase 3 is data-driven

Phases 1+2 cover business logic paths. Phase 3 targets the long tail — rare conditionals, boundary conditions, uncovered branches identified by coverage analysis. The exact test count depends on what the coverage report reveals after Phase 2.

### PR-55: Coverage gap analysis + targeted fill (~35 new functions + 5 property functions)

**Step 1**: Generate detailed coverage report after Phase 2 merge:
```bash
uv run pytest --cov=src/shenbi --cov-branch \
    --cov-report=term-missing --cov-report=html:tests/coverage
```

**Step 2**: For each module below 90% line / 80% branch, write targeted tests:

| Category | Est. new functions | Typical gaps |
|---|---|---|
| Gate regex branches | 10 | G0.5b rubric parsing patterns, G6.4 entity/knowledge regexes, G6.8 voice profile parsing |
| G4 checker long tail | 10 | 15 non-bespoke checkers each have 1-3 unique branches |
| Shared helper boundaries | 5 | `jload`/`yload` with empty files, `word_count_md` edge cases |
| Dispatcher internals | 5 | Dispatch loop branches, error recovery |
| Plugin generator | 5 | Codex/cursor/opencode format branches |

**Step 3**: Add property-based tests for invariant verification:

```python
# tests/property/gates/test_gate_invariants.py

@given(text(alphabet=string.ascii_letters + " \n", min_size=0, max_size=1000))
def test_word_count_md_non_negative(content):
    """word_count_md always returns non-negative int for any input."""
    ...

@given(list_of_chapter_contents(min_size=0, max_size=20))
def test_gate_g6_never_crashes(chapters, make_project):
    """G6 never raises for any combination of chapter contents."""
    ...
```

5 property functions covering: word_count_md, jload/yload, gate output JSON validity, G4 checker input resilience, scoring determinism.

**Done criteria**: every module at ≥85% line / ≥75% branch.

### PR-56: Final fill + threshold enforcement (~15 new functions)

**Step 1**: Second coverage analysis. Fill remaining gaps.

**Step 2**: Enforce thresholds permanently:
- Remove xfail from `test_branch_coverage_meets_threshold` (branch ≥80%)
- Remove xfail from `test_density_meets_threshold` (density ≥0.10)
- Raise `fail_under` to 90

**Step 3**: Verify density:
```bash
uv run pytest tests/unit/test_test_density.py -v  # must PASS, not xfail
```

**Done criteria**: `just check` passes with `fail_under=90`, both xfail tests removed and passing, density ≥0.10.

### Phase 3 totals

| Metric | After Phase 2 | After Phase 3 |
|---|---|---|
| Test functions | ~619 | ~674 |
| Test density | ~0.099 | ~0.108 |
| Line coverage | ~70-75% | ≥90% |
| Branch coverage | ~60-65% | ≥80% |
| xfail count | 2 | 0 |
| `fail_under` | 55 | 90 |

**Margin**: 674 functions / 6232 LOC = 0.108. This gives 50 functions of headroom above the 624 minimum (0.10 × 6232), absorbing minor LOC growth from bug fixes.

## PR Dependency Graph

```
PR-48 (fixture factory + gate happy paths, ~55 fn)
  │
  ├── PR-49 (G4 contract verify + parametrized harness, 7 fn / 147 cases)
  │
  ├── PR-50 (dispatcher + plugins happy paths, ~13 fn)
  │
  ├── PR-50b (skill_utils happy paths, ~35 fn)          ← NEW
  │
  └── PR-51 (threshold bump: fail_under 1→25)
        │
        ├── PR-52 (gate + skill_utils error paths, ~98 fn)
        │
        ├── PR-53 (G4 bespoke error paths, ~25 fn)
        │
        └── PR-54 (dispatcher+plugins errors + threshold 25→55)
              │
              ├── PR-55 (coverage analysis + targeted fill + property tests, ~40 fn)
              │
              └── PR-56 (final fill + threshold 55→90, remove both xfails)
```

PRs within each phase can be parallelized across subagents. Cross-phase PRs are sequential.

## Rollback Strategy

1. **Single-PR rollback**: `git revert <PR-merge-commit>`. Each PR is atomic. Tests and threshold changes are in the same PR.
2. **Threshold rollback**: if a threshold bump proves too aggressive (CI red after merge), revert just the `fail_under` / xfail change. The tests stay; only the enforcement is relaxed.
3. **Fixture factory rollback**: if `make_project` proves inadequate, the PR-48 tests that use it can be reverted independently of later PRs. Later PRs would need to provide their own fixtures.
4. **Phase rollback**: if Phase 2 reveals Phase 1's fixture factory was wrong, revert Phase 2 PRs, fix Phase 1, re-apply Phase 2.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Phase 3 test count estimate is wrong | Phase 3 is data-driven. PR-55 starts with coverage analysis. If gaps need more tests, split PR-55. If fewer, merge PR-55+56. |
| G4 parametrized harness (147 cases) is slow | All direct-import. 147 cases in <2 seconds (estimated). Monitor in CI; if >10s, investigate. |
| Coverage plateaus below 90% | Accept `# pragma: no cover` for genuinely unreachable code with inline reason. Target: ≤3% excluded. If plateau persists, audit for dead code and delete. |
| Gate logic changes during test-writing | Tests pin current behavior. If logic changes, test fails → conscious update. |
| Branch coverage harder to hit than line | Phase 3 PR-55 uses `--cov-report=term-missing` to identify specific missed branches. Each gets a targeted test. |
| Density function count falls short | Phase 3 has 7-function headroom (668 vs 624 needed). If still short, add property tests (each counts as 1 function) covering edge cases that also improve branch coverage. |
| skill_utils tests are complex (analysis functions with many outputs) | Focus on return-type verification + a few key output values. Don't test every possible statistic — test the contract (returns dict, has expected keys, values are numeric). |
| G4 checker contract violations block PR-49 | PR-49 Step 1 verifies contract compliance. Any violating checker is fixed in the same PR before harness tests run. |

## Acceptance Criteria

After PR-56 merges:

1. **`fail_under = 90`** in `pyproject.toml` and CI passes
2. **`BRANCH_THRESHOLD_PCT = 80`** test passes **without xfail**
3. **`test_density_meets_threshold`** passes **without xfail** (density ≥0.10)
4. **Test function count ≥ 624** (624/6232 = 0.10; spec targets 668 for headroom)
5. **Every `src/shenbi/*.py` module** has ≥1 test file, including `skill_utils/`
6. **G4 parametrized harness** covers all 21 checkers for 7 common patterns (147 cases)
7. **`just check` passes** including coverage + density threshold tests (no xfail, no `-m "not last"` exclusion for coverage)
8. **No `# pragma: no cover`** without an inline reason comment
9. **Property-based tests present** in `tests/property/` covering gate invariants (target: ~5 functions)

## Estimated Effort

| Phase | PRs | New functions | Est. effort |
|---|---|---|---|
| Phase 1 | PR-48, 49, 50, 50b, 51 | ~110 | 3-4 days |
| Phase 2 | PR-52, 53, 54 | ~129 | 3-4 days |
| Phase 3 | PR-55, 56 | ~55 | 2-3 days |
| **Total** | **10 PRs** | **~294** | **8-11 days** |

## References

- P-1.E spec acceptance criteria: `docs/superpowers/specs/2026-06-15-p-1.e-foundation-completion/README.md`
- Threshold justification: same spec, §"Threshold Justification"
- Density metric definition: same spec, §"Metric definitions (canonical)"
- Current coverage state: `pyproject.toml` (`fail_under = 1`), `tests/unit/test_coverage_thresholds.py` + `tests/unit/test_test_density.py` (both xfail)
- Test style reference: PR-28 through PR-31 (scoring/phase_runner/update_progress/summarize_round tests)
