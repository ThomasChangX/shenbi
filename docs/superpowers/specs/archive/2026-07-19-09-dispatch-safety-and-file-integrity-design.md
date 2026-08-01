# Spec 3: Dispatch Safety and File Integrity Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical
> **Consolidated from:**
> - `2026-07-17-fix-revision-overwrite-chapter-content-design.md` (C1)
> - `2026-07-17-fix-seven-chapters-zero-prose-design.md`
> - `2026-07-17-fix-staging-residue-cleanup-design.md` (H4)
> - `2026-07-17-fix-snapshot-coverage-gaps-design.md` (M3)
> - `2026-07-17-fix-snapshot-bloat-lockfile-budget-design.md`

---

## 1. Executive Summary

The dispatch system's output writing path (`dispatch_helper.py:_write_parsed_outputs`) unconditionally overwrites target files with no content-size guard, no pre-write backup, and no staging cleanup in auto mode. This has caused 5 chapters (8.9%) to have their novel prose permanently replaced by revision metadata summaries. An additional 2 chapters contain severely degraded prose. The snapshot system -- intended as a safety net -- has coverage gaps (Ch1-4 and Ch56 have no snapshots) and stores bloated full-file copies (18x chapter size) including audit reports. Staging residue accumulates to 119 files (1.2MB) because `clear_staging()` is never called in auto-commit code paths. Lockfile permissions are wrong (0755 instead of 0644), and adjacent-chapter decision budgets are copied without recalculation.

**Shared root cause:** `_write_parsed_outputs` at `dispatch_helper.py:294-323` calls `safe_write(path, content)` at line 316 with zero guards. The method treats all output paths equally -- chapter body prose, revision metadata, audit reports -- and has no awareness of what constitutes a valid content size for each file type. The auto-commit path in `chapter_loop.py` (around lines 516-545) calls `commit_staging()` but never follows up with `clear_staging()`. Snapshot generation starts at step 19 and has no initialization hook for early chapters.

---

## 2. Root Cause Analysis (Per-Source-Spec Breakdown)

### 2.1 Revision Overwrite of Chapter Content (C1, consumed into this spec)

**Discovery:** 5/56 chapters (8.9%) have their `chapters/chapter-N.md` containing revision metadata instead of novel prose:

| Chapter | File Size | Content Type | Snapshot Status |
|---------|-----------|-------------|-----------------|
| Ch2 | 916 bytes | "All three files have been output. Here's a summary of the revision..." | No snapshot |
| Ch9 | 367 bytes | "第9章修订结论: Auto-skip（无修订）" | Snapshot also corrupted |
| Ch12 | 1,340 bytes | "The revision is complete. Here's a summary..." | Snapshot also corrupted |
| Ch44 | 1,199 bytes | "All three output files have been produced..." | Snapshot also corrupted |
| Ch55 | 101 bytes | "Chapter content unchanged -- no revision needed." | Snapshot also corrupted |

**Critical fact: Ch2 has no snapshot -> prose is permanently lost.**

**Root cause chain:**

```
shenbi-chapter-revision no-op route
  -> LLM outputs summary to ### FILE: chapters/chapter-N.md
    -> _write_parsed_outputs unconditionally overwrites via safe_write
      -> Original prose permanently lost
```

Three systemic failures converged:

1. **Revision skill's write contract** includes `chapters/chapter-N.md` as an output path (`dispatch_helper.py:195-203`), but no-op scenarios should not write to this file.

2. **No pre-revision backup.** `state_snapshot-pre-rev.md` is written to `truth/` during revision (SKILL.md line 63) but does not back up `chapters/chapter-N.md`. The chapter loop's snapshot timing: snapshot is step 19, but revision is step 18 -- snapshot occurs after revision, not before.

3. **No content-size guard in `_write_parsed_outputs`.** Line 316 unconditionally writes whatever the LLM outputs without comparing against the original file size.

### 2.2 Seven Chapters with Zero or Degraded Prose (Extension of C1, consumed into this spec)

**Discovery (Agent 2 + D24):** Extended audit reveals 7 total chapters with prose issues:

| Chapter | File Size | CJK Chars | Snapshot | Problem |
|---------|-----------|-----------|----------|---------|
| Ch2 | 1,035B | 38 | None | Revision metadata overwrite |
| Ch9 | 641B | 121 | Corrupted | Revision metadata overwrite |
| Ch12 | 1,506B | 68 | Corrupted | Revision metadata overwrite |
| **Ch40** | 3,546B | **2,173** | Present (317KB) | **New: prose exists but severely degraded (system term density 33.6 per mille)** |
| Ch44 | 1,229B | 9 | Corrupted | Revision metadata overwrite |
| **Ch46** | 15,822B | **7,382** | Present (288KB) | **New: parameter density 114.7 per mille** |
| Ch55 | 103B | 0 | Corrupted | Revision metadata overwrite |

**Classification:**
- **Complete loss** (revision metadata overwrite): Ch2, Ch9, Ch12, Ch44, Ch55 (5 chapters)
- **Severe degradation** (unreadable parameter prose): Ch40, Ch46 (2 chapters)

The severe degradation chapters are technically "not empty" but are undeliverable as literature. They are addressed by the linguistic drift detection in the consolidated Context Persistence spec, while the content-size guard in this spec prevents the complete-loss pattern.

### 2.3 Staging Residue Cleanup (H4, consumed into this spec)

**Discovery:** `novel-output/xinghuo-ranqiong/staging/` contains 119 leftover files:

| Directory | File Count | Size |
|-----------|-----------|------|
| `staging/plans/` | 111 (56 .md + 55 .json) | ~1.2MB |
| `staging/truth/` | 8 (state-settling intermediates) | ~45KB |

All 56 chapters have corresponding final plans files -- staging contains duplicate copies.

**Design expectation vs reality:**

`checkpoint.py` defines a complete staging lifecycle:
- `commit_staging()` (line 32-56): Copy staging files to final paths via `safe_write`
- `clear_staging()` (line 59-73): `shutil.rmtree` the entire staging directory

Expected flow:
```
dispatch skill -> write to staging/ -> G4 validate -> commit_staging -> clear_staging
```

**Root cause:** Auto mode in `chapter_loop.py` (around lines 516-545, `_advance` function) calls `commit_staging()` but never follows with `clear_staging()`:

```python
# chapter_loop.py:516-545 -- auto mode path
if step.uses_staging:
    commit_staging(project_dir, [target])
    # MISSING: clear_staging(project_dir)
```

The human-approval path in `cli.py:317-351` correctly calls both `commit_staging()` and `clear_staging()`. Only auto mode is affected. Additionally, state-settling's auto-commit at `chapter_loop.py:537` has the same missing `clear_staging()`.

### 2.4 Snapshot Coverage Gaps (M3, consumed into this spec)

**Discovery:**
- **Snapshots present:** Ch5-55 (51 chapters)
- **Snapshots missing:** Ch1-4, Ch56 (5 chapters)
- **Snapshots corrupted:** Ch9/12/44/55 contain revision metadata instead of prose

**Root cause:** Snapshot generation is step 19 in the chapter loop (`chapter_loop.py:242-247`). Ch1-4 were generated in an earlier pipeline version or during debugging where the snapshot step wasn't included. Ch56 (final chapter) has no snapshot because the pipeline terminated before step 19 ran. There is no initialization snapshot at chapter loop start, and no emergency snapshot on abnormal termination.

### 2.5 Snapshot Bloat, Lockfile Permissions, and Budget Copying (LN1-LN3, consumed into this spec)

**LN1 -- Snapshot bloat (verified, worse than initially reported):**

| Chapter | Snapshot Size | Chapter Size | Ratio |
|---------|--------------|--------------|-------|
| Ch38 | 344,529 chars | ~21,000 chars | **~16x** |
| Ch37 | 335,678 chars | ~20,000 chars | **~16x** |
| Ch41 | 328,494 chars | 21,901 chars | **~15x** |

All snapshots are ~300KB+ while chapter files are ~20-40KB. Snapshots include complete audit reports (`audits/chapter-N-*.md`), all truth files (`truth/*.md` — global, not chapter-scoped), and revision tables. They should only contain chapter state.

**Root cause (verified):** `_snapshot_chapter_files` (`chapter_loop.py:903-960`) at lines 924-939 copies the chapter file PLUS all `audits/chapter-N-*.md` PLUS **all** `truth/*.md` (global truth files, not chapter-scoped). No differential snapshot support exists (grep for `differential`/`delta` returned zero).

**LN2 -- Lockfile permissions:** `pipeline-state.json.lockfile`: 0 bytes, permissions 0755 (should be 0644). The lockfile creation in `safe_write.py`'s `_acquire_lock` does not set explicit permissions.

**LN3 -- Decision budget copying (verified):** 2 pairs of adjacent chapter decision JSONs have identical `budget` fields (Ch14-Ch15, Ch19-Ch20) — budgets are copied without per-chapter recalculation. (Earlier analysis reported 6 pairs; filesystem verification with `raw_decode`-tolerant parsing found only 2 adjacent pairs with byte-identical budget objects across 55 readable chapters.)

---

## 3. Unified Fix Strategy

### 3.1 Pre-Revision Backup of Chapter Files

**Location:** `chapter_loop.py` (before step 18 revision dispatch, around line 1427, in `_route_revision_after_resonance`)

```python
# Before dispatching revision, back up the current chapter prose
import shutil
chapter_path = project_dir / f"chapters/chapter-{state.current_chapter}.md"
backup_path = project_dir / f"chapters/chapter-{state.current_chapter}-pre-rev.md"
if chapter_path.exists():
    shutil.copy2(chapter_path, backup_path)
    logger.info("pre_revision_backup", chapter=state.current_chapter,
                size=chapter_path.stat().st_size)
```

This ensures that even if the revision skill overwrites the chapter body, the original prose is recoverable from the `-pre-rev.md` backup.

### 3.2 Content-Size Guard in `_write_parsed_outputs`

> **Priority clarification:** This size guard is a DEFENSE-IN-DEPTH secondary safety net, NOT the primary root-cause fix. The primary fix is the write-contract change (§3.9 / Spec 2: revision skill must NOT emit the chapter body in no-op mode) + §3.1 (pre-revision backup). The 20% threshold is deliberately conservative — it catches the catastrophic cases (101-byte summary replacing 10KB prose) without blocking legitimate aggressive rewrites. Legitimate rewrites that compress by >80% are rare and would trigger only a WARN, not a block.

**Location:** `dispatch_helper.py:_write_parsed_outputs` (around line 316, before `safe_write` call)

```python
# Content-size guard for chapter body files
# NOTE: PurePath.match does not handle multi-segment patterns reliably;
# use parent.name + name checks instead.
from pathlib import Path
full_path = Path(path)
if (full_path.parent.name == "chapters"
        and full_path.name.startswith("chapter-")
        and full_path.name.endswith(".md")
        and not full_path.name.endswith("-pre-rev.md")):
    if full_path.exists():
        original_size = full_path.stat().st_size
        if len(content) < original_size * 0.2:
            logger.warning("revision_content_too_small", path=str(path),
                           original=original_size, new=len(content))
            continue  # Skip overwrite, preserve original
```

**Key design decisions:**
- Threshold: <20% of original file size triggers refusal. This catches the 101-byte "no revision needed" summaries while allowing legitimate heavy rewrites.
- The guard is a WARN + skip, not a HARD pipeline abort -- the original file is preserved.
- Only applies to chapter body files (`chapters/chapter-N.md`), not to metadata or audit files.
- Pre-revision backup (`-pre-rev.md` files) are excluded from the guard.

### 3.3 Clear Staging After Auto-Commit

**Location(s):** `chapter_loop.py` -- two fix points

**Fix point 1** -- auto mode for chapter-planning (around line 516-545, in `_advance`):

```python
if step.uses_staging and not requires_checkpoint:
    commit_staging(project_dir, [target])
    clear_staging(project_dir)  # ADD THIS LINE
```

**Fix point 2** -- auto-commit for state-settling (around line 537):

```python
commit_staging(project_dir, [target])
clear_staging(project_dir)  # ADD THIS LINE
```

### 3.4 Defensive Residual Cleanup at Pipeline Resume

**Location:** `cli.py` or `chapter_loop.py` resume entry point

```python
# At pipeline resume initialization
staging_dir = project_dir / "staging"
if staging_dir.exists():
    # If no pending staging steps exist in state, safe to clean
    if not _has_pending_staging_step(state):
        clear_staging(project_dir)
        logger.info("cleaned_staging_residue", project_dir=str(project_dir))
```

Additionally, `clear_staging()` in `checkpoint.py:59-73` already has a `staging.exists()` guard (verified at line 68: `if staging_dir.exists(): shutil.rmtree(...) else: log.debug(...)`), so no hardening is needed there — the function is already safe against missing directories.

### 3.5 Generate Starting Snapshot at Chapter Loop Initialization

**Location:** `chapter_loop.py` (chapter loop initialization, when `current_chapter == 1` and `step_index == 0`)

```python
# At chapter loop initialization, generate Ch1 starting snapshot
if state.chapter_loop.current_chapter == 1 and state.chapter_loop.step_index == 0:
    _snapshot_chapter_files(project_dir, state.chapter_loop.current_chapter)
```

### 3.6 Register `atexit` Emergency Snapshot Handler

**Location:** `chapter_loop.py` or pipeline entry point

```python
import atexit

def _emergency_snapshot(project_dir: Path, state: PipelineState) -> None:
    """Save current chapter state on abnormal termination."""
    try:
        _snapshot_chapter_files(project_dir, state.chapter_loop.current_chapter,
                                label="emergency")
    except Exception:
        pass  # Best-effort, never crash the crash handler

atexit.register(_emergency_snapshot, project_dir, state)
```

### 3.7 Content Guard in `_snapshot_chapter_files`

**Location:** `chapter_loop.py:_snapshot_chapter_files` (around line 903-942)

Add a minimum content check for chapter body files before including them in snapshots:

```python
# In _snapshot_chapter_files, before writing snapshot
text = chapter_path.read_text()
chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
if chinese_chars < 500:
    logger.warning("snapshot_suspect_content", chapter=chapter,
                   chinese_chars=chinese_chars)
    # Still save snapshot, but mark metadata as suspect
```

The threshold of 500 Chinese characters ensures that a snapshot containing only revision metadata (like the 101-byte Ch55 "no revision needed" text) is flagged but still saved -- preserving whatever data exists.

**Note:** Spec 10 (Data Storage Optimization) proposes a full rewrite of `_snapshot_chapter_files` with differential JSON-manifest format. The content guard and core-files filtering in this section should be integrated INTO Spec 10's rewrite, not applied as a separate in-place edit.

### 3.8 Filter Snapshots to Core Files Only

**Location:** `chapter_loop.py:_snapshot_chapter_files` (around line 903-942)

Restrict snapshot content to core chapter-state files, excluding:
- Audit reports (`audits/chapter-N-*.md`)
- Truth files (`truth/*.md`) that are already tracked separately
- Staging files

Only include:
- `chapters/chapter-N.md` (chapter prose)
- `chapters/chapter-N-meta.md` (chapter metadata)
- `chapters/chapter-N-decisions.json` (chapter decisions)
- `chapters/chapter-N-revision-decisions.json` (if exists)

**Note:** Spec 10 (Data Storage Optimization) proposes a full rewrite of `_snapshot_chapter_files` with differential JSON-manifest format. The content guard and core-files filtering in this section should be integrated INTO Spec 10's rewrite, not applied as a separate in-place edit.

### 3.9 Fix Lockfile Permissions

**Location:** `safe_write.py` (`_acquire_lock` function)

```python
# In _acquire_lock, after creating lockfile
os.chmod(lockfile, 0o644)
```

### 3.10 Add Adjacent-Chapter Budget Comparison in G4 Decisions

**Location:** `gates/g4/decisions_validator.py` (or `gates/g4/generic.py`)

```python
# Compare budget field with previous chapter's decisions
prev_decisions = project_dir / f"chapters/chapter-{chapter-1}-decisions.json"
curr_decisions = project_dir / f"chapters/chapter-{chapter}-decisions.json"
if prev_decisions.exists() and curr_decisions.exists():
    prev_data = json.loads(prev_decisions.read_text())
    curr_data = json.loads(curr_decisions.read_text())
    if prev_data.get('budget') == curr_data.get('budget'):
        issues.append("G4.dec.budget_unchanged: adjacent chapter budgets are identical")
```

This is a WARN-level check, not HARD -- budgets could legitimately be the same for adjacent chapters, but it flags potential copy-paste errors.

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/dispatch_helper.py:316` | Add content-size guard before `safe_write` | Prevent revision metadata from overwriting chapter prose |
| `src/shenbi/pipeline/chapter_loop.py:1021` (`_route_revision_after_resonance`) | Add pre-revision backup via `shutil.copy2` | Always preserve original prose before revision dispatch |
| `src/shenbi/pipeline/chapter_loop.py:516-545` (`_advance` auto mode) | Add `clear_staging()` after `commit_staging()` | Fix staging residue leak in auto mode |
| `src/shenbi/pipeline/chapter_loop.py:537` (state-settling auto-commit) | Add `clear_staging()` after `commit_staging()` | Fix staging residue leak in state-settling auto-commit |
| `src/shenbi/pipeline/chapter_loop.py` (chapter loop init) | Add Ch1 starting snapshot generation | Close Ch1-4 snapshot coverage gap |
| `src/shenbi/pipeline/chapter_loop.py` (or pipeline entry) | Add `atexit` emergency snapshot handler | Close Ch56 and crash-scenario coverage gaps |
| `src/shenbi/pipeline/chapter_loop.py:903-942` (`_snapshot_chapter_files`) | Add 500 Chinese char minimum content guard | Flag suspect snapshot content |
| `src/shenbi/pipeline/chapter_loop.py:903-942` (`_snapshot_chapter_files`) | Filter to core chapter files only | Fix 18x snapshot bloat |
| `src/shenbi/pipeline/cli.py` (resume entry) | Add defensive residual staging cleanup | Cleanup on pipeline resume |
| ~~`src/shenbi/pipeline/checkpoint.py:59-73`~~ | ~~Add `staging.exists()` guard~~ | **Already implemented** at line 68 — no change needed |
| `src/shenbi/safe_write.py` (`_acquire_lock`) | Add `os.chmod(lockfile, 0o644)` | Fix lockfile permissions |
| `src/shenbi/gates/g4/decisions_validator.py` | Add adjacent-chapter budget comparison | Detect copied budgets |
| `skills/shenbi-chapter-revision/SKILL.md:105-108` | Add no-op output instruction: do NOT write chapter body | Prevent LLM from writing summaries to chapter files |
| `skills/shenbi-snapshot-manage/SKILL.md` | Document core-files-only filtering | Align skill prompt with code behavior |

---

## 5. Verification Criteria

1. **Pre-revision backup test** (`tests/unit/pipeline/test_revision_safety.py`):
   - Simulate revision dispatch outputting 200-char summary to `chapters/chapter-N.md` with original file at 8,000 chars -> assert original file is NOT overwritten
   - Assert `chapter-N-pre-rev.md` exists with original content

2. **Content-size guard test:**
   - Original chapter 8,000 bytes, LLM outputs 100 bytes -> guard triggers, original preserved
   - Original chapter 8,000 bytes, LLM outputs 6,000 bytes (legitimate rewrite) -> guard passes

3. **Staging cleanup test:**
   - Auto-commit dispatch -> assert `staging/` directory does not exist after step completion
   - Reject path -> assert staging is cleaned and files not written to final

4. **Snapshot coverage:**
   - Chapter 1 completion -> `snapshots/` has file immediately
   - Simulate SIGTERM -> emergency snapshot generated
   - Snapshot content >= 500 Chinese characters (suspect warning only on genuine anomalies)

5. **Snapshot size:**
   - Snapshot size <= 5x chapter file size (down from 18x)

6. **Lockfile permissions:** `ls -l pipeline-state.json.lockfile` shows `-rw-r--r--` (0644)

7. **Adjacent chapter budgets differ** (WARN-only, not blocking)

8. **Canary verification:** Re-run with previously corrupted Ch2/9/12/44/55 scenarios -> no overwrite occurs

9. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 3 (this spec, Dispatch Safety and File Integrity)
    |
    +---> Supports Spec 2 (Output Validation and Format Enforcement) -- revision safety benefits from valid JSON decisions
    +---> Supports Spec 4 (Context Persistence and Linguistic Drift Prevention) -- snapshot integrity enables recovery

Prerequisites: None (standalone fix, though coordinated with revision skill changes in Spec 2)
```

### 6.1 Original Issue Code Mapping

| Original Issue Code | Description | Consolidated To |
|---|---|---|
| C1 | Revision Overwrite Chapter Content | Spec 3 (this spec) |
| H4 | Staging Residue Leak | Spec 3 (this spec) |
| M3 | Snapshot Coverage Gaps | Spec 3 (this spec) |
| LN1-LN3 | Snapshot Bloat / Lockfile / Budget Copy | Spec 3 (this spec) |
| CN1 | 主角消失 (Protagonist Disappearance) | Spec 1 |
| CN2 | Hook System Bifurcation | Spec 1 |
| CN3 | Truth File Overwrite | Spec 1 |
| CN4 | Resonance Score Null | Spec 1 |
| CN5 | Style Learning Never Updated | Spec 1 |
| CN6 | Pipeline State Stale Data | Spec 1 |
| H1 | JSON Corruption | Spec 2 |
| H2 | Revision System Failure | Spec 2 |
| M5 | G4 Format Mismatch | Spec 2 |
| C2 | Progressive Prose Collapse | Spec 4 |
| H3 | Context Assembly Persistence Gap | Spec 4 |
| HN1 | Template Duplication | Spec 4 |
| content-looping | Chapter Content Looping | Spec 4 |
| title-degradation, plan-content-mismatch, RS1, static-review-checklist | Review Quality Issues | Spec 5 |
| step-reorganization, parallelize, SCR, M1 | Pipeline Architecture | Spec 6 |
| maturity-bp-fixes, crash-recovery, runtime-optimizations, L1-L3, M2, H5, M4 | Pipeline Infrastructure | Spec 7 |
| llm-context-optimization | LLM Context Engineering | Spec 8 |
| volume-map, character-archive, C3 | Content Planning and Deliverable Design | Spec 9 |
| gate-markers, review-checklist-static, snapshot-differential | Data Storage Optimization | Spec 10 |
| validation, chapter-size-time | End-to-End Validation Protocol | Spec 11 |
