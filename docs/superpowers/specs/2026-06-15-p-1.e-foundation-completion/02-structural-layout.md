# Cluster 02: Structural Layout — `tests/` as Runtime Package

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F7–F9



## Problem Statement

The Shenbi framework runtime code (validate-gate, scoring, dispatcher, phase
runner, summarize-round, update-progress, error-guidance, exceptions, logging)
**lives under `tests/`**. `pyproject.toml:52` ships `tests/` as the wheel
package:

```toml
[tool.hatch.build.targets.wheel]
packages = ["tests"]
```

This conflates "framework runtime code" with "test code" — both physically
and semantically. The name `tests/` lies about its contents.

### Evidence

```
tests/
├── validate-gate.py          # 4318 lines — framework runtime
├── scoring.py                # 384 lines  — framework runtime
├── phase-runner.py           # 314 lines  — framework runtime
├── summarize-round.py        # 182 lines  — framework runtime
├── update-progress.py        # 324 lines  — framework runtime
├── error_guidance.py         # 52 lines   — framework runtime
├── recovery.py               # ?          — framework runtime
├── exceptions.py             # 153 lines  — framework runtime (P-1.C added)
├── logging.py                # 43 lines   — framework runtime (P-1.C added)
├── dispatch-subagent.sh      # 203 lines  — framework runtime
├── gates/                    # stub       — intended framework runtime
├── dispatcher/               # stub       — intended framework runtime
├── conftest.py               # actual test code
├── unit/ integration/ property/ benchmark/   # actual test code
├── fixtures/ rounds/ baselines/              # test data
└── __init__.py               # shipped in wheel
```

**13 of 16 top-level entries in `tests/` are runtime code, not test code.**

### Specific consequences

1. **Importing `tests.scoring` from production is "normal"** — but the name
   `tests` signals to every reader "this is test code, safe to delete or
   skip reading". Multi-agent consumers (Cursor, Codex) reading `AGENTS.md`
   see "tests/scoring.py" listed under "Test infrastructure" and may treat
   it as expendable.
2. **P0's new tools have no clean home.** `build_registry.py`,
   `load_registry.py`, `validate_registry.py`, `validate_skill.py`,
   `migrate_skill.py` are all production code. Where do they go?
   - If under `tests/`, the lie continues.
   - If under `skills/`, they're skill data, not framework.
   - If under a new top-level `framework/`, the project has 4 code roots.
3. **`pyproject.toml` ships `tests/` in the wheel.** Anyone who installs
   Shenbi via `uv pip install shenbi` gets all the test code in their
   site-packages. This bloats the wheel from ~50KB (real runtime) to ~200KB+
   (with test data, fixtures, archived rounds).
4. **`[tool.hatch.build.targets.wheel.force-include]`** adds `skills/` and
   `docs/adr/` to the wheel too. This means the wheel is a snapshot of the
   entire repo, not a curated runtime artifact.
5. **CI matrix installs wheel and runs `pytest` from `tests/`**, which works
   only because `tests/` is the package. After src layout migration, the
   install workflow must change.
6. **Coverage `source = ["tests"]`** (pyproject.toml:203) measures coverage
   of the wrong directory.

## Root Cause Analysis

### Root cause 1: Project evolved from shell-script-based prototype

The original Shenbi was a collection of shell scripts and Python helpers in
`tests/` (named thus because they "tested" the skills by running them). As
the project grew, the helpers became framework code, but the directory name
stayed. The framing "tests/" was never revisited.

**Fix**: Explicit src layout migration. No gradual approach — rename
happens once, atomically, in PR-18.

### Root cause 2: No `[project.scripts]` entry points

```toml
# pyproject.toml:43-45
# 注：[project.scripts] 暂不定义。
# gates/cli.py 和 dispatcher/cli.py 当前 forward 到 legacy 脚本（subprocess）。
# P-1.E 完成 Python 原生重写后再加 entry points。
```

Without entry points, users invoke framework tools via
`python tests/validate-gate.py ...`. This pins the path
`tests/validate-gate.py` into every consumer's muscle memory and every
agent's plugin manifest. Renaming the path breaks everyone.

**Fix**: PR-18 adds `[project.scripts]` entries. After merge, all
documentation and agent plugins use the entry point names
(`shenbi-validate`, `shenbi-dispatch`, etc.), not file paths.

### Root cause 3: `tests/` was treated as "the project", not "tests of the project"

The structural decision to put framework code under `tests/` was never
questioned because it worked. P-1.A through P-1.D added more code to
`tests/` (exceptions.py, logging.py) without asking "should this be here?"
Each addition made the migration harder.

**Fix**: PR-18 is a non-negotiable prerequisite for P0. P0's brainstorming
(see `08-p0-plan-patches.md`) assumes the src layout exists.

## Target State

```
shenbi/
├── src/
│   └── shenbi/
│       ├── __init__.py             # version, public API
│       ├── exceptions.py           # moved from tests/
│       ├── logging.py              # moved from tests/
│       ├── scoring.py              # moved + refactored
│       ├── phase_runner.py         # moved + renamed (was phase-runner.py)
│       ├── summarize_round.py      # moved + renamed
│       ├── update_progress.py      # moved + renamed
│       ├── error_guidance.py       # moved
│       ├── recovery.py             # moved
│       ├── gates/                  # moved + modularized (PR-18)
│       │   ├── __init__.py
│       │   ├── cli.py
│       │   ├── shared.py
│       │   ├── g0.py ... g7.py
│       │   ├── g_transition.py
│       │   ├── g_dispatch.py
│       │   ├── g_reconcile.py
│       │   └── g4/
│       ├── dispatcher/             # moved + rewritten (PR-20)
│       │   ├── __init__.py
│       │   ├── cli.py
│       │   ├── executor.py
│       │   └── modes/
│       └── plugins/                # NEW: plugin manifest generator (PR-45)
│           ├── __init__.py
│           └── generate.py
├── tests/                          # ONLY test code
│   ├── conftest.py
│   ├── unit/ integration/ property/ benchmark/
│   ├── rounds/
│   ├── fixtures/
│   └── baselines/
├── skills/                         # unchanged (P0 will restructure)
├── docs/                           # unchanged
└── pyproject.toml                  # updated: src layout, entry points
```

`pyproject.toml` changes:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/shenbi"]
# No force-include of skills/ or docs/adr/ — those are repo assets,
# not wheel contents. If needed, ship as separate sdist only.

[project.scripts]
shenbi-validate = "shenbi.gates.cli:main"
shenbi-dispatch = "shenbi.dispatcher.cli:main"
shenbi-score = "shenbi.scoring:main"
shenbi-summarize = "shenbi.summarize_round:main"
shenbi-progress = "shenbi.update_progress:main"
shenbi-phase = "shenbi.phase_runner:main"
shenbi-generate-plugins = "shenbi.plugins.generate:main"

[tool.coverage.run]
branch = true
source = ["src/shenbi"]   # was: ["tests"]

[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration", "tests/property", "tests/benchmark"]
# Already correct, but now actually means "tests/" is only tests.
```

## Components (PRs)

### PR-18: src/shenbi/ layout migration

**Pre-migration audit**: Run grep to enumerate all references that need updating:

```bash
# All Python imports of tests.* modules
grep -rn "from tests\." --include='*.py' .
grep -rn "import tests\." --include='*.py' .

# All path references in shell scripts
grep -rn "tests/validate-gate\|tests/scoring\|tests/dispatch" --include='*.sh' .

# All path references in markdown (docs, agent skills)
grep -rn "tests/validate-gate\|tests/scoring\|tests/dispatch" --include='*.md' .

# All path references in plugin manifests
grep -rn "tests/" .claude-plugin/ .codex-plugin/ .cursor-plugin/ .opencode/

# Multi-agent entry files
grep -n "tests/" CLAUDE.md AGENTS.md GEMINI.md
```

Capture all matches to `tests/baselines/src-migration-references.txt` for
use as a checklist.

**Migration steps**:

1. Create `src/shenbi/__init__.py` with version and minimal public API.
2. Move `tests/exceptions.py` → `src/shenbi/exceptions.py` (no rename).
3. Move `tests/logging.py` → `src/shenbi/logging.py` (no rename).
4. Move `tests/error_guidance.py` → `src/shenbi/error_guidance.py`.
5. Move `tests/recovery.py` → `src/shenbi/recovery.py`.
6. Move + rename hyphenated files:
   - `tests/phase-runner.py` → `src/shenbi/phase_runner.py`
   - `tests/summarize-round.py` → `src/shenbi/summarize_round.py`
   - `tests/update-progress.py` → `src/shenbi/update_progress.py`
   - `tests/dispatch-subagent.sh` → leave in place (PR-20 handles)
   - `tests/validate-gate.py` → leave in place (PR-18 handles)
7. Update all imports per the audit checklist.
8. Update `pyproject.toml`: `[tool.hatch.build.targets.wheel]` → `packages = ["src/shenbi"]`.
9. Add `[project.scripts]` entries.
10. Update `pytest.ini_options` and `coverage.run.source`.
11. Run full test suite to verify.

**Note on PR-18 / PR-19 / PR-20 dependency**: PR-18 only moves the "easy" files
(exceptions, logging, error_guidance, recovery, phase_runner, summarize_round,
update_progress, scoring). `validate-gate.py` moves during PR-19 (modularization)
and `dispatch-subagent.sh` moves during PR-20 (Python rewrite), because both
require modularization / rewrite, not just relocation.

**Acceptance**:

- [ ] `src/shenbi/` directory exists with at least 7 modules
- [ ] `tests/` directory contains only: `conftest.py`, test subdirs, data dirs
      (`fixtures/`, `rounds/`, `baselines/`), and the two files explicitly
      deferred to PR-19 / PR-20 (`validate-gate.py`, `dispatch-subagent.sh`)
- [ ] `python -c "import shenbi; print(shenbi.__version__)"` works after
      `uv sync`
- [ ] All 7 entry points (`shenbi-validate`, etc.) work after `uv sync`
- [ ] `pytest` collection still works; no test fails due to import path
- [ ] `uv build --wheel` produces a wheel containing only `src/shenbi/`
      (verify with `unzip -l dist/*.whl`)
- [ ] Zero references to `tests.exceptions`, `tests.logging`, etc. in
      tracked files (excluding archived rounds and ADRs)
- [ ] `AGENTS.md`, `GEMINI.md`, `CLAUDE.md` updated to reference new paths

### PR-47: Remove `force-include` from wheel build

Per the user directive "不考虑开发成本", this is **required** in P-1.E, not
optional. The `force-include` block embeds repo assets (skills, ADRs) in
the wheel, conflating "installable runtime" with "repo documentation".
Mandatory cleanup.

Currently `pyproject.toml:54-56`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"skills/" = "skills/"
"docs/adr/" = "docs/adr/"
```

This bundles 76 skill files + 10 ADR files into the wheel. After src layout
migration, the wheel should contain only `src/shenbi/`. Skills and ADRs are
repo assets, not installable artifacts.

If downstream consumers need skills at runtime, they should clone the repo,
not pip-install. If they need to read ADRs, point them to the docs site.

**Acceptance**:

- [ ] `force-include` block removed from `pyproject.toml`
- [ ] `uv build --wheel` produces wheel < 100KB
- [ ] Document in `CONTRIBUTING.md` that skills are not pip-installable

## Risks

| Risk | Mitigation |
|------|------------|
| Migration breaks downstream agent plugins that hardcode `tests/scoring.py` paths | Pre-migration audit (step 1) catches all references; update plugins in same PR |
| Hidden dynamic imports (`importlib.import_module("tests.scoring")`) | grep for `importlib` usage; run full test suite |
| Coverage drops during migration because new paths not yet measured | Update `[tool.coverage.run].source` in same commit |
| Wheel size shrinks dramatically, breaking some external automation that expects `skills/` in installed package | Audit external consumers; if any exist, provide migration guide |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | `py.typed` marker for PEP 561? | **Yes, add in PR-18.** | PEP 561 standard for shipping type information. Without `py.typed`, downstream consumers can't benefit from our type annotations even when running mypy. Industry standard for any typed Python package. |
| 2 | `shenbi[full]` extra with skills data? | **No.** | Skills are not pip-installable data; they're prose + scripts that require the full repo context (agent plugin configs, fixtures, etc.). Users who want skills should `git clone`. Documented in `CONTRIBUTING.md` and `README.md`. |
| 3 | `phase_runner` vs `phase-runner` module name? | **`phase_runner` (underscore).** | Python module names cannot contain hyphens (PEP 8 §4.4 "Package and Module Names"). The rename from `phase-runner.py` to `phase_runner.py` is mandated by Python syntax, not a stylistic choice. |
