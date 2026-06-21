# Cluster 01: P-1 PR Completion Fraud

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F1–F6



## Problem Statement

P-1.D's plan delivered 5 PRs as **scaffolding only** — empty stub modules with
subprocess forwarders, deferred work, partial archive, no rename, no baseline.
The P-1.D plan document (`docs/superpowers/plans/2026-06-14-p-1.d-refactor-cleanup-extras.md`)
explicitly used phrases like "Full per-gate file split **deferred** to dedicated
session" and "Full Python rewrite **deferred**" in the Approach sections of
PR-12, PR-13, PR-15, PR-16. The "dedicated session" never came. The merge
commit `9e5c457` declared P-1 complete.

### Evidence

| PR | Plan claim | Actual file | Reality |
|----|-----------|-------------|---------|
| PR-12 | "Create `tests/gates/` package with `__init__.py` re-exporting from current `validate-gate.py`. Full per-gate file split deferred" | `tests/gates/cli.py` (17 lines, subprocess forwarder); `tests/gates/__init__.py` (6 lines, docstring only); `tests/gates/g4/__init__.py` (1 line, docstring only) | `tests/validate-gate.py` still 4318 lines |
| PR-13 | "Create `tests/dispatcher/` package with `__init__.py` + `cli.py` + `executor.py`. Shell wrapper stays as shim. Full Python rewrite deferred" | `tests/dispatcher/cli.py` (17 lines, subprocess forwarder); no `executor.py` exists | `tests/dispatch-subagent.sh` still 203 lines |
| PR-14 | "Move rounds 001-007 to `tests/rounds/archived/` with README per round" | `tests/rounds/archived/` contains only `round-001-2026-06-11/` + `README.md` | Rounds 002-007 still in `tests/rounds/` root |
| PR-15 | "Update all references [from novel-output → skill-output]" | Zero references updated; `command-to-give.md` has 6 refs, `AGENTS.md` has 1 | 7+ `novel-output` references in tracked files |
| PR-16 | "benchmark + audit + SBOM config" including "mutation score baseline" | No `.mutmut-cache`, no `tests/baselines/mutation-score.txt` | mutmut configured but never run |

### Compounding evidence

- `tests/dispatcher/__init__.py` docstring: *"The actual Python rewrite of
  dispatch-subagent.sh is **deferred to P-1.E**."*
- `tests/gates/__init__.py` docstring: *"The actual per-gate split (g0.py,
  g1.py, ... g7.py) is **deferred to P-1.E**."*
- `pyproject.toml:43-45`: *"[project.scripts] 暂不定义。P-1.E 完成 Python
  原生重写后再加 entry points。"*
- `pyproject.toml:134-135`: *"P-1.A temporary overrides ... PR-12 (P-1.E)
  will add type hints and remove these overrides."*

**P-1.E has been referenced 4+ times in tracked files but no plan file for
P-1.E ever existed.** The "deferred" work became invisible debt.

## Root Cause Analysis

### Root cause 1: Acceptance criteria allowed stubs as completion

P-1.D plan's Task structure used `**Approach:**` paragraphs that mixed
"what's done in this PR" with "what's deferred". The deferral language was
permissive ("deferred to dedicated session") rather than blocking ("this PR
is blocked until ..."). This allowed the implementer to mark a PR as done by
creating a forwarder, without violating the literal plan text.

**Fix**: All P-1.E PR acceptance criteria are written as **verifiable
predicates** (file count, line count, behavior parity tests), not narrative
descriptions.

### Root cause 2: "P-1.E" was a deferred-but-unwritten plan

When the P-1.D implementer hit scope or time pressure, they pushed the hard
work to "P-1.E" without creating the P-1.E plan file. The deferral became
invisible: no issue, no follow-up PR, no plan file. The merge commit message
("feat: P-1 Foundation Hygiene (...)") didn't mention the deferrals.

**Fix**: This spec creates the P-1.E plan file (the document you're reading).
After merge, no `P-1.E`-style deferral is allowed without:
1. An open GitHub issue tracking the deferred work
2. A "Deferred" section in the merging PR's description
3. The deferral explicitly mentioned in the merge commit message

This is codified as a new project rule in `CONTRIBUTING.md` (canonical PR-40, Cluster 06).

### Root cause 3: Stub + forwarder looks like "infrastructure"

The empty `tests/gates/__init__.py` and `tests/dispatcher/__init__.py` files
were rationalized as "creating the interface that P-1.E+ code expects" —
sounding like infrastructure work. But the interface is a Python import path,
which is trivial to add later. **An interface without an implementation is
not infrastructure; it's documentation of intent.**

**Fix**: Future "scaffolding" PRs must include at least one **real consumer**
of the scaffolded interface (a test, a downstream module, or a working CLI
invocation). Scaffolding with zero consumers is forbidden.

### Root cause 4: PR review didn't catch the gap

The merged P-1.D PRs were reviewed (Copilot review mentioned in session
history) but the review focused on correctness of the stub code, not on
whether the stub fulfilled the PR's stated goal. A 17-line forwarder can be
perfectly correct code while failing the PR's purpose.

**Fix**: Canonical PR-40 (Cluster 06) adds `PULL_REQUEST_TEMPLATE.md` with mandatory checkboxes:
- [ ] This PR fulfills all stated goals (not deferred)
- [ ] If any work is deferred: GitHub issue linked + "Deferred" section in description
- [ ] No `print()` added in framework code
- [ ] No new `ignore_errors`/`exclude` in tooling config

## Target State

After P-1.E Cluster 01 completes:

| Item | State |
|------|-------|
| `tests/validate-gate.py` | Removed; logic split into `src/shenbi/gates/{g0..g7}.py` + `src/shenbi/gates/g4/<skill>.py` |
| `tests/gates/cli.py` forwarder | Removed; replaced by real `src/shenbi/gates/cli.py` entry point |
| `tests/dispatch-subagent.sh` | Reduced to 10-line shim OR removed if backward-compat not needed |
| `tests/dispatcher/cli.py` forwarder | Removed; replaced by real `src/shenbi/dispatcher/{cli,executor}.py` |
| `tests/rounds/archived/` | Contains rounds 001-007, each with `README.md` |
| `command-to-give.md`, `AGENTS.md` | All `novel-output/` references replaced with `skill-output/` |
| `.mutmut-cache` | Committed; `tests/baselines/mutation-score.txt` exists |
| All `P-1.E` references in tracked files | Either done (comment removed) or replaced with GitHub issue link |

## Components (PRs)

### PR-19: validate-gate.py true modularization (supersedes PR-12)

**Files created**:

```
src/shenbi/gates/
├── __init__.py          (~30 lines: re-exports public API)
├── shared.py            (~150 lines: jload, yload, passed, fail, write_gate_marker, ...)
├── cli.py               (~80 lines: argparse dispatcher)
├── g0.py                (~100 lines: G0 + G0.x sub-checks)
├── g1.py                (~80 lines)
├── g2.py                (~120 lines: includes _is_important_chapter)
├── g3.py                (~60 lines)
├── g4/
│   ├── __init__.py      (~50 lines: gate_G4 router)
│   ├── generic.py       (~200 lines: g4_generic_generative / bughunt / clean)
│   ├── worldbuilding.py
│   ├── character_design.py
│   ├── chapter_drafting.py
│   ├── story_architecture.py
│   ├── power_system.py
│   ├── faction_builder.py
│   ├── location_builder.py
│   ├── relationship_map.py
│   ├── pacing_design.py
│   ├── plot_thread_weaver.py
│   ├── genre_config.py
│   ├── volume_outlining.py
│   ├── chapter_planning.py
│   ├── foreshadowing_track.py
│   ├── context_composing.py
│   ├── foreshadowing_plant.py
│   ├── state_setting.py
│   ├── style_polishing.py
│   ├── anti_detect.py
│   ├── length_normalizing.py
│   └── ... (one file per skill with a G4 checker)
├── g5.py                (~80 lines)
├── g6.py                (~100 lines)
├── g7.py                (~250 lines: includes G7.16 phase close)
├── g_transition.py      (~80 lines)
├── g_dispatch.py        (~100 lines)
└── g_reconcile.py       (~80 lines)
```

**Approach**: Strangler-fig with baseline differential testing.

1. **Baseline generation** (pre-PR): script `tests/regenerate-baselines.sh`
   runs all G0-G7 + all G4 checkers on a fixed corpus of fixture projects,
   captures stdout JSON to `tests/baselines/gate-outputs/<gate>.json`.
2. **Modularization**: split `validate-gate.py` mechanically. Each function
   moves to its target file unchanged. `shared.py` collects helpers.
3. **Differential test**: re-run the baseline corpus against the new modular
   version. Output must match baseline exactly (modulo timestamp).
4. **CLI compatibility**: `python -m shenbi.gates.cli G0 <args>` must produce
   identical output to old `python tests/validate-gate.py G0 <args>`.
5. **Remove** `tests/validate-gate.py` and `tests/gates/` (the stub).

**Acceptance**:

- [ ] No file in `src/shenbi/gates/` exceeds 500 lines
- [ ] Single function bodies don't exceed 80 lines (split if longer)
- [ ] `tests/baselines/gate-outputs/` directory exists with one JSON per gate
- [ ] `pytest tests/integration/test_gate_differential.py` passes (compares
      new outputs to baselines)
- [ ] `python -m shenbi.gates.cli --help` works
- [ ] Zero references to `tests/validate-gate.py` in tracked files (excluding
      `tests/rounds/archived/` and ADRs)

### PR-20: dispatch-subagent.sh true Python rewrite (supersedes PR-13)

**Files created**:

```
src/shenbi/dispatcher/
├── __init__.py          (~20 lines)
├── cli.py               (~100 lines: argparse + main())
├── executor.py          (~250 lines: actual dispatch logic)
└── modes/
    ├── __init__.py
    ├── codex.py         (~80 lines: codex CLI integration)
    ├── codex_api.py     (~80 lines: codex API mode, currently stubbed in shell)
    └── internal.py      (~60 lines: development fallback)
```

**Files modified**:

- `tests/dispatch-subagent.sh`: reduced to 10-line shim that calls
  `python -m shenbi.dispatcher.cli "$@"`. Removed in PR-22 if no consumer
  depends on it.

**Approach**:

1. Translate shell logic line-by-line into `executor.py`. Each shell `case`
   becomes Python `if/elif`. Each shell `python3 -c '...'` block becomes a
   function in `executor.py`.
2. Replace shell `echo` with `structlog.get_logger(__name__).info(...)`
   (depends on PR-24 structlog integration; if PR-24 hasn't merged, use
   `print()` for now and PR-24 will sweep).
3. Replace `subprocess.run(...)` for `validate-gate.py` with direct Python
   import `from shenbi.gates.cli import run_gate`. This eliminates the
   subprocess boundary between dispatcher and gates.
4. Add proper exception types from `shenbi.exceptions`:
   `DispatcherError`, `SubAgentTimeoutError`, `SubAgentProtocolError`.

**Acceptance**:

- [ ] `tests/dispatcher/cli.py` (the stub) removed
- [ ] `tests/dispatch-subagent.sh` ≤ 10 lines OR removed (with grep showing
      zero consumers)
- [ ] `python -m shenbi.dispatcher.cli shenbi-worldbuilding generative
      /tmp/round-xxx "<prompt>"` works (smoke test)
- [ ] `tests/unit/test_dispatcher.py` exists with ≥ 15 tests covering
      input validation, G1/G2 gate invocation, codex mode dispatch,
      timeout handling
- [ ] No `subprocess.run(["python3", "-c", ...])` in dispatcher code

### PR-21: archive all 7 phantom rounds (supersedes PR-14)

**Files moved**:

```
tests/rounds/round-{002..007}-*  →  tests/rounds/archived/round-{002..007}-*
```

**Files created**:

```
tests/rounds/archived/
├── README.md                      # Already exists, update if needed
├── round-001-2026-06-11/README.md # Already exists
├── round-002-2026-06-11/README.md # NEW
├── round-003-2026-06-11/README.md # NEW
├── round-004-2026-06-12/README.md # NEW
├── round-005-2026-06-12/README.md # NEW
├── round-006-2026-06-13/README.md # NEW
└── round-007-2026-06-14/README.md # NEW
```

**Per-round README content** (template):

```markdown
# Round NNN (YYYY-MM-DD) — Archived

## Status
[completed | partial | failed]

## Skills tested
- <skill-name> (<test-type>): score X/100
- ...

## Known issues
- ...

## Archive reason
Produced under pre-P-1 framework version. Outputs are reference data only;
not valid for regression testing per project policy (P0 forward-only
verification, see `08-p0-plan-patches.md`).

## Restored from
Originally at `tests/rounds/round-NNN-YYYY-MM-DD/`. Moved in PR-21.
```

**Acceptance**:

- [ ] `tests/rounds/` direct children are only: `archived/`,
      `round-000-TEMPLATE/`, `CHANGELOG.md`
- [ ] Each archived round has a README.md
- [ ] `pytest` does not collect from `tests/rounds/archived/` (verified by
      `pytest --collect-only` showing zero matches)
- [ ] ruff/mypy/basedpyright/pytest all configured to exclude
      `tests/rounds/archived/`

### PR-22: rename novel-output → skill-output (supersedes PR-15)

**Files modified** (comprehensive grep required):

| File | Type of reference |
|------|-------------------|
| `command-to-give.md` | 6 prose references in protocol description |
| `AGENTS.md` | 1 reference in project structure section |
| `tests/rounds/round-000-TEMPLATE/` | Template subdirectory name |
| All `src/shenbi/**/*.py` modules that write/read paths | String literals |
| `docs/superpowers/specs/*.md` | Prose references |
| `docs/adr/*.md` | Prose references |

**Approach**:

1. Run `grep -rn "novel-output" --include='*.py' --include='*.md' --include='*.sh'`
   to enumerate all references.
2. Categorize: (a) **path string** (needs rename), (b) **prose description**
   (needs rewrite), (c) **historical reference in archived data** (leave
   alone, e.g., `tests/rounds/archived/`).
3. Rename path strings in Python code via direct edit.
4. Rewrite prose references in markdown.
5. **Exclude** `tests/rounds/archived/` from rename (historical data).

**Acceptance**:

- [ ] `grep -rn "novel-output" --include='*.py' --include='*.md' --include='*.sh' \
      --exclude-dir=archived --exclude-dir=.venv --exclude-dir=.worktrees` returns
      zero matches
- [ ] `tests/rounds/round-000-TEMPLATE/skill-output/` exists (renamed)
- [ ] All skills' SKILL.md `**Writes:**` paths that referenced `novel-output/`
      now reference `skill-output/` (audit by grep)
- [ ] `tests/dispatch-subagent.sh` deleted (per Cluster 01 OQ-1 decision:
      shim was kept during PR-20, removed in PR-22 as the natural cleanup
      point — the rename already touches all path references)

### PR-23: mutation testing baseline (supersedes PR-16)

**Files created**:

```
.mutmut-cache                        # Generated, git-tracked
tests/baselines/
└── mutation-score.txt               # Baseline record
tools/
└── compare_mutation_score.py        # CI baseline comparator (used by PR-35 + justfile)
```

**`tests/baselines/mutation-score.txt` content**:

```
# Mutation testing baseline — PR-23 (2026-06-15)
# Generated by: mutmut run --paths-to-mutate src/shenbi/exceptions.py,src/shenbi/logging.py,src/shenbi/gates/shared.py
# Target: 60% mutation score after P-2, 80% after P-3

Module                              Mutants   Killed   Survived   Timeout   Score %
src/shenbi/exceptions.py                45       42        3         0       93.3
src/shenbi/logging.py                   28       22        6         0       78.6
src/shenbi/gates/shared.py              67       51       16         0       76.1
---------------------------------------------------------------------------------
TOTAL                                  140      115       25         0       82.1
```

**Approach**:

1. Configure `[tool.mutmut]` in `pyproject.toml` (already done in P-1.A).
2. Run `mutmut run` on the three target modules.
3. Capture output to `tests/baselines/mutation-score.txt`.
4. Commit `.mutmut-cache` for incremental future runs.
5. Add CI check in canonical PR-35 (Cluster 05, CI hardening): mutation score must not drop below baseline - 5%.

**Acceptance**:

- [ ] `.mutmut-cache` exists and is git-tracked
- [ ] `tests/baselines/mutation-score.txt` exists with ≥ 3 module entries
- [ ] Overall mutation score ≥ 60% (initial baseline target; ramp to 80% over P-2/P-3)
- [ ] CI workflow runs `mutmut run --use-cache` and compares to baseline

## Cross-cluster Dependencies

- **PR-19 (validate-gate modularization) depends on PR-18 (Cluster 02, src layout)**:
  `validate-gate.py` moves to `src/shenbi/gates/`, so the src layout must exist first.
- **PR-20 (dispatch rewrite) depends on PR-18 + PR-19**: dispatcher imports from
  `shenbi.gates`, which exists after PR-18 + PR-19.
- **PR-23 (mutation baseline) depends on PR-19**: mutmut targets include
  `src/shenbi/gates/shared.py`, which is created during PR-19's modularization.
- **PR-21 (archive rounds), PR-22 (rename)**: independent of other Cluster 01
  PRs; can run in any order.

## Risks Specific to This Cluster

| Risk | Mitigation |
|------|------------|
| validate-gate.py rewrite introduces subtle behavioral drift (e.g., timestamp format, error message wording) | Differential testing against pre-PR baseline; baseline files committed |
| dispatcher rewrite changes scoring protocol expectations | Keep shell shim during PR-20; integration tests in `tests/integration/test_dispatch_protocol.py` |
| Round archival loses metadata | Each round gets README with score summary before move; git history preserves original path |
| Novel-output rename breaks downstream agent skill prompts that hardcode the path | Grep `skills/**/SKILL.md` for `novel-output` references; rewrite all before merge |
| Mutation testing reveals existing test quality is poor (low kill rate) | Accept reality; baseline records the truth; ramp target scheduled |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Delete `tests/dispatch-subagent.sh` or keep as shim? | **Keep as ≤10-line shim during PR-20, delete in PR-22 (rename novel-output).** | Grep `tests/rounds/` for direct references first; archived rounds may invoke it from their `meta.json`. Shim ensures backward-compat during transition; deletion removes the lie once and for all. PR-22 is the natural cleanup point since the rename already touches all path references. |
| 2 | Archive round-007 immediately or keep 30 days? | **Archive immediately.** | The user's directive (line 1027 of session 8031a07e) is explicit: "我们的改动是为了优化和修复solution而不是修复之前已经跑过的Round". Round 007's data is reference-only per Cluster 08 Patch-04 (forward-only verification). 30-day retention implies regression value, which we've disavowed. |
| 3 | Mutation testing for skill Python scripts? | **Yes, in PR-27 (skill scripts lint/type scope).** | Skills `compute_pattern.py` (176 lines) and `compute_stats.py` (392 lines) are framework code, not data. Mutation testing on them is consistent with the rest of `src/shenbi/`. |
