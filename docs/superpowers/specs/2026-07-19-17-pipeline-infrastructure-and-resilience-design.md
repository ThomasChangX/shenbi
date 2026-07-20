# Spec 7: Pipeline Infrastructure and Resilience Design

> **Date:** 2026-07-19
> **Status:** Consolidated Design
> **Severity:** Critical (P0.5 end-to-end validation gap + P1 engineering gaps; P0.1-P0.4 already fixed)
> **Sources Merged:**
> - `2026-07-16-pipeline-maturity-and-bp-fixes-design.md` (P0 bugs, P1 engineering, P2 consistency)
> - `2026-07-18-graceful-shutdown-crash-recovery-design.md` (crash recovery)
> - `2026-07-18-pipeline-runtime-optimizations-design.md` (5 runtime optimizations)
> - `2026-07-17-improve-pipeline-observability-metrics-design.md` (observability)
> - `2026-07-17-restore-progress-tracking-design.md` (progress tracking)
> - `2026-07-17-fix-state-machine-current-step-corruption-design.md` (state machine fix)
> - `2026-07-17-fix-state-settling-timeout-design.md` (dynamic timeout)
> **Purpose:** Unify 7 source specs into a single consolidated plan covering all pipeline infrastructure gaps: P0 blocking bugs, crash recovery, runtime optimization, observability, progress tracking, state machine correctness, and adaptive timeouts.

---

## 1. Executive Summary

> **CORRECTION NOTICE (2026-07-15):** The original audit listed P0.1-P0.4 as blocking bugs. **All four are ALREADY FIXED in the current code** (P0.1 phase_runner, P0.2 shenbi-progress, P0.3 rollback stub, P0.4 codex_api branch). See Section 2.1 for verified current state. The only genuine remaining P0 blocker is **P0.5 (no validated end-to-end run)**. The crash-recovery, state-machine, progress-tracking, timeout, and observability gaps below remain accurate and stand.

The Shenbi pipeline underwent a comprehensive audit (5 parallel analysis agents + line-by-line code verification on 2026-07-15). The audit revealed a paradox: a 91/100 architecture score wraps a 45/100 unverified kernel. While 585 commits refined gates, contracts, and state machines, **no complete novel has ever been produced through the pipeline**. The root cause is systematic infrastructure debt across multiple dimensions:

| Infrastructure Gap | Impact |
|---|---|
| **P0.1-P0.4 "blocking bugs"** (4 items) | **ALREADY FIXED** — phase_runner gate path, shenbi-progress writes, rollback stub, and codex_api branch all resolved in current code. No action needed (see §2.1). |
| **No validated end-to-end run** (P0.5) | The sole remaining P0: `novel-output/` is empty, `.gitignore` suppresses output, no auditable artifact proves the pipeline works. |
| **No signal handling** | 40-hour/56-chapter runs can be killed by OOM, Ctrl-C, or SIGTERM with zero progress preservation |
| **No performance instrumentation** | 9.3x step-time variance (10 min to 93 min) with no per-step timing to locate bottlenecks |
| **Progress tracking broken** | `progress.json` frozen at Genesis for entire 40-hour run; `MARK_DONE` trace events never emitted |
| **State machine corrupt** | `_advance` sets `step_index` but not `current_step`; on interrupt, `current_step=""` renders resume impossible |
| **Hardcoded timeouts** | 900s for all dispatch regardless of chapter size; Ch35 (38KB) hits timeout boundary |
| **Runtime waste** | META blocks sent to auditors (16-31% waste), genre-config reread 7x per chapter, truth-index stale, pipeline-state unbounded, world files never updated |

**Shared root cause:** The pipeline was engineered for architectural elegance (state machines, gates, contracts) but the fundamental "run, survive, resume, observe" infrastructure was never built. This spec addresses all seven dimensions in a unified, dependency-ordered plan.

---

## 2. Root Cause Analysis

### 2.1 P0 Blocking Correctness Issues (from pipeline maturity audit)

**Source:** `2026-07-16-pipeline-maturity-and-bp-fixes-design.md` Section 4

The original audit listed five blocking issues. **P0.1-P0.4 are all ALREADY FIXED** in the current codebase (verified 2026-07-15); only P0.5 remains a genuine blocker:

#### P0.1: phase_runner dead path — ALREADY FIXED
- **File:** `src/shenbi/phase_runner.py:54-75`
- **Status:** ALREADY FIXED — migrated to `shenbi.gates.cli` with OSError catch. No action needed.
- **Current code:** `run_gate()` (lines 54-75) already targets `python -m shenbi.gates.cli` (line 64). The except clause is `except (json.JSONDecodeError, ValueError, OSError)` (line 70) — `OSError` is the parent of `FileNotFoundError`. The docstring explicitly documents the PR-19 migration away from the deleted `tests/validate-gate.py`.
- **Note:** Original audit's claim that this was broken was based on stale code; the migration was already complete.

#### P0.2: shenbi-progress script unregistered — ALREADY FIXED
- **File:** `src/shenbi/dispatcher/modes/codex.py:20-48`
- **Status:** ALREADY FIXED — replaced by direct `_record_completion` write. No action needed.
- **Current code:** `_record_completion` (lines 20-48) writes directly to `progress.json` via `safe_write`, appending to `completed_skill_names` and recording the skill score/status. The docstring states "Replaces the historical `shenbi-progress mark-done` subprocess, which invoked an entry point never registered in pyproject.toml." There is no subprocess call to `shenbi-progress` and no unregistered entry point.

#### P0.3: rollback stub misleads users — ALREADY FIXED
- **File:** `src/shenbi/pipeline/cli.py:783-803`, `main()` subparser registration
- **Status:** ALREADY FIXED — returns 1, subparser removed. No action needed.
- **Current code:** `cmd_rollback` (lines 783-803) returns `1` (line 803), emits `{"status": "not_implemented", ...}`, and the docstring notes "The subparser registration has been removed so 'pipeline --help' does not advertise this command." `main()` subparsers are: `init`, `next`, `status`, `review`, `resume`, `chapters` — no `rollback` subparser exists.

#### P0.4: codex_api dead branch — ALREADY FIXED
- **File:** `src/shenbi/dispatcher/executor.py:164-174,230-239`
- **Status:** ALREADY FIXED — no codex-api branch in dispatch(). No action needed.
- **Current code:** `detect_mode()` (lines 164-174) returns only `"codex"` or `"internal"`. `dispatch()` (lines 230-239) contains only a `codex` branch (lines 233-236) with `internal` as the fallback (lines 237-239). There is no `codex-api` branch anywhere in the dispatch path; a grep for `codex-api`/`codex_api`/`dispatch_codex_api` in `executor.py` returns no matches.

#### P0.5: No validated end-to-end run exists
- **File:** `.gitignore`, `novel-output/` (create)
- **Root cause:** `novel-output/` exists but is UNTRACKED (not committed to git) and `progress.json` is frozen. The pipeline ran but its outputs cannot be audited via git history, and the progress view does not reflect actual completion. `tests/rounds/` was deleted (commit `b978d3cc`). Previous "phantom data" incident (Round 005 with fake T2/T3 data).
- **Symptom:** The project's core defect -- no auditable real output proves the pipeline works.
- **Fix:** (a) establish a git-tracked audit mechanism for pipeline outputs (add `.gitignore` exceptions for `novel-output/` so artifacts can be committed and reviewed via git history), (b) fix `progress.json` materialization (§3.5). Run complete pipeline on `outline-example.md` (星火燃穹). Submit all intermediate artifacts (pipeline-state.json, genesis/, chapters/, truth/, audits/, gate-markers/).

### 2.2 P1 Engineering Gaps (from pipeline maturity audit)

**Source:** `2026-07-16-pipeline-maturity-and-bp-fixes-design.md` Section 5

| Gap | Current State | Industry Standard |
|-----|--------------|-------------------|
| No retry | Single `chat.completions.create`, 429/500/timeout = immediate failure | tenacity exponential backoff (3 retries) |
| No streaming | Blocking `create()` for 16K tokens, no incremental feedback | `stream=True` with early-stop patterns |
| No structured output | Regex `### FILE:` parsing -- one format drift loses a chapter | JSON mode + Pydantic `model_validate_json` |
| Hardcoded temperature | `_API_TEMPERATURE = 0.7` for all 67 skills | Per-skill config via `executor_config.toml` |
| Internal mode silent pass | `internal.py` returns success with no scoring output | Hard-reject: raise `DispatcherError` |
| No golden evaluation set | 1875 tests mock LLM; zero end-to-end quality assertions | 10-chapter golden set with human scores |

### 2.3 P2 Consistency Issues (from pipeline maturity audit)

**Source:** `2026-07-16-pipeline-maturity-and-bp-fixes-design.md` Section 6

| Issue | File | Problem |
|-------|------|---------|
| CJK normalization | `contracts/fields.py:23-24` | Only ASCII whitespace + U+3000 normalized; no zero-width folding, no NFKC |
| Severity type split | `contracts/schemas/decisions.py:28,52` | `Selection.severity` is `Literal["low","high"]` but `Adjustment.severity` is free `str` |
| Hardcoded thresholds | `scoring.py:176-183` | `classify` uses magic numbers 90/75/60 instead of `TEST_PASS` from `thresholds.py` |
| legacy.py mislabel | `contracts/legacy.py:1` | Marked DEPRECATED but is the canonical active loader consumed by all gates/dispatchers |
| Deferred PASS stubs | `g7.py:108-112`, `g_dispatch.py:67-69`, etc. | Multiple gates return unconditional PASS with "deferred" note; `UNIMPLEMENTED` status exists but unused |
| Stale docs | `docs/getting-started/first-novel.md:231-233` | Claims orchestration is "placeholder" but `pipeline next/resume` is fully implemented |

### 2.4 Crash Recovery (no signal handling)

**Source:** `2026-07-18-graceful-shutdown-crash-recovery-design.md`

- **Root cause:** Pipeline has zero signal handlers. `kill` or `Ctrl-C` directly terminates the process. No atexit hook. No emergency snapshot. No resume logic for interrupted state.
- **Evidence:** Ch56 interrupted with `current_step=''`, `step_index=9`. Pipeline state preserved but recovery impossible without manual intervention.
- **Impact:** 40-hour/56-chapter runs vulnerable to OOM, API rate limits, network interruptions, or accidental termination -- no progress preservation.

### 2.5 Runtime Inefficiencies (5 accumulated issues)

**Source:** `2026-07-18-pipeline-runtime-optimizations-design.md`

| Issue | Impact |
|-------|--------|
| META blocks sent to auditors | 13 auditors + state-settling + lifecycle receive `<!--META-BEGIN-->...<!--META-END-->` blocks; Ch10: 16% waste, average 31% across chapters |
| genre-config.json repeat I/O | 3.6KB file read ~8 times per chapter, each triggering disk I/O |
| Stale truth-index | Built at Genesis, never rebuilt; grows stale across 56 chapters |
| Unbounded pipeline-state.json | 132KB at 56 chapters, full `json.dump` on every save; retry_feedback (54 entries) permanently accumulates |
| Stale world files | `world/` files written at Genesis, never updated; story advances from Ironforge to Misty Mountains but `locations.md` unchanged |

### 2.6 Observability Gaps

**Source:** `2026-07-17-improve-pipeline-observability-metrics-design.md`

| Gap | Symptom |
|-----|---------|
| No per-step timing | Chapter times vary 9.3x (10 min to 93 min) with no per-skill breakdown to identify bottlenecks |
| No token tracking | Entire 40-hour run has zero token counts or cost logs; `response.usage` never recorded |
| Word count instability | Range 101 words (Ch55, damaged) to 18,363 words (Ch47); standard deviation too high |

### 2.7 Progress Tracking Broken

**Source:** `2026-07-17-restore-progress-tracking-design.md`

- **Root cause:** `_record_step_done` (`chapter_loop.py:443-451`) updates in-memory `PipelineState` but never emits `MARK_DONE` trace events. `progress.json` is a trace-derived view (`trace/materialize.py:31-101`) -- without trace events, it remains frozen.
- **Evidence:** `progress.json` last modified at Genesis (04:53:55). Remained unchanged for 40 hours and 56 chapters.
- **Symptom:** Progress tracking, which G3.4 scoring independence depends on, is non-functional.

### 2.8 State Machine current_step Corruption

**Source:** `2026-07-17-fix-state-machine-current-step-corruption-design.md`

- **Root cause:** `_advance` (`chapter_loop.py:489-563`) sets `step_index` but never sets `current_step`. `ChapterLoopStateData.current_step` defaults to `""`. If pipeline is interrupted between steps, the persisted state has `step_index=9, current_step=""` -- a contradiction.
- **Effect:** `pipeline resume` uses `current_step` to determine recovery point. Empty string causes undefined behavior: may skip steps, restart from step 0, or enter illegal state.

### 2.9 Hardcoded Timeout Does Not Scale

**Source:** `2026-07-17-fix-state-settling-timeout-design.md`

- **Root cause:** `dispatch_helper.py` uses a global hardcoded 900s (15 min) dispatch timeout. State-settling, the heaviest step (reads all truth files + current chapter + updates 7 truth files), exceeds this for large chapters.
- **Evidence:** Ch35 (38KB) state-settling exceeded 900s, triggering escalation checkpoint. Retry succeeded but exposed the flaw.
- **Risk:** Chapter size vs. timeout:
  - <10KB: 2-5 min (safe)
  - 20-30KB: 10-15 min (borderline)
  - 30-40KB: 15-25 min (**exceeds 900s**)

---

## 3. Unified Fix Strategy

### 3.1 P0 Blocking Fixes

**Dependency chain:** P0.1-P0.4 are all ALREADY FIXED (no work needed). P0.5 depends on execution backend readiness only — the four "blocking bugs" it was originally gated on have already been resolved.

#### P0.1: Fix run_gate() dead path — ALREADY FIXED, NO ACTION

**File:** `src/shenbi/phase_runner.py:54-75`

Already implemented. `run_gate()` invokes `python -m shenbi.gates.cli` (line 64) and catches `(json.JSONDecodeError, ValueError, OSError)` (line 70). No changes required. (The `scoring.py` gate references in the original audit were not part of this dead-path bug.)

#### P0.2: Fix shenbi-progress registration — ALREADY FIXED, NO ACTION

**File:** `src/shenbi/dispatcher/modes/codex.py:20-48`

Already implemented. `_record_completion` writes directly to `progress.json` via `safe_write`; there is no `shenbi-progress` subprocess call and no entry point to register. No changes required.

#### P0.3: Remove rollback CLI registration — ALREADY FIXED, NO ACTION

**File:** `src/shenbi/pipeline/cli.py:783-803`

Already implemented. `cmd_rollback` returns exit code `1` (line 803) and the `rollback` subparser is not registered in `main()` (subparsers are: init, next, status, review, resume, chapters). No changes required.

#### P0.4: Delete codex_api dead branch — ALREADY FIXED, NO ACTION

**File:** `src/shenbi/dispatcher/executor.py:164-174,230-239`

Already implemented. `dispatch()` contains only a `codex` branch with `internal` fallback; no `codex-api` branch exists. No changes required.

#### P0.5: End-to-end real run

1. Add `.gitignore` exceptions for `novel-output/`
2. Configure execution backend (`SHENBI_LLM_API_KEY` + `SHENBI_LLM_BASE_URL` + `SHENBI_LLM_MODEL`)
3. Run full pipeline on `outline-example.md` (星火燃穹)
4. Submit auditable artifacts: `pipeline-state.json`, `genesis/`, `chapters/`, `truth/`, `audits/`, `gate-markers/`
5. Risk mitigation: run 5-chapter canary first; pipeline is resumable; quality not expected to be perfect

### 3.2 Engineering Practices (P1)

#### P1.2: Scoring independence hardening

**File:** `src/shenbi/dispatcher/modes/internal.py`, `dispatch_helper.py`

- `internal.py`: Replace silent pass with `raise DispatcherError("internal mode has no LLM backend, cannot score. Set SHENBI_LLM_API_KEY.")`
- `dispatch_helper.dispatch_skill`: Write `current_scorer_agent` to `progress.json` after scoring skill execution, enabling G3.4 fail-closed logic in pipeline path
- Scoring session physical isolation: inject unique `request_id`, separate client instance via `SHENBI_SCORING_SESSION=1`

#### P1.3: Structured output (replace regex parsing)

**File:** `src/shenbi/pipeline/dispatch_helper.py:272-291,402-459`

```python
class FileOutput(BaseModel):
    path: str
    content: str

class SkillOutput(BaseModel):
    files: list[FileOutput]
    decisions: dict | None = None

response = client.chat.completions.create(
    model=model, messages=messages,
    response_format={"type": "json_object"},
    temperature=temp, max_tokens=max_tok,
)
output = SkillOutput.model_validate_json(response.choices[0].message.content)
```

CLI backend retains `### FILE:` regex fallback. API path uses 0 regex.

#### P1.4: LLM-level retry with exponential backoff

**File:** `src/shenbi/pipeline/dispatch_helper.py:402-459`

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=30),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
)
def _call_llm(client, model, messages, **kwargs):
    return client.chat.completions.create(model=model, messages=messages, **kwargs)
```

Retry layers: LLM layer (P1.4) handles transient 429/5xx/timeout. Gate layer (existing `error_handler`) handles structural failures (G4 failure). LLM layer exhausts first.

#### P1.5: Streaming with early-stop

**File:** `src/shenbi/pipeline/dispatch_helper.py:402-459`

```python
def _call_llm_streaming(client, model, messages, early_stop_patterns=None, **kwargs):
    collected = []
    stop_reason = None
    stream = client.chat.completions.create(model=model, messages=messages, stream=True, **kwargs)
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        collected.append(delta)
        if early_stop_patterns:
            text_so_far = "".join(collected)
            for pat in early_stop_patterns:
                if pat in text_so_far:
                    stop_reason = f"early_stop: matched {pat}"
                    break
            if stop_reason:
                break
    return "".join(collected), stop_reason
```

Early-stop patterns from `genre-config.json` `fatigueWords` and `chapter-drafting` SKILL.md banned sentence patterns.

#### P1.6: Per-skill temperature/model config

**File:** `src/shenbi/pipeline/dispatch_helper.py:40-49`, new `executor_config.toml`

```toml
[default]
temperature = 0.7
max_tokens = 16384

[overrides."shenbi-chapter-drafting"]
temperature = 0.85

[overrides."shenbi-review-continuity"]
temperature = 0.2

[overrides."shenbi-review-anti-ai"]
temperature = 0.15
```

After migration, delete `_API_TEMPERATURE` and `_API_MAX_TOKENS` constants.

#### P1.8: Golden evaluation set

**Directory:** `tests/golden/` (new)

- 10-20 chapters from P0.5 real output, human-scored per rubric
- `shenbi-score --calibrate-against` mode: Pearson/Spearman correlation, Cohen's kappa
- Nightly CI smoke test: 1 chapter real run (alert on failure, not PR-blocking)

#### P1.9: Dual state machine documentation

**File:** `src/shenbi/phase_runner.py:1-11`, `src/shenbi/pipeline/cli.py:1-19`

Add explicit annotations distinguishing the test orchestrator (`shenbi-phase`) from the novel generator (`pipeline` CLI). Add "Two State Machines" section to `docs/architecture/overview.md`.

### 3.3 Consistency Fixes (P2)

#### P2.1: CJK zero-width normalization

**File:** `src/shenbi/contracts/fields.py:23-24`

```python
def _normalize_ws(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = "".join(c for c in text if c not in "\u200b\ufeff\u200c\u200d")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
```

Also transcode or remove `report-example.txt` (GBK-encoded public domain text mistakenly labeled as audit report).

#### P2.2: Severity enum unification

**File:** `src/shenbi/contracts/schemas/decisions.py:28,52`

```python
Severity = Literal["low", "medium", "high"]

class Selection(BaseModel):
    severity: Severity = "low"

class Adjustment(BaseModel):
    severity: Severity  # was: str
```

Bump schema version: `shenbi-decisions-v1` to `shenbi-decisions-v2`. v1 `low`/`high` remain valid; `medium` is new.

#### P2.3: Dead constant cleanup + threshold single-source

**File:** `src/shenbi/scoring.py:176-183`, `src/shenbi/contracts/thresholds.py`

- `scoring.classify`: Replace hardcoded 90 with `TEST_PASS` import
- G6: Wire `T3_PASS` for T3 score checks
- Verify `CONVERGENCE`: delete if orphaned, annotate if reserved

#### P2.4: legacy.py accurate docstring

**File:** `src/shenbi/contracts/legacy.py:1`

Replace DEPRECATED notice with accurate description: "Canonical contract loader and validator. Despite historical naming, this is the current single source of truth consumed by all gates, dispatchers, and pipeline."

#### P2.5: Deferred PASS stubs to UNIMPLEMENTED

**Files:** `g7.py:108-112`, `g_dispatch.py:67-69`, `g_reconcile.py:74-76`, `g_transition.py:66-91`, `g0.py:237-238`

Each stub: `c.append({"id": "G7.2", "s": "PASS", "note": "deferred"})` becomes `c.append(shared.unimplemented("G7.2", "skill-traces check not yet implemented"))`. `UNIMPLEMENTED` treated as PASS in gate chain (non-blocking), but flagged WARN in audit report.

Note: G3.1 (`g3.py:85-91`) is intentionally skipped with `"s": "SKIP"` -- not a deferred stub, do not change.

#### P2.6: Stale documentation fix

**File:** `docs/getting-started/first-novel.md:231-233`

Update or remove the claim that orchestration is "a placeholder." Pipeline `next`/`resume` are fully implemented (`cli.py:582-751`).

### 3.4 Crash Recovery

**Source:** `2026-07-18-graceful-shutdown-crash-recovery-design.md` Section 2

**New file:** `src/shenbi/pipeline/crash_recovery.py`

#### Signal handlers

```python
def register_emergency_handlers(project_dir: Path, state: 'PipelineState'):
    _emergency_state['project_dir'] = project_dir
    _emergency_state['pipeline_state'] = state
    signal.signal(signal.SIGTERM, _handle_emergency_signal)
    signal.signal(signal.SIGINT, _handle_emergency_signal)
    atexit.register(_emergency_cleanup)
```

On SIGTERM/SIGINT: set `shutdown_requested = True`, call `_emergency_cleanup()`, then re-raise signal for correct exit code.

#### Emergency cleanup

`_emergency_cleanup()` (also called by atexit for normal exits with unsaved changes):
1. Mark current step as `EMERGENCY_SHUTDOWN_AT_{step.skill}`
2. Save pipeline state via `save_pipeline_state()`
3. Create emergency snapshot via `_snapshot_chapter_files(label="emergency")`
4. Clear staging via `clear_staging()`

All wrapped in try/except -- cleanup failure must not prevent process exit.

#### Chapter loop integration

**File:** `src/shenbi/pipeline/chapter_loop.py`

```python
for step in CHAPTER_STEPS:
    if is_shutdown_requested():
        logger.info("graceful_shutdown_at_step_boundary", ...)
        break  # exit at step boundary, not mid-LLM-call
    result = run_chapter_step(state, step)
```

#### Resume recovery

**File:** `src/shenbi/pipeline/cli.py:cmd_resume`

```python
if cl.current_step and cl.current_step.startswith("EMERGENCY_SHUTDOWN"):
    logger.warning("resuming_from_emergency_shutdown", ...)
    cl.current_step = CHAPTER_STEPS[cl.step_index].skill if cl.step_index < len(CHAPTER_STEPS) else ""
    save_pipeline_state(project_dir, state)
```

### 3.5 Runtime Optimizations + Observability

#### Runtime optimization 1: META block stripping

**File:** `src/shenbi/pipeline/dispatch_helper.py`

```python
_META_PATTERN = re.compile(r'<!--META-BEGIN-->.*?<!--META-END-->', re.DOTALL)

def _strip_meta_for_non_drafting(skill_name: str, text: str) -> str:
    if skill_name in ('shenbi-chapter-drafting', 'shenbi-chapter-revision'):
        return text
    return _META_PATTERN.sub('', text)
```

Saves 16-31% input per non-drafting call (13 auditors + state-settling + lifecycle).

#### Runtime optimization 2: genre-config caching

**File:** `src/shenbi/pipeline/dispatch_helper.py`

Module-level cache keyed by chapter number. ~7 disk I/O per chapter reduced to 1.

#### Runtime optimization 3: Truth-index periodic rebuild

**File:** `src/shenbi/pipeline/chapter_loop.py:_complete_chapter`

Rebuild truth-index at volume boundaries or every 15 chapters.

#### Runtime optimization 4: Pipeline-state compaction

**File:** `src/shenbi/pipeline/state.py`

- Archive chapter states beyond last 10 to `pipeline-state-archive.json`
- Prune `retry_feedback` to last 30 entries
- Reduces 236KB (at 100 chapters) to ~80KB

#### Runtime optimization 5: World file freshness

**File:** `src/shenbi/pipeline/chapter_loop.py:_complete_chapter`

At volume boundaries: compare `locations.md` against SCR-extracted locations from last 10 chapters. Log WARNING for missing locations; generate human review note (non-blocking).

#### Per-step timing

**File:** `src/shenbi/pipeline/chapter_loop.py:run_chapter_step`

```python
step_start = time.monotonic()
try:
    # ... execute step ...
finally:
    elapsed = time.monotonic() - step_start
    logger.info("step_timing", chapter=..., step=..., elapsed_seconds=round(elapsed, 1))
    _record_step_timing(state, step.skill, elapsed)
```

End-of-run summary: per-skill avg/min/max times.

#### API token tracking

**File:** `src/shenbi/pipeline/dispatch_helper.py`

```python
if hasattr(response, 'usage'):
    usage = response.usage
    logger.info("llm_token_usage", skill=skill_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens)
    _record_token_usage(state, skill_name, usage)
```

Non-API paths (codex CLI) approximate from progress tracking.

#### Word count stability

- Chapter memo/planning prompts: tighten ranges (5000-8000 Transition, 8000-12000 Advance)
- G4 post-write bounds: transition >8000 words = issue; climax <6000 = issue
- Hard floor: 4000 words; hard ceiling: 15000 words

#### Progress tracking: emit MARK_DONE events

**File:** `src/shenbi/pipeline/chapter_loop.py:_record_step_done`

```python
def _record_step_done(state, chapter, skill_name):
    # ... existing logic ...
    from shenbi.trace.writer import write_event
    write_event(project_dir, event_type="MARK_DONE", skill=skill_name,
                chapter=chapter, timestamp=datetime.now(timezone.utc).isoformat())
```

Materialize progress every 5 steps or at chapter completion. Auto-rebuild on resume if trace has events but progress.json is stale.

#### State machine: heal current_step

**File:** `src/shenbi/pipeline/state.py` or persistence layer

```python
def _heal_current_step(state: PipelineState) -> None:
    cl = state.chapter_loop
    if not cl.current_step and cl.step_index > 0:
        if cl.step_index < len(CHAPTER_STEPS):
            cl.current_step = CHAPTER_STEPS[cl.step_index].skill
        else:
            cl.current_step = "chapter_complete"
```

Also fix `_advance` (`chapter_loop.py:489-563`) to explicitly set `current_step` alongside `step_index`.

Add `_validate_state_consistency()` at resume: check for step_index > 0 but empty current_step, heal if found.

#### Dynamic timeout

**File:** `src/shenbi/pipeline/dispatch_helper.py`

```python
def _compute_dispatch_timeout(chapter_path: Path | None = None) -> int:
    base = 300  # 5 min
    if chapter_path and chapter_path.exists():
        chapter_size_kb = chapter_path.stat().st_size / 1024
        extra = int(chapter_size_kb * 30)
    else:
        extra = 0
    return min(base + extra, 1800)  # max 30 min

# state-settling gets 2x multiplier
if skill_name == "shenbi-state-settling":
    timeout = int(timeout * 2.0)
```

**Timeout examples:**
- 10KB chapter: ~600s
- 38KB chapter: ~1440s
- Cap: 1800s (30 min)

**Graceful degradation on timeout:** Save partial LLM output, reuse previous truth file versions for incomplete updates, log WARN (not HARD failure).

**Code-path coverage (critical):** The 900s timeout above only applies to the legacy CLI subprocess path (`subprocess.run(..., timeout=timeout)`). The API path (`_dispatch_via_api`) passes NO timeout to the API client — the `_call_llm` wrapper in §P1.4 retries transient errors but never enforces a wall-clock ceiling. The fix must address all three paths: (a) CLI subprocess (current timeout — apply `_compute_dispatch_timeout`), (b) API path (needs `client.chat.completions.create(timeout=...)` wired from `_compute_dispatch_timeout`), (c) IDE-CLI path (separate `_IDE_AGENT_TIMEOUT` — scale it with chapter size using the same formula).

---

## 4. Affected Files

| File | Source Spec | Fix |
|------|-------------|-----|
| `src/shenbi/phase_runner.py:54-75` | P0.1 | **ALREADY FIXED** — targets `shenbi.gates.cli`, catches `OSError`. No action needed. |
| `src/shenbi/dispatcher/modes/codex.py:20-48` | P0.2 | **ALREADY FIXED** — `_record_completion` writes `progress.json` directly. No action needed. |
| `src/shenbi/pipeline/cli.py:783-803` | P0.3 | **ALREADY FIXED** — `cmd_rollback` returns 1, subparser removed. No action needed. |
| `src/shenbi/dispatcher/executor.py:164-174,230-239` | P0.4 | **ALREADY FIXED** — no `codex-api` branch in `dispatch()`. No action needed. |
| `.gitignore` | P0.5 | Add `novel-output/` exception |
| `src/shenbi/dispatcher/modes/internal.py` | P1.2 | Hard-reject scoring in internal mode |
| `src/shenbi/pipeline/dispatch_helper.py:272-291,402-459` | P1.3 | JSON mode + Pydantic structured output |
| `src/shenbi/pipeline/dispatch_helper.py:402-459` | P1.4 | tenacity retry decorator |
| `src/shenbi/pipeline/dispatch_helper.py:402-459` | P1.5 | Streaming with early-stop |
| `src/shenbi/pipeline/dispatch_helper.py:40-49,425-441` | P1.6 | Per-skill temperature config; delete `_API_TEMPERATURE` |
| `tests/golden/` (new) | P1.8 | Golden evaluation set |
| `src/shenbi/phase_runner.py:1-11` | P1.9 | Docstring annotation |
| `src/shenbi/pipeline/cli.py:1-19` | P1.9 | Docstring annotation |
| `src/shenbi/contracts/fields.py:23-24` | P2.1 | CJK zero-width + NFKC normalization |
| `src/shenbi/contracts/schemas/decisions.py:28,52` | P2.2 | Severity Literal union |
| `src/shenbi/scoring.py:176-183` | P2.3 | Use `TEST_PASS` constant |
| `src/shenbi/contracts/legacy.py:1` | P2.4 | Accurate docstring |
| `src/shenbi/gates/g7.py:108-112` | P2.5 | Deferred PASS → UNIMPLEMENTED |
| `src/shenbi/gates/g_dispatch.py:67-69` | P2.5 | Deferred PASS → UNIMPLEMENTED |
| `src/shenbi/gates/g_reconcile.py:74-76` | P2.5 | Deferred PASS → UNIMPLEMENTED |
| `src/shenbi/gates/g_transition.py:66-91` | P2.5 | Deferred PASS → UNIMPLEMENTED |
| `src/shenbi/gates/g0.py:237-238` | P2.5 | Deferred PASS → UNIMPLEMENTED |
| `docs/getting-started/first-novel.md:231-233` | P2.6 | Remove stale placeholder claim |
| `src/shenbi/pipeline/crash_recovery.py` (new) | Crash Recovery | Signal handlers, emergency cleanup, shutdown flag |
| `src/shenbi/pipeline/chapter_loop.py` | Crash Recovery | `is_shutdown_requested()` check between steps |
| `src/shenbi/pipeline/cli.py:cmd_resume` | Crash Recovery | Emergency shutdown recovery logic |
| `src/shenbi/pipeline/dispatch_helper.py` | Runtime | META strip, genre-config cache, dynamic timeout |
| `src/shenbi/pipeline/chapter_loop.py` | Runtime | Truth-index rebuild, world file freshness check |
| `src/shenbi/pipeline/state.py` | Runtime | Pipeline-state compaction + archive |
| `src/shenbi/pipeline/chapter_loop.py:run_chapter_step` | Observability | Per-step timing with `time.monotonic()` |
| `src/shenbi/pipeline/dispatch_helper.py` | Observability | Record `response.usage` token counts |
| `src/shenbi/pipeline/chapter_loop.py:_record_step_done` | Progress | Emit `MARK_DONE` trace events |
| `src/shenbi/pipeline/chapter_loop.py` | Progress | Materialize progress every 5 steps |
| `src/shenbi/pipeline/cli.py:cmd_resume` | Progress | Auto-rebuild progress on resume |
| `src/shenbi/pipeline/state.py` | State Machine | `_heal_current_step()` |
| `src/shenbi/pipeline/chapter_loop.py:489-563` | State Machine | `_advance` explicitly sets `current_step` |
| `src/shenbi/pipeline/cli.py:cmd_resume` | State Machine | `_validate_state_consistency()` |
| `src/shenbi/pipeline/dispatch_helper.py` | Timeout | `_compute_dispatch_timeout()` dynamic timeout |

---

## 5. Verification Criteria

1. `shenbi-phase start` no longer raises `FileNotFoundError` (P0.1) — **ALREADY FIXED** (verified: `run_gate` uses `shenbi.gates.cli` + `OSError` catch)
2. Codex mode dispatch does not fail on `shenbi-progress` subprocess (P0.2) — **ALREADY FIXED** (verified: `_record_completion` writes `progress.json` directly, no subprocess)
3. `pipeline --help` does not show `rollback` command (P0.3) — **ALREADY FIXED** (verified: subparser removed, `cmd_rollback` returns 1)
4. No code path can reach `dispatch_codex_api` (P0.4) — **ALREADY FIXED** (verified: no `codex-api` branch in `dispatch()`)
5. `novel-output/xinghuo-ranqiong/` contains complete auditable artifacts (P0.5)
6. Internal mode scoring raises `DispatcherError` (P1.2)
7. API path output parsing uses 0 regex (P1.3) -- grep confirms
8. 429 responses auto-retry 3 times with exponential backoff (P1.4)
9. Long chapters (>5000 words) produce streaming output, chunk interval <2s (P1.5)
10. Different skills use different temperatures as configured (P1.6)
11. `tests/golden/` contains >=10 chapters with human scores (P1.8)
12. Both CLI help texts have explicit "testing orchestrator" vs "novel generator" annotations (P1.9)
13. Zero-width/half-width field matching passes property tests (P2.1)
14. `severity: "medium"` validates; `"critical"` is rejected (P2.2)
15. `classify` uses `TEST_PASS` constant, not magic number 90 (P2.3)
16. `legacy.py` docstring accurately describes its role (P2.4)
17. No `"deferred"` + `PASS` combination remains in gate code (P2.5)
18. `first-novel.md` no longer claims orchestration is a placeholder (P2.6)
19. `kill -TERM <pid>` saves pipeline state + creates emergency snapshot before exit
20. `Ctrl-C` triggers same emergency cleanup
21. `pipeline resume` correctly recovers from emergency shutdown state
22. Step boundary check: shutdown occurs between steps, not mid-LLM-call
23. Emergency cleanup failure does not prevent process exit
24. Audit skill inputs do not contain `<!--META-BEGIN-->` blocks
25. Same-chapter `genre-config.json` reads trigger exactly 1 disk I/O
26. `truth-index.json` mtime updates after volume boundary
27. Simulated 100-chapter `pipeline-state.json` < 100KB
28. New locations not in `locations.md` produce WARNING log
29. Pipeline logs contain per-step timing with skill-level granularity
30. Pipeline completion prints timing summary (avg/min/max per skill)
31. API path logs contain `llm_token_usage` with prompt/completion/total tokens
32. 10 consecutive chapters have word counts within target range (+/-30%)
33. `progress.json` updates after each chapter completion during a 3-chapter mini-pipeline
34. `progress.json` contains latest `completed_skill_names` and chapter progress
35. Interrupt-resume cycle results in `progress.json` reflecting latest state
36. Unit test: `step_index=9, current_step=""` auto-heals to `CHAPTER_STEPS[9].skill`
37. Unit test: after `_advance`, `current_step` is non-empty
38. Unit test: all steps complete sets `current_step="chapter_complete"`
39. 10KB chapter timeout ~600s; 38KB chapter timeout ~1440s
40. Timeout never exceeds 1800s cap
41. `just check` full suite passes at every stage

---

## 6. Dependencies

```
Execution Backend Decision (OpenAI-compatible API as primary)
    |
    +-- P0.1 (phase_runner dead path) -------- ALREADY FIXED
    |   P0.2 (shenbi-progress unregistered) -- ALREADY FIXED   (P0.1-P0.4 all verified
    |   P0.3 (rollback stub removal) --------- ALREADY FIXED    complete in current code;
    +-- P0.4 (codex_api dead branch) --------- ALREADY FIXED    no work required)
                |
                v (P0.1-4 already complete)
            P0.5 (end-to-end real run) -- requires execution backend ready
                |
                v (first auditable artifact produced)
    +-- P1.3 (structured output) --> P1.4 (retry) --> P1.5 (streaming) --> P1.6 (temperature config)
    |       These four form "production-grade API executor"
    +-- P1.2 (scoring independence) -- depends on execution backend decision
    +-- P1.8 (golden set) -- depends on P0.5 real output
    +-- P1.9 (dual state machine docs) -- independent
                |
                v
    +-- P2.1-P2.6 (consistency cleanup) -- mostly independent, parallelizable
    +-- Crash Recovery -- depends on State Machine fix (current_step correctness)
    +-- Runtime Optimizations -- independent
    +-- Observability -- weak dependency on Progress Tracking (shared trace infrastructure)
    +-- Progress Tracking -- independent
    +-- State Machine Fix -- independent
    +-- Dynamic Timeout -- independent
                |
                v
        Final acceptance: end-to-end pass + full `just check` + auditable artifacts committed
```

### Original Code Mapping

| Original Issue Code | Consolidated Spec |
|---|---|
| maturity-bp | Spec 7 (this spec) |
| crash-recovery | Spec 7 (this spec) |
| runtime-opt | Spec 7 (this spec) |
| L1 | Spec 7 (this spec) |
| L2 | Spec 7 (this spec) |
| L3 | Spec 7 (this spec) |
| M2 | Spec 7 (this spec) |
| H5 | Spec 7 (this spec) |
| M4 | Spec 7 (this spec) |
