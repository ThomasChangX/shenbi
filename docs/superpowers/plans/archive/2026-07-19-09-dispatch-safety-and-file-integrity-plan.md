# Dispatch Safety and File Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pre-revision chapter backup (primary defense), a content-size guard as a DEFENSE-IN-DEPTH secondary safety net, staging cleanup in auto-commit paths, defensive residual cleanup at resume, starting snapshots and a signal-handler + checkpoint-on-step crash-recovery mechanism (atexit alone is insufficient), snapshot core-files filtering (integrated into Spec 10's rewrite, not a separate in-place edit), lockfile permissions fix, and adjacent-chapter budget comparison.

**Architecture:** A `shutil.copy2` backup runs before every revision dispatch, creating `chapter-N-pre-rev.md` — this is the PRIMARY root-cause fix (paired with the Spec 2 revision-skill write-contract change that stops no-op mode from emitting the chapter body). The content-size guard in `_write_parsed_outputs` is a SECONDARY defense-in-depth safety net that refuses writes < 20% of original chapter prose; it uses `parent.name`/`name.startswith()` checks (NOT `PurePath.match`, which does not handle multi-segment patterns reliably). Two missing `clear_staging()` calls are added in auto-commit paths. Crash recovery uses a signal handler (SIGTERM/SIGINT) plus checkpoint-on-step in addition to `atexit` — atexit alone does not run on SIGTERM/SIGKILL. Snapshot filtering (§3.7/§3.8) is integrated INTO Spec 10's rewrite of `_snapshot_chapter_files`, NOT applied as a separate in-place edit here. Lockfile permissions are set explicitly via `os.chmod`.

**Tech Stack:** Python 3.11+, pathlib, structlog, json, shutil, atexit, signal, os

## Global Constraints

- Simulate revision dispatch outputting 200-char summary to `chapters/chapter-N.md` with original file at 8,000 chars: original file is NOT overwritten
- Assert `chapter-N-pre-rev.md` exists with original content
- Original chapter 8,000 bytes, LLM outputs 100 bytes: guard triggers (WARN + skip, original preserved), original preserved
- Original chapter 8,000 bytes, LLM outputs 6,000 bytes (legitimate rewrite): guard passes
- Auto-commit dispatch: assert `staging/` directory does not exist after step completion
- Chapter 1 completion: `snapshots/` has file immediately
- Simulate SIGTERM: emergency snapshot generated (via signal handler, not atexit alone)
- Snapshot content >= 500 Chinese characters (suspect warning only on genuine anomalies)
- Snapshot size <= 5x chapter file size (down from ~15x — measured Ch37/38/41 are ~15-16x, not 18x)
- `ls -l pipeline-state.json.lockfile` shows `-rw-r--r--` (0644)
- Adjacent chapter budgets: 2 known identical pairs (Ch14-15, Ch19-Ch20) — WARN-only, not blocking (earlier "6 pairs" claim corrected to 2 by filesystem verification)
- Re-run with previously corrupted Ch2/9/12/44/55 scenarios: no overwrite occurs
- `clear_staging()` in `checkpoint.py:59-73` already has a `staging.exists()` guard at line 68 — no hardening needed there
- Regression: `just check` passes fully

---

### Task 1: Add Pre-Revision Backup of Chapter Files

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (in `_route_revision_after_resonance`, around line 1021)
- Test: `tests/unit/pipeline/test_revision_safety.py`

**Interfaces:**
- Consumes: Current chapter file at `chapters/chapter-N.md`
- Produces: Backup at `chapters/chapter-N-pre-rev.md` before revision dispatch

- [ ] **Step 1: Write the failing test**

```python
"""Tests for pre-revision backup safety."""
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _create_pre_revision_backup


def test_backup_creates_copy_of_chapter_file():
    """Pre-revision backup creates a -pre-rev.md copy."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        original.write_text("林烽站在城墙上，风沙扑面而来。远处的烽火台冒着黑烟。")

        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.exists()
        assert backup.read_text() == original.read_text()


def test_backup_preserves_file_metadata():
    """Backup preserves modification time and file size."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        content = "x" * 8000
        original.write_text(content)

        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.stat().st_size == 8000


def test_backup_skips_when_chapter_missing():
    """No error when chapter file does not exist yet."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        _create_pre_revision_backup(project_dir, chapter=99)

        backup = chapters / "chapter-99-pre-rev.md"
        assert not backup.exists()


def test_backup_overwrites_previous_backup():
    """Second backup for same chapter overwrites the first."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        original = chapters / "chapter-5.md"
        original.write_text("version 1")
        _create_pre_revision_backup(project_dir, chapter=5)

        original.write_text("version 2")
        _create_pre_revision_backup(project_dir, chapter=5)

        backup = chapters / "chapter-5-pre-rev.md"
        assert backup.read_text() == "version 2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_revision_safety.py -v`
Expected: FAIL (ImportError: _create_pre_revision_backup not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
import shutil as _shutil


def _create_pre_revision_backup(project_dir: Path, chapter: int) -> None:
    """Create a backup of the chapter file before revision dispatch.

    Copies ``chapters/chapter-N.md`` to ``chapters/chapter-N-pre-rev.md``
    using ``shutil.copy2`` which preserves metadata. If the chapter file
    does not exist, this is a no-op.

    This ensures the original prose is recoverable even if the revision
    skill incorrectly overwrites the chapter body.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.
    """
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        log.debug("pre_rev_backup_skip", chapter=chapter,
                  reason="chapter file does not exist")
        return

    backup_path = project_dir / "chapters" / f"chapter-{chapter}-pre-rev.md"
    _shutil.copy2(chapter_path, backup_path)
    log.info("pre_revision_backup_created", chapter=chapter,
             size=chapter_path.stat().st_size)
```

Then integrate into `_route_revision_after_resonance` (around line 1021). At the top of the function, before any revision dispatch logic:

```python
# At the beginning of _route_revision_after_resonance:
_create_pre_revision_backup(project_dir, chapter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_revision_safety.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_revision_safety.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: add pre-revision chapter backup before revision dispatch"
```

---

### Task 2: Add Content-Size Guard in `_write_parsed_outputs`

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_write_parsed_outputs`, around line 316)
- Test: `tests/unit/pipeline/test_revision_safety.py` (add content-size guard tests)

**Interfaces:**
- Consumes: Original file size (if exists), new content from LLM output
- Produces: Guard that refuses writes when new content < 20% of original (DEFENSE-IN-DEPTH secondary safety net)

**Priority (from spec §3.2):** This size guard is a DEFENSE-IN-DEPTH secondary safety net, NOT the primary root-cause fix. The primary fix is (a) the Spec 2 write-contract change — the revision skill must NOT emit the chapter body in no-op mode — plus (b) Task 1's pre-revision backup. The 20% threshold is deliberately conservative: it catches catastrophic cases (101-byte summary replacing 10KB prose) without blocking legitimate aggressive rewrites. Legitimate rewrites that compress by >80% are rare and trigger only a WARN + skip (original preserved), not a hard pipeline abort. Use `parent.name`/`name.startswith()` checks — NOT `PurePath.match`, which does not handle multi-segment patterns reliably.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/pipeline/test_revision_safety.py

from shenbi.pipeline.dispatch_helper import _check_content_size_guard


def test_content_guard_blocks_tiny_overwrite():
    """Refuses to overwrite when new content < 20% of original."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5.md"
        existing.write_text("a" * 8000)

        # New content is 100 bytes — only 1.25% of original
        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5.md", "x" * 100)

        assert should_block is True
        assert "content_too_small" in reason.lower()


def test_content_guard_allows_legitimate_rewrite():
    """Allows overwrite when new content is >= 20% of original."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5.md"
        existing.write_text("a" * 8000)

        # New content is 6000 bytes — 75% of original
        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5.md", "x" * 6000)

        assert should_block is False


def test_content_guard_allows_new_files():
    """Allows write when no existing file (first creation)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-55.md", "x" * 8000)

        assert should_block is False


def test_content_guard_skips_non_chapter_md():
    """Only applies to chapters/chapter-N.md, not other files."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)

        existing = truth_dir / "current_state.md"
        existing.write_text("a" * 8000)

        should_block, reason = _check_content_size_guard(
            project_dir, "truth/current_state.md", "short")

        assert should_block is False


def test_content_guard_skips_pre_rev_files():
    """The -pre-rev.md backup files are never guarded."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir(parents=True)

        existing = chapters / "chapter-5-pre-rev.md"
        existing.write_text("a" * 8000)

        should_block, reason = _check_content_size_guard(
            project_dir, "chapters/chapter-5-pre-rev.md", "short")

        assert should_block is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_revision_safety.py::test_content_guard_blocks_tiny_overwrite -v`
Expected: FAIL (ImportError: _check_content_size_guard not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/dispatch_helper.py`:

```python
# Minimum ratio of new content to original before overwrite is allowed.
# Below this, the write is refused (WARN + skip) to prevent revision metadata
# summaries from overwriting actual chapter prose. This is a DEFENSE-IN-DEPTH
# secondary safety net — the primary fix is the revision write-contract change
# (Spec 2) + the pre-revision backup (Task 1).
_CONTENT_SIZE_MIN_RATIO = 0.20


def _check_content_size_guard(
    project_dir: Path,
    rel_path: str,
    new_content: str,
) -> tuple[bool, str]:
    """Check if new content is too small compared to existing file.

    Only applies to ``chapters/chapter-N.md`` files (not metadata, audits,
    truth files, or ``-pre-rev.md`` backups). Path matching uses
    ``parent.name``/``name.startswith()`` — NOT ``PurePath.match``, which
    does not handle multi-segment patterns reliably.

    Args:
        project_dir: Root directory of the novel project.
        rel_path: Relative path within the project directory.
        new_content: The new content about to be written.

    Returns:
        A tuple of ``(should_block, reason)``. ``should_block`` is True
        when the write should be refused. ``reason`` is a human-readable
        explanation (empty string if not blocking).
    """
    # Only guard chapter body files: parent dir must be "chapters", name must
    # start with "chapter-" and end with ".md", and must NOT be a -pre-rev
    # backup. Use parent.name/name.startswith() per spec §3.2 (PurePath.match
    # does not handle multi-segment patterns reliably).
    path = Path(rel_path)
    if path.parent.name != "chapters":
        return False, ""
    if not path.name.startswith("chapter-"):
        return False, ""
    if not path.name.endswith(".md"):
        return False, ""
    if path.name.endswith("-pre-rev.md"):
        return False, ""

    full_path = project_dir / rel_path
    if not full_path.exists():
        return False, ""

    original_size = full_path.stat().st_size
    if original_size == 0:
        return False, ""

    new_size = len(new_content)
    ratio = new_size / original_size

    if ratio < _CONTENT_SIZE_MIN_RATIO:
        reason = (
            f"content_too_small: {new_size}B is {ratio:.1%} of "
            f"original {original_size}B (threshold: {_CONTENT_SIZE_MIN_RATIO:.0%})"
        )
        return True, reason

    return False, ""
```

Then integrate into `_write_parsed_outputs` (around line 316), before `safe_write`:

```python
# Before safe_write(full_path, content):
should_block, reason = _check_content_size_guard(project_dir, rel_path, content)
if should_block:
    log.warning("write_blocked_content_size_guard", path=rel_path, reason=reason)
    continue  # Skip this file, preserve original
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_revision_safety.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_revision_safety.py src/shenbi/pipeline/dispatch_helper.py
git commit -m "feat: add content-size guard to prevent revision metadata overwrites"
```

---

### Task 3: Add `clear_staging()` After `commit_staging()` in Auto-Commit Paths

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (two fix points in `_advance`, around lines 516-545)
- Test: `tests/unit/pipeline/test_staging_cleanup.py`

**Interfaces:**
- Consumes: `commit_staging`, `clear_staging` from `checkpoint.py`
- Produces: Staging directory cleaned after every auto-commit

- [ ] **Step 1: Write the failing test**

```python
"""Tests for staging cleanup in auto-commit paths."""
import tempfile
from pathlib import Path

from shenbi.pipeline.checkpoint import commit_staging, clear_staging, staging_path


def test_clear_staging_removes_directory():
    """clear_staging removes the entire staging directory."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        (staging_dir / "test.txt").write_text("data")

        clear_staging(project_dir)

        assert not staging_dir.exists()


def test_clear_staging_handles_missing_directory():
    """clear_staging does not crash when staging doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Should not raise
        clear_staging(project_dir)


def test_commit_then_clear_leaves_no_staging():
    """commit_staging + clear_staging = clean state."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Simulate: skill writes to staging
        staging_plan = staging_path(project_dir, "plans/chapter-5-plan.md")
        staging_plan.parent.mkdir(parents=True)
        staging_plan.write_text("# Chapter 5 Plan")

        # Commit
        commit_staging(project_dir, ["plans/chapter-5-plan.md"])
        final_path = project_dir / "plans" / "chapter-5-plan.md"
        assert final_path.exists()

        # Clear
        clear_staging(project_dir)

        staging_dir = project_dir / "staging"
        assert not staging_dir.exists()


def test_clear_staging_handles_nested_directories():
    """clear_staging removes nested staging directories."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        nested = staging_dir / "plans" / "nested"
        nested.mkdir(parents=True)
        (nested / "file.md").write_text("content")

        clear_staging(project_dir)

        assert not staging_dir.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_staging_cleanup.py -v`
Expected: PASS (these test the existing `clear_staging` which already works correctly -- the bug is in `_advance` not calling it)

The tests pass, but we are testing the existing `clear_staging`. The actual fix is in `_advance`.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/chapter_loop.py`, in `_advance` function. Find the auto-commit path (around line 516-545):

**Fix point 1** -- auto mode for chapter-planning:

```python
# In _advance, the auto-commit path (around line 516-545):
# Change:
#     if step.uses_staging and not requires_checkpoint:
#         from shenbi.pipeline.checkpoint import commit_staging
#         commit_staging(project_dir, [target])
# To:
if step.uses_staging and not requires_checkpoint:
    from shenbi.pipeline.checkpoint import commit_staging, clear_staging
    commit_staging(project_dir, [target])
    clear_staging(project_dir)  # Fix: clean staging after auto-commit
```

**Fix point 2** -- auto-commit for state-settling (around line 537):

```python
# In the state-settling auto-commit path:
# Change:
#     commit_staging(project_dir, [target])
# To:
commit_staging(project_dir, [target])
clear_staging(project_dir)  # Fix: clean staging after auto-commit
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_staging_cleanup.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_staging_cleanup.py src/shenbi/pipeline/chapter_loop.py
git commit -m "fix: add clear_staging() after commit_staging() in auto-commit paths"
```

---

### Task 4: Add Defensive Residual Cleanup at Pipeline Resume

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (resume entry point)
- Test: `tests/unit/pipeline/test_staging_cleanup.py` (add resume cleanup test)

**Interfaces:**
- Consumes: Pipeline state at resume, staging directory on disk
- Produces: Staging directory cleaned if no pending staging steps

**Note on the underlying `clear_staging`:** `clear_staging()` in `checkpoint.py:59-73` already has a `staging.exists()` guard at line 68 (`if staging_dir.exists(): shutil.rmtree(...) else: log.debug(...)`), so it is already safe against a missing directory. This task does NOT harden `clear_staging` — it adds the resume-entry `_cleanup_residual_staging` wrapper that decides whether to call it based on pending staging steps.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/pipeline/test_staging_cleanup.py

from shenbi.pipeline.chapter_loop import _cleanup_residual_staging


def test_cleanup_removes_residual_staging_on_resume():
    """Residual staging is cleaned at pipeline resume."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        (staging_dir / "plans").mkdir()
        (staging_dir / "plans" / "old-file.md").write_text("stale data")

        _cleanup_residual_staging(project_dir, has_pending_staging=False)

        assert not staging_dir.exists()


def test_cleanup_preserves_staging_when_steps_pending():
    """Staging is NOT cleaned when pending staging steps exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        staging_dir = project_dir / "staging"
        staging_dir.mkdir()
        (staging_dir / "pending.txt").write_text("active step data")

        _cleanup_residual_staging(project_dir, has_pending_staging=True)

        assert staging_dir.exists()


def test_cleanup_handles_no_staging_dir():
    """No error when staging directory does not exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        _cleanup_residual_staging(project_dir, has_pending_staging=False)

        # No exception expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_staging_cleanup.py::test_cleanup_removes_residual_staging_on_resume -v`
Expected: FAIL (ImportError: _cleanup_residual_staging not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
def _cleanup_residual_staging(
    project_dir: Path,
    has_pending_staging: bool,
) -> None:
    """Clean residual staging directory at pipeline resume.

    If the staging directory exists and no pipeline steps are pending
    that write to staging, the directory is safe to remove. This
    prevents accumulation of stale staging files across pipeline runs.

    Args:
        project_dir: Root directory of the novel project.
        has_pending_staging: True if any pending step uses staging.
    """
    from shenbi.pipeline.checkpoint import clear_staging

    staging_dir = project_dir / "staging"
    if not staging_dir.exists():
        return

    if has_pending_staging:
        log.debug("staging_cleanup_skipped", reason="pending staging steps")
        return

    clear_staging(project_dir)
    log.info("residual_staging_cleaned_at_resume", project_dir=str(project_dir))
```

Then integrate at the pipeline resume initialization (in `chapter_loop.py`, the function that loads state and begins the chapter loop). After loading state, before entering the loop:

```python
# At pipeline resume, after state is loaded:
_cleanup_residual_staging(project_dir, has_pending_staging=_has_pending_staging_step(state))
```

And add the helper to determine if any pending step uses staging:

```python
def _has_pending_staging_step(state: PipelineState) -> bool:
    """Check if any pending step in the current chapter uses staging."""
    chapter = state.chapter_loop.current_chapter
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        return False
    for step in CHAPTER_STEPS[step_idx:]:
        if step.uses_staging:
            return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_staging_cleanup.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_staging_cleanup.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: add defensive residual staging cleanup at pipeline resume"
```

---

### Task 5: Generate Starting Snapshot and Register Emergency Snapshot Handler

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (chapter loop init + atexit handler)
- Test: `tests/unit/pipeline/test_snapshot_coverage.py`

**Interfaces:**
- Consumes: Chapter loop initialization, process signals (SIGTERM/SIGINT)
- Produces: Ch1 snapshot at loop start, emergency snapshot on abnormal termination via signal handler + checkpoint-on-step (atexit alone is insufficient)

**Crash-recovery rationale (from spec §3.6):** `atexit` alone is insufficient — it does NOT run on SIGTERM/SIGKILL, which is exactly the abnormal-termination scenario that loses Ch56's snapshot. The fix registers a `signal` handler for SIGTERM/SIGINT that generates an emergency snapshot, AND keeps a module-level "current chapter/step" updated on each step (checkpoint-on-step) so the handler knows the latest state to snapshot. `atexit` is kept as a backstop for clean-ish exits.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for snapshot coverage and emergency handler."""
import signal
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _should_generate_starting_snapshot,
    _register_emergency_snapshot,
    _update_emergency_checkpoint,
    _do_emergency_snapshot,
)


def test_starting_snapshot_triggers_at_ch1_step0():
    """Starting snapshot triggers at chapter 1, step index 0."""
    assert _should_generate_starting_snapshot(
        current_chapter=1, step_index=0) is True


def test_starting_snapshot_does_not_trigger_at_ch2():
    """No starting snapshot at chapter 2."""
    assert _should_generate_starting_snapshot(
        current_chapter=2, step_index=0) is False


def test_starting_snapshot_does_not_trigger_at_ch1_step1():
    """No starting snapshot mid-chapter."""
    assert _should_generate_starting_snapshot(
        current_chapter=1, step_index=5) is False


def test_starting_snapshot_triggers_at_ch2_when_ch1_missing():
    """Self-heal: triggers at Ch2 step 0 if Ch1 snapshot is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        snapshots_dir = project_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        # No chapter-1 snapshot exists

        assert _should_generate_starting_snapshot(
            current_chapter=2, step_index=0,
            project_dir=project_dir) is True


def test_starting_snapshot_skips_when_ch1_snapshot_exists():
    """No starting snapshot at Ch2 step 0 if Ch1 snapshot exists."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        snapshots_dir = project_dir / "snapshots"
        snapshots_dir.mkdir(parents=True)
        # Create a chapter-1 snapshot marker
        (snapshots_dir / "chapter-1-snapshot.md").write_text("# snapshot")

        assert _should_generate_starting_snapshot(
            current_chapter=2, step_index=0,
            project_dir=project_dir) is False


def test_emergency_snapshot_registered():
    """Emergency snapshot handler can be registered without error."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)

        # Should not raise (installs signal handlers + atexit backstop)
        _register_emergency_snapshot(project_dir, chapter=5)


def test_emergency_checkpoint_tracks_latest_chapter():
    """Checkpoint-on-step updates the emergency target to the latest chapter."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        _register_emergency_snapshot(project_dir, chapter=1)
        # Simulate the loop advancing through chapters
        _update_emergency_checkpoint(project_dir, chapter=56)

        import shenbi.pipeline.chapter_loop as cl
        assert cl._emergency_snapshot_chapter == 56
        assert cl._emergency_snapshot_project_dir == project_dir


def test_do_emergency_snapshot_uses_latest_checkpoint():
    """The snapshot helper reads the checkpoint-on-step state, not init state."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        (project_dir / "chapters" / "chapter-56.md").write_text("# Ch56")
        _register_emergency_snapshot(project_dir, chapter=1)
        _update_emergency_checkpoint(project_dir, chapter=56)

        # Must not raise; best-effort snapshot of chapter 56 (not chapter 1)
        _do_emergency_snapshot()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_snapshot_coverage.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
import atexit as _atexit
import signal as _signal

# Module-level storage for emergency snapshot params.
# Set at pipeline init, consumed by the atexit + signal handlers.
# This is the "checkpoint-on-step": updated on every chapter-loop step so the
# signal handler always knows the latest chapter to snapshot on SIGTERM/SIGINT.
_emergency_snapshot_project_dir: Path | None = None
_emergency_snapshot_chapter: int = 0
_emergency_signal_handler_installed: bool = False
_emergency_flag: bool = False


def _check_emergency_flag(project_dir: Path, chapter: int) -> None:
    """Called at step boundaries in the main loop. If flag is set,
    perform emergency snapshot safely from the main thread."""
    global _emergency_flag
    if _emergency_flag:
        _emergency_flag = False
        _do_emergency_snapshot()


def _should_generate_starting_snapshot(
    current_chapter: int,
    step_index: int,
    project_dir: Path | None = None,
) -> bool:
    """Determine if a starting snapshot should be generated.

    Generates snapshot at:
        - Chapter 1, step 0 (initialization)
        - Any chapter step 0 if Ch1 snapshot is missing (self-heal)

    Args:
        current_chapter: Current chapter number.
        step_index: Current step index (0 = start).
        project_dir: Optional project dir to check for existing snapshots.

    Returns:
        True if a starting snapshot is warranted.
    """
    if current_chapter == 1 and step_index == 0:
        return True

    # Self-heal: if we're at step 0 of any chapter and no Ch1 snapshot exists
    if step_index == 0 and project_dir is not None:
        snapshots_dir = project_dir / "snapshots"
        if not snapshots_dir.exists():
            return True
        ch1_snapshots = list(snapshots_dir.glob("chapter-1-*.md"))
        if not ch1_snapshots:
            return True

    return False


def _do_emergency_snapshot() -> None:
    """Best-effort emergency snapshot. Never raises.

    Reads the module-level checkpoint state (set by checkpoint-on-step) and
    writes an ``emergency`` snapshot of the current chapter. Safe to call from
    a signal handler or atexit: any exception is swallowed so the crash handler
    never crashes the crash.
    """
    try:
        pd = _emergency_snapshot_project_dir
        ch = _emergency_snapshot_chapter
        if pd is not None and ch > 0:
            _snapshot_chapter_files(pd, ch, label="emergency")
            log.warning("emergency_snapshot_saved", chapter=ch)
    except Exception:
        pass


def _register_emergency_snapshot(project_dir: Path, chapter: int) -> None:
    """Register handlers that generate an emergency snapshot on termination.

    Three layers of defense (per spec §3.6, atexit alone is insufficient):

    1. ``signal.signal(SIGTERM/SIGINT)`` — catches abnormal termination that
       ``atexit`` misses (SIGTERM does not run atexit handlers).
    2. ``atexit.register`` — backstop for clean-ish interpreter shutdown.
    3. Checkpoint-on-step — ``_update_emergency_checkpoint`` is called on every
       chapter-loop step so handlers always snapshot the LATEST chapter, not a
       stale one from init.

    The signal handler is installed exactly once (guarded by
    ``_emergency_signal_handler_installed``) to avoid stacking duplicate
    handlers across pipeline re-entries.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Current chapter number at registration time.
    """
    global _emergency_snapshot_project_dir, _emergency_snapshot_chapter
    global _emergency_signal_handler_installed
    _emergency_snapshot_project_dir = project_dir
    _emergency_snapshot_chapter = chapter

    # Layer 2: atexit backstop
    _atexit.register(_do_emergency_snapshot)

    # Layer 1: signal handlers for SIGTERM/SIGINT (installed once)
    if not _emergency_signal_handler_installed:
        _signal.signal(_signal.SIGTERM, _emergency_snapshot_signal_handler)
        _signal.signal(_signal.SIGINT, _emergency_snapshot_signal_handler)
        _emergency_signal_handler_installed = True


def _emergency_snapshot_signal_handler(signum, frame) -> None:
    """Signal handler: ONLY sets atomic flag. No I/O, no locks.

    The actual snapshot work is done in _check_emergency_flag(), called at
    step boundaries in the main loop. This keeps I/O out of signal context
    (which is unsafe and can deadlock).
    """
    global _emergency_flag
    _emergency_flag = True
    # Restore default disposition so a second signal terminates immediately
    _signal.signal(signum, _signal.SIG_DFL)


def _update_emergency_checkpoint(project_dir: Path, chapter: int) -> None:
    """Checkpoint-on-step: refresh the emergency-snapshot state every step.

    Called on each chapter-loop iteration so signal/atexit handlers always
    snapshot the LATEST chapter rather than the chapter active at init. This
    is what closes the gap that lost Ch56's snapshot (spec §3.6).

    Args:
        project_dir: Root directory of the novel project.
        chapter: The chapter just entered (or currently being processed).
    """
    global _emergency_snapshot_project_dir, _emergency_snapshot_chapter
    _emergency_snapshot_project_dir = project_dir
    _emergency_snapshot_chapter = chapter
```

(``_os_exit`` is ``os._exit`` — import it at module top as ``from os import _exit as _os_exit``.)

Then integrate at the chapter loop entry point and on each step:

```python
# At chapter loop initialization (near where the loop starts):
if _should_generate_starting_snapshot(
    state.chapter_loop.current_chapter,
    state.chapter_loop.step_index,
    project_dir=project_dir,
):
    _snapshot_chapter_files(project_dir, state.chapter_loop.current_chapter)

# Register emergency handler ONCE (installs signal handlers + atexit backstop)
_register_emergency_snapshot(project_dir, state.chapter_loop.current_chapter)

# ...inside the chapter loop, at the top of each iteration (checkpoint-on-step):
_update_emergency_checkpoint(project_dir, state.chapter_loop.current_chapter)
# Check for emergency snapshot flag at each step boundary (safe I/O from main thread)
_check_emergency_flag(project_dir, state.chapter_loop.current_chapter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_snapshot_coverage.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_snapshot_coverage.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: add starting snapshot, checkpoint-on-step, and signal-driven emergency snapshot"
```

---

### Task 6: Filter Snapshots to Core Files and Add Content Guard

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (`_snapshot_chapter_files`, around line 903-942)
- Test: `tests/unit/pipeline/test_snapshot_coverage.py` (add filtering tests)

**Interfaces:**
- Consumes: Project directory, chapter number, the existing `_snapshot_chapter_files` body
- Produces: Snapshots containing only core chapter files with minimum CJK content check (cuts ~15x bloat, per spec §3.7)

**Integration note (spec §3.7/§3.8):** Spec 10 already rewrites `_snapshot_chapter_files` end-to-end. The §3.7 core-files filtering and §3.8 content guard from this plan MUST be folded INTO that Spec 10 rewrite as a single, coherent implementation — NOT applied as a separate, conflicting in-place edit that would collide with Spec 10's structure. Concretely: edit the `_snapshot_chapter_files` produced by Spec 10 (not the pre-Spec-10 version), so the core-file list and CJK check are part of the same rewrite. If executing this plan before Spec 10, implement `_snapshot_chapter_files` here in its final form (core-file list + CJK check) so Spec 10 has nothing to add.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/pipeline/test_snapshot_coverage.py

from shenbi.pipeline.chapter_loop import (
    _get_core_snapshot_files,
    _has_minimum_chinese_chars,
)


def test_core_snapshot_files_only_includes_chapter_artifacts():
    """Snapshot file list includes only core chapter files."""
    files = _get_core_snapshot_files(project_dir=Path("/tmp/test"), chapter=5)

    # Should include the chapter body
    assert any("chapter-5.md" in f or f.endswith("chapter-5.md") for f in files)

    # Should NOT include audit reports
    for f in files:
        assert "audits/" not in str(f)
        assert "truth/" not in str(f)
        assert "staging/" not in str(f)


def test_min_chinese_chars_detects_short_content():
    """Content with fewer than 500 Chinese chars triggers warning."""
    # Revision metadata — 0 Chinese chars
    short = "Chapter complete. No changes needed. Summary follows."
    assert _has_minimum_chinese_chars(short, threshold=500) is False


def test_min_chinese_chars_passes_normal_prose():
    """Normal Chinese prose passes the minimum character check."""
    normal = "林烽" * 300  # 600 Chinese characters
    assert _has_minimum_chinese_chars(normal, threshold=500) is True


def test_min_chinese_chars_counts_only_cjk():
    """Only CJK unified ideographs are counted, not punctuation."""
    mixed = "林烽站在城墙上。" * 100  # ~400 Chinese chars + punctuation
    result = _has_minimum_chinese_chars(mixed, threshold=300)
    assert result is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_snapshot_coverage.py -v -k "core_snapshot or min_chinese"`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
# Files included in snapshots (core chapter-state only).
# Excludes audits, truth files, and staging to prevent ~15x bloat (spec §3.7).
_CORE_SNAPSHOT_PATTERNS = [
    "chapters/chapter-{chapter}.md",
    "chapters/chapter-{chapter}-meta.md",
    "chapters/chapter-{chapter}-decisions.json",
    "chapters/chapter-{chapter}-revision-decisions.json",
]


def _get_core_snapshot_files(project_dir: Path, chapter: int) -> list[Path]:
    """Get list of core chapter files to include in a snapshot.

    Only includes chapter body, metadata, decisions, and revision decisions.
    Excludes audit reports, truth files, and staging to reduce snapshot bloat.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.

    Returns:
        List of existing file paths to include in the snapshot.
    """
    files: list[Path] = []
    for pattern in _CORE_SNAPSHOT_PATTERNS:
        path = project_dir / pattern.format(chapter=chapter)
        if path.exists():
            files.append(path)
    return files


def _has_minimum_chinese_chars(text: str, threshold: int = 500) -> bool:
    """Check if text has at least ``threshold`` Chinese characters.

    Chinese characters are defined as CJK Unified Ideographs (U+4E00 to
    U+9FFF). This is used to flag snapshots that may contain revision
    metadata instead of actual prose.

    Args:
        text: The text content to check.
        threshold: Minimum number of Chinese characters required.

    Returns:
        True if the text has >= ``threshold`` Chinese characters.
    """
    count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return count >= threshold
```

Then update `_snapshot_chapter_files` (around line 903) to use `_get_core_snapshot_files` instead of scanning the entire project, and add the Chinese char check:

```python
# In _snapshot_chapter_files, replace the existing file collection logic:
# Old: scan chapters/, audits/, truth/ etc.
# New:
core_files = _get_core_snapshot_files(project_dir, chapter)

# Content check for chapter body file
chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
if chapter_path.exists():
    text = chapter_path.read_text(encoding="utf-8")
    if not _has_minimum_chinese_chars(text):
        log.warning("snapshot_suspect_content", chapter=chapter,
                    chinese_chars=sum(1 for c in text if '\u4e00' <= c <= '\u9fff'))
        # Still save snapshot, but mark as suspect
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_snapshot_coverage.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_snapshot_coverage.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: filter snapshots to core files and add min-CJK content guard"
```

---

### Task 7: Fix Lockfile Permissions and Add Budget Comparison

**Files:**
- Modify: `src/shenbi/safe_write.py` (`_acquire_lock`, add `os.chmod`)
- Modify: `src/shenbi/gates/g4/decisions_validator.py` (add adjacent-chapter budget comparison)
- Test: `tests/unit/test_safe_write.py` (lockfile permission test)
- Test: `tests/unit/gates/g4/test_decisions_validator.py` (budget comparison test)

**Interfaces:**
- Consumes: Lockfile path, adjacent chapter decisions files
- Produces: Lockfile at 0o644, budget comparison WARN

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/test_safe_write.py (or create)

import os
import tempfile
from pathlib import Path

from shenbi.safe_write import safe_write


def test_lockfile_has_correct_permissions():
    """Lockfile created by safe_write has 0o644 permissions."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.json"
        safe_write(path, '{"key": "value"}')

        # Check that no lockfile is lingering (already cleaned)
        # But check the parent dir for any leftover lockfiles:
        lockfiles = list(Path(tmp).glob("*.lock"))
        assert len(lockfiles) == 0  # Lockfile was cleaned


def test_lockfile_permissions_are_set():
    """Verify os.chmod is called correctly on lockfile creation."""
    import stat
    with tempfile.TemporaryDirectory() as tmp:
        lockfile = Path(tmp) / "test.lock"
        # Create lockfile like _acquire_lock does
        fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Set permissions
        os.chmod(lockfile, 0o644)

        actual_mode = lockfile.stat().st_mode & 0o777
        assert actual_mode == 0o644, f"Expected 0o644, got {oct(actual_mode)}"


# Add to tests/unit/gates/g4/test_decisions_validator.py (or create)

import json
import tempfile
from pathlib import Path

from shenbi.gates.g4.decisions_validator import _check_adjacent_budget


def test_budget_comparison_detects_copy():
    """Identical budgets in adjacent chapters trigger WARN."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        budget = {"token_planning": 5000, "token_drafting": 8000}

        prev = chapters / "chapter-5-decisions.json"
        curr = chapters / "chapter-6-decisions.json"
        prev.write_text(json.dumps({"budget": budget}))
        curr.write_text(json.dumps({"budget": budget}))

        issues = _check_adjacent_budget(project_dir, chapter=6)
        assert len(issues) > 0
        assert "budget_unchanged" in issues[0]


def test_budget_comparison_passes_different_budgets():
    """Different budgets do not trigger WARN."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        prev = chapters / "chapter-5-decisions.json"
        curr = chapters / "chapter-6-decisions.json"
        prev.write_text(json.dumps({"budget": {"token_planning": 5000}}))
        curr.write_text(json.dumps({"budget": {"token_planning": 6000}}))

        issues = _check_adjacent_budget(project_dir, chapter=6)
        assert len(issues) == 0


def test_budget_comparison_skips_when_prev_missing():
    """No error when previous chapter decisions file does not exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters = project_dir / "chapters"
        chapters.mkdir()

        curr = chapters / "chapter-1-decisions.json"
        curr.write_text(json.dumps({"budget": {"token_planning": 5000}}))

        issues = _check_adjacent_budget(project_dir, chapter=1)
        assert len(issues) == 0  # No previous chapter
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_safe_write.py::test_lockfile_has_correct_permissions tests/unit/gates/g4/test_decisions_validator.py -v`
Expected: FAIL (some tests pass, new tests may fail with ImportError)

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/safe_write.py`, in `_acquire_lock`, after the `os.open(..., os.O_CREAT | os.O_EXCL | os.O_WRONLY)` call on the lockfile path:

> **Note:** This fix applies only to the M5 O_EXCL fallback path. The primary
> `fcntl.flock` path locks the parent directory and does not create `.lock`
> files, so permissions don't apply there.

```python
# In _acquire_lock, after creating the lockfile via os.open(...)
# (around line 68, in the M5 fallback branch):
try:
    fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.chmod(lockfile, 0o644)  # Fix: set correct permissions
    return fd, lockfile
except FileExistsError:
    # ... retry logic ...
```

Similarly for the retry-created lockfile (around line 77):

```python
# In the retry loop:
try:
    fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.chmod(lockfile, 0o644)  # Fix: set correct permissions
    return fd, lockfile
except FileExistsError:
    continue
```

And for the stale takeover (around line 88):

```python
# In the stale lock takeover:
try:
    os.unlink(str(lockfile))
except FileNotFoundError:
    pass
fd = os.open(str(lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
os.chmod(lockfile, 0o644)  # Fix: set correct permissions
return fd, lockfile
```

Add to `src/shenbi/gates/g4/decisions_validator.py`:

```python
def _check_adjacent_budget(project_dir: Path, chapter: int) -> list[str]:
    """Check if adjacent chapter decision budgets are identical.

    Identical budgets across adjacent chapters suggest copy-paste without
    per-chapter recalculation. This is a WARN-level check.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Current chapter number.

    Returns:
        List of issue strings (WARN level, not HARD).
    """
    if chapter <= 1:
        return []

    prev_path = project_dir / "chapters" / f"chapter-{chapter - 1}-decisions.json"
    curr_path = project_dir / "chapters" / f"chapter-{chapter}-decisions.json"

    if not prev_path.exists() or not curr_path.exists():
        return []

    try:
        prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
        curr_data = json.loads(curr_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    prev_budget = prev_data.get("budget", {})
    curr_budget = curr_data.get("budget", {})

    if prev_budget and curr_budget and prev_budget == curr_budget:
        return [f"G4.dec.budget_unchanged: chapters {chapter-1}-{chapter}"]

    return []
```

Register this check in the decisions_validator G4 function so it runs alongside other decisions checks.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_safe_write.py tests/unit/gates/g4/test_decisions_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_safe_write.py tests/unit/gates/g4/test_decisions_validator.py src/shenbi/safe_write.py src/shenbi/gates/g4/decisions_validator.py
git commit -m "fix: set lockfile permissions to 0o644 and add adjacent-chapter budget comparison"
```

---
