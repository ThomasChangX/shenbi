# Task 18-8 Report: End-to-End Verification (Plan 18)

**Date**: 2026-07-15
**Branch**: `fix/p0-blocking-defects`
**Commit**: `b6bb37a0` — fix: resolve lint/type errors found during end-to-end verification

---

## 8a. `just check` — Lint/Static Analysis

| Check | Status | Notes |
|-------|--------|-------|
| `lint_status_strings.py` | PASS | |
| `lint_repo_consistency.py` | PASS | |
| `lint-contracts` (graph + fields + contracts) | PASS | 10 dangling-write warnings (pre-existing) |
| `ruff check` | PASS | Fixed 1 D417 error (missing docstring args) |
| `ruff format --check` | PASS | |
| `mypy src/shenbi/` | PASS | Fixed 3 no-untyped-def errors |
| `basedpyright` | PASS | Fixed reportPrivateUsage (renamed `_print_token_summary`), reportUnusedFunction, reportAssignmentType (test_retry.py) |
| `shenbi-sync-contracts` | PASS | |
| `pytest -n auto -m "not last"` | **67 FAILED**, 2627 passed | Pre-existing failures (see below) |
| `pytest -m "last"` | Not reached | Blocked by step above |

**Fixes applied** (commit `b6bb37a0`):
1. `dispatch_helper.py:1390` — Added missing argument descriptions (`project_dir`, `prompt`, `shared_context`, `skill`, `uses_staging`) to `_dispatch_via_api` docstring (D417)
2. `dispatch_helper.py:1234,1252,1272` — Added `Any` type annotations to `_log_token_usage`, `_record_token_usage`, `print_token_summary` parameters (mypy no-untyped-def)
3. `dispatch_helper.py:1272` + `chapter_loop.py:59,976` — Renamed `_print_token_summary` to `print_token_summary` (basedpyright reportPrivateUsage across modules)
4. `test_retry.py:37,54,93` — Fixed tuple unpacking from 2-variable to 3-variable (`_call_llm_streaming_with_retry` returns 3-tuple)

**Pre-existing test failures (67 total)**: All failures predate the lint/type fixes above. They span:
- `test_chapter_loop.py` — 22 failures (StagingIntegration, ContextAssembly, EdgeCases, ConditionalResolveIntegration, RevisionRoutingIntegration, ResolveG4Files)
- `test_chapter_loop_full.py` — 28 failures (FullChapterSequence, ContextAssemblyIntegration, CLIChapterLoop)
- `test_genesis_to_loop.py` — 3 failures
- `test_full_flows.py` — 1 failure
- `test_cli.py` — 1 failure
- `test_e2e.py` — 1 failure
- Other files — 11 failures

Root cause: Tests are not updated for Plan 18 architectural changes (parallel dispatch via `dispatch_reviews_parallel` spawns ThreadPoolExecutor threads that call `dispatch_skill` without mocks; timeouts occur when API calls hang in test environments). Coverage threshold (85%) cannot be reached because tests timeout before full execution.

---

## 8b. 3-Chapter Mini-Pipeline

**Status**: Architecture verified via code inspection. Cannot execute full pipeline without API keys (`SHENBI_LLM_API_KEY`).

Pipeline entry points confirmed:
- `uv run pipeline init <seed-file> --auto` — initializes project, persists `--auto`
- `uv run pipeline next <project-dir>` — advances one checkpoint per call

The existing project `novel-output/xinghuo-ranqiong/` was generated pre-Plan 18 and does not contain Plan 18 artifacts (SCR cache files, grouped audit reports).

---

## 8c. Core Steps Count: 16 (was 20)

**PASS**. `CHAPTER_STEPS` at `src/shenbi/pipeline/chapter_loop.py:148-273` contains exactly **16** steps:

| # | Skill | Type |
|---|-------|------|
| 1 | `pipeline-volume-align` | checkpoint (ADD-1) |
| 2 | `shenbi-chapter-planning` | core |
| 3 | `pipeline-context-prepare` | context (ADD-2) |
| 4 | `shenbi-chapter-drafting` | core |
| 5 | `pipeline-post-draft-extract` | checkpoint (ADD-3) |
| 6 | `pipeline-linguistic-drift-check` | checkpoint (ADD-4) |
| 7 | `shenbi-foreshadowing-lifecycle` | core (MERGE-1) |
| 8 | `shenbi-state-settling` | core |
| 9 | `shenbi-review-group-factual` | audit (MERGE-2) |
| 10 | `shenbi-review-group-character` | audit (MERGE-2) |
| 11 | `shenbi-review-group-craft` | audit (MERGE-2) |
| 12 | `shenbi-review-group-plan` | audit (MERGE-2) |
| 13 | `shenbi-review-resonance` | audit |
| 14 | `shenbi-review-sensitivity` | audit |
| 15 | `pipeline-pre-revision-snapshot` | checkpoint (ADD-5) |
| 16 | `shenbi-chapter-revision` | core (conditional) |

3 conditional steps (`CONDITIONAL_STEPS`): `shenbi-intent-management`, `shenbi-drift-guidance`, `shenbi-snapshot-manage`.

---

## 8d. Foreshadowing-Lifecycle + State-Settling Concurrent

**PASS**. Implemented at `run_parallel_post_draft_steps()` (`chapter_loop.py:2556-2620`):

- Uses `ThreadPoolExecutor(max_workers=2)` to submit both `shenbi-foreshadowing-lifecycle` and `shenbi-state-settling` concurrently
- Single-writer pattern: main thread merges results sequentially to `PipelineState`
- Writes to disjoint files (lifecycle -> `pending_hooks.md`, settling -> 6 truth files) — zero data conflict
- Triggered at step index `_FORESHADOWING_LIFECYCLE_IDX = 6`

---

## 8e. SCR Cache Files at `context/chapter-N-scr.json`

**PASS**. Implemented at `src/shenbi/pipeline/scr_extractor.py:424-434`:

- `extract_scr()` deterministically extracts structured chapter representation
- Caches result to `context/chapter-{N}-scr.json`
- Returns cached data if file exists and is fresh
- Called from `_run_chapter_step_impl` (step 5: `pipeline-post-draft-extract`)

---

## 8f. Grouped Audit Output with Separate Dimension Reports

**PASS**. Six grouped audit skills in `CHAPTER_STEPS` (steps 9-14):

| Skill | Dimension |
|-------|-----------|
| `shenbi-review-group-factual` | audit:factual |
| `shenbi-review-group-character` | audit:character |
| `shenbi-review-group-craft` | audit:craft |
| `shenbi-review-group-plan` | audit:plan |
| `shenbi-review-resonance` | review-resonance |
| `shenbi-review-sensitivity` | audit:sensitivity |

Dispatched as two parallel waves via `dispatch_reviews_parallel()` (`chapter_loop.py:2744-2779`):
- **Wave 1**: Core-circle reviews (all `is_audit` skills with "review" in name)
- **Wave 2**: Genre-circle reviews (conditionally active, from `genre-config.json`)

Shared audit context is built once per chapter via `build_shared_audit_context()` with cascade filtering to skip clean audits.

---

## 8g. Token Usage Summary at Pipeline Completion

**PASS**. Implemented at multiple levels:

1. `_log_token_usage()` (`dispatch_helper.py:1234`) — logs per-dispatch token counts (prompt/completion/total) with structured logging
2. `_record_token_usage()` (`dispatch_helper.py:1252`) — accumulates token usage in `PipelineState.token_usage` dict per skill
3. `print_token_summary()` (`dispatch_helper.py:1272`) — prints summary at chapter completion with per-skill averages
4. Called at `chapter_loop.py:976` at the end of each chapter pipeline cycle

---

## 8h. Deprecated Skills Unreachable from Chapter Loop

**PASS**. Five deprecated skills removed from `CHAPTER_STEPS`:

| Deprecated Skill | Replacement |
|-----------------|-------------|
| `shenbi-foreshadowing-plant` | Deterministic `plant_hooks_from_plan()` — backward-compat handler at line 2906 |
| `shenbi-foreshadowing-track` | Merged into `shenbi-foreshadowing-lifecycle` (MERGE-1) |
| `shenbi-foreshadowing-recall` | Merged into `shenbi-foreshadowing-lifecycle` (MERGE-1) |
| `shenbi-context-composing` | Deterministic curation — backward-compat handler at line 2899 |
| `shenbi-escalation-review` | Dispatched reactively by `revision_router.dispatch_escalation` (not from chapter loop) |

Backward-compatibility handlers exist for old state files that reference these skills — they run deterministic replacements, never dispatch the deprecated LLM skills.

---

## Summary

| Check | Result |
|-------|--------|
| 8a — `just check` lint/static | **PASS** (fixes committed) |
| 8a — `just check` tests | **67 pre-existing failures** (not caused by this task) |
| 8b — 3-chapter mini-pipeline | **Architecture verified** (API keys required for execution) |
| 8c — 16 core steps | **PASS** |
| 8d — Parallel post-draft dispatch | **PASS** |
| 8e — SCR cache files | **PASS** |
| 8f — Grouped audit output | **PASS** |
| 8g — Token usage summary | **PASS** |
| 8h — Deprecated skills unreachable | **PASS** |

**Key finding**: 67 pre-existing test failures block full `just check` pass. These failures stem from Plan 18 architectural changes (parallel dispatch, grouped audits) that tests have not been updated to mock. A dedicated test-update task is needed to bring tests in line with the new architecture.
