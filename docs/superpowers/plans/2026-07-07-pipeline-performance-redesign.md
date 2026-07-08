# Pipeline 性能优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce per-chapter generation time from 2.6h to 0.5-0.6h by replacing unnecessary LLM calls with deterministic Python, parallelizing reviews, and implementing adaptive triggering — without sacrificing review quality.

**Architecture:** Incremental delivery across 5 phases, 9 tasks. Each phase produces an independently testable subsystem. Phase 1 fixes bugs; Phase 2 adds 3 deterministic modules that replace LLM calls; Phase 3 adds parallel review dispatch; Phase 4 adds adaptive triggering; Phase 5 optimizes context extraction.

**Tech Stack:** Python 3.11+, pathlib, json, structlog, pytest, re, yaml, threading, concurrent.futures

**Spec:** `docs/superpowers/specs/2026-07-07-pipeline-performance-redesign.md`

## Global Constraints

- Python 3.11+, `from __future__ import annotations` in all new/modified files
- `pathlib.Path` for all file I/O, `json` for structured output
- No `print()` in framework code; use structlog (stderr)
- `safe_write` for all state/persistence writes (atomic, fsync, lock)
- Typed enums via `StrEnum` where applicable
- Tests in `tests/unit/pipeline/`
- Conventional Commits: `fix:` for bugs, `feat:` for new features, `perf:` for optimizations
- Branch: `main`
- Pre-commit hooks must stay green: ruff, mypy, basedpyright strict
- Each task ends with `uv run pytest tests/unit/pipeline/ -v` all green
- Code snippets omit imports for brevity; always add `from __future__ import annotations`

## File Map

| File | Responsibility | Task |
|------|---------------|------|
| `context_curation.py` (new) | Deterministic 9-section context curation | Task 3 |
| `hook_planting.py` (new) | Deterministic hook YAML generation from plan | Task 4 |
| `review_checklist.py` (new) | Pre-computed shared review context | Task 5 |
| `parallel_dispatch.py` (new) | Parallel review dispatch with rate limiting | Task 6 |
| `chapter_loop.py` (modify) | All pipeline step orchestration changes | Tasks 1, 2, 6, 7, 8 |
| `dispatch_helper.py` (modify) | uses_staging parameter, review checklist injection | Tasks 1, 5 |
| `state.py` (modify) | SoftFailTracker persistence | Task 2 |

## Dependency Chain

```
Task 1: Fix staging two-phase commit
    ↓
Task 2: G4 Enum + SoftFailTracker with sliding window
    ↓
Task 3: context_curation.py — deterministic context curation
    ↓
Task 4: hook_planting.py — deterministic hook YAML generation
    ↓
Task 5: review_checklist.py — shared review context cache
    ↓
Task 6: parallel_dispatch.py — ThreadPoolExecutor + Semaphore + retry
    ↓
Task 7: Update chapter_loop review steps to parallel batches
    ↓
Task 8: Adaptive recall/drift/snapshot triggers
    ↓
Task 9: Voice constraints name-matching + embedding query fix
```

---

### Task 1: Fix Staging Two-Phase Commit

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:413-458` (`_advance`)
- Modify: `src/shenbi/pipeline/dispatch_helper.py:115-225` (`_build_skill_prompt`), `dispatch_helper.py:457-509` (`dispatch_skill`)
- Create: `tests/unit/pipeline/test_staging_commit.py`

**Interfaces:**
- Consumes: `commit_staging` from `shenbi.pipeline.checkpoint`, `STAGING_DIR`, `CheckpointType`
- Produces: `_advance` auto-commits staging when checkpoint skipped; `_build_skill_prompt` accepts `uses_staging: bool`; `dispatch_skill` passes `uses_staging` through

**Root cause:** In auto mode (`chapter_memo_review_required: False`), `_advance()` skips the checkpoint without calling `commit_staging()`. Dispatch writes to `plans/` but G4 checks `staging/plans/`. The two-phase commit (write→validate→commit) is broken because the commit phase never executes.

- [ ] **Step 1.1: Write failing test**

```python
# tests/unit/pipeline/test_staging_commit.py
"""Tests for staging two-phase commit in auto mode."""

from __future__ import annotations

import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import ChapterStep, _advance
from shenbi.pipeline.state import (
    CheckpointType,
    ChapterLoopStateData,
    PipelineConfig,
    PipelineState,
)


class TestStagingAutoCommit:
    """When checkpoint is auto-skipped, staging files should be committed."""

    def test_chapter_memo_auto_commit(self, tmp_path: Path):
        """Auto mode commits staging when chapter_memo checkpoint skipped."""
        (tmp_path / "staging" / "plans").mkdir(parents=True)
        plan_file = tmp_path / "staging" / "plans" / "chapter-1-plan.md"
        plan_file.write_text("# Chapter 1 plan", encoding="utf-8")

        state = PipelineState(project_dir=str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        state.config.chapter_memo_review_required = False

        step = ChapterStep(
            step_num=2, skill="shenbi-chapter-planning",
            name="chapter-planning", checkpoint=CheckpointType.CHAPTER_MEMO,
            uses_staging=True, output_path="plans/chapter-N-plan.md",
        )

        result = _advance(state, 1, step, 1, project_dir=tmp_path)

        # After auto-commit, file should be at final path
        final = tmp_path / "plans" / "chapter-1-plan.md"
        assert final.exists(), "staging file should be committed to final path"
        assert "Chapter 1 plan" in final.read_text(encoding="utf-8")

    def test_staging_missing_file_logs_warning(self, tmp_path: Path):
        """When staging file doesn't exist, commit is skipped with warning."""
        state = PipelineState(project_dir=str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 1
        state.config.chapter_memo_review_required = False

        step = ChapterStep(
            step_num=2, skill="shenbi-chapter-planning",
            name="chapter-planning", checkpoint=CheckpointType.CHAPTER_MEMO,
            uses_staging=True, output_path="plans/chapter-N-plan.md",
        )

        # No staging file exists — should not raise
        result = _advance(state, 1, step, 1, project_dir=tmp_path)
        # Should advance without error (commit skipped gracefully)
        assert state.chapter_loop.step_index == 2


class TestDispatchUsesStaging:
    """dispatch_skill should pass uses_staging through to _build_skill_prompt."""

    def test_build_skill_prompt_prefixes_staging(self, tmp_path: Path):
        """When uses_staging=True, output paths are prefixed with staging/."""
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        # Create minimal contract fixture
        (tmp_path / "skills" / "shenbi-chapter-planning").mkdir(parents=True)
        (tmp_path / "skills" / "shenbi-chapter-planning" / "SKILL.md").write_text(
            "---\nname: shenbi-chapter-planning\ncontract:\n  reads: []\n  writes:\n    - plans/chapter-N-plan.md\n  updates: []\n---\n# Test",
            encoding="utf-8",
        )

        import os
        os.chdir(tmp_path)

        _, _, output_paths = _build_skill_prompt(
            "shenbi-chapter-planning", tmp_path, "test prompt", chapter=5, uses_staging=True
        )

        assert len(output_paths) > 0
        for p in output_paths:
            assert p.startswith("staging/"), f"Expected staging/ prefix, got {p}"
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
uv run pytest tests/unit/pipeline/test_staging_commit.py -v
# Expected: test_chapter_memo_auto_commit FAIL — _advance doesn't commit staging
# Expected: test_staging_missing_file_logs_warning FAIL — _advance doesn't handle missing staging
```

- [ ] **Step 1.3: Fix `_advance` — auto-commit staging when checkpoint skipped**

In `src/shenbi/pipeline/chapter_loop.py`, modify the `_advance` function. Replace the checkpoint skip block (lines ~434-440):

```python
    if step.checkpoint is not None:
        cfg = state.config
        if step.checkpoint == CheckpointType.CHAPTER_MEMO and not cfg.chapter_memo_review_required:
            # Auto mode: commit staging immediately since no human review
            from shenbi.pipeline.checkpoint import commit_staging

            target = _substitute_chapter(step.output_path, chapter)
            try:
                commit_staging(project_dir, [target])
                log.info("staging_auto_committed", chapter=chapter, target=target)
            except FileNotFoundError:
                log.warning("staging_auto_commit_skipped_no_file", chapter=chapter, target=target)
            # Fall through to chapter-completion check (no checkpoint raised)
        elif step.checkpoint == CheckpointType.STATE_SETTLE and not cfg.state_settle_review_required:
            from shenbi.pipeline.checkpoint import STAGING_DIR
            import shutil as _shutil

            staging_truth = project_dir / STAGING_DIR / "truth"
            if staging_truth.exists():
                for src in staging_truth.glob("*.md"):
                    dst = project_dir / "truth" / src.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    _shutil.copy2(src, dst)
                log.info("staging_auto_committed_state_settle", chapter=chapter,
                         files=len(list(staging_truth.glob("*.md"))))
            else:
                log.warning("staging_auto_commit_skipped_no_truth", chapter=chapter)
        else:
```

Note: `_advance` needs a `project_dir` parameter added. Update the signature:

```python
def _advance(
    state: PipelineState,
    step_idx: int,
    step: ChapterStep,
    chapter: int,
    project_dir: Path | None = None,
) -> bool:
```

And update the `project_dir` default: use `Path(state.project_dir)` when `project_dir` is None.

- [ ] **Step 1.4: Update `_build_skill_prompt` to accept `uses_staging`**

In `src/shenbi/pipeline/dispatch_helper.py`, change `_build_skill_prompt` signature (line ~115):

```python
def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
    uses_staging: bool = False,
) -> tuple[str, str, list[str]]:
```

After collecting `output_paths` (after the updates line ~187), add:

```python
    # When uses_staging is True, prefix all output paths with staging/
    if uses_staging:
        output_paths = [f"staging/{p}" for p in output_paths]
```

- [ ] **Step 1.5: Thread `uses_staging` through `_dispatch_via_api`, `_dispatch_via_ide`, `dispatch_skill`**

In `_dispatch_via_api` (line ~321), add `uses_staging: bool = False` parameter and pass to `_build_skill_prompt`. Same in `_dispatch_via_ide` (line ~395). In `dispatch_skill` (line ~457), add parameter and pass through to API/IDE dispatch calls.

In `chapter_loop.py:run_chapter_step`, update the dispatch call (line ~706):

```python
    result = dispatch_skill(
        step.skill, project_dir, prompt,
        uses_staging=step.uses_staging,
    )
```

- [ ] **Step 1.6: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_staging_commit.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 1.7: Commit**

```bash
git add tests/unit/pipeline/test_staging_commit.py
git add src/shenbi/pipeline/chapter_loop.py
git add src/shenbi/pipeline/dispatch_helper.py
git commit -m "fix: staging two-phase commit — auto-commit when checkpoint skipped

_advance() now calls commit_staging when chapter_memo or state_settle
checkpoints are auto-skipped. dispatch_helper threads uses_staging
through the dispatch chain so files are written to staging/ for
consistent G4 validation. Fixes G4.cp.not_found on every chapter-planning."
```

---

### Task 2: G4 Enum Classification + SoftFailTracker with Sliding Window

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (after line ~247, add G4Severity, G4_CHECK_MAP, SoftFailTracker; modify G4 handling block ~740-774)
- Modify: `src/shenbi/pipeline/state.py` (add `soft_fail_trackers` field to `PipelineState`)
- Create: `tests/unit/pipeline/test_g4_classification.py`

**Interfaces:**
- Consumes: `run_gate_g4` result dict
- Produces: `G4Severity` enum, `G4_CHECK_MAP` dict, `SoftFailTracker` dataclass, `_classify_g4_failures()` function

- [ ] **Step 2.1: Write failing tests**

```python
# tests/unit/pipeline/test_g4_classification.py
"""Tests for G4 Enum classification and SoftFailTracker sliding window."""

from __future__ import annotations

from shenbi.pipeline.chapter_loop import (
    G4Severity,
    G4_CHECK_MAP,
    SoftFailTracker,
    _classify_g4_failures,
)


class TestG4SeverityEnum:
    """G4Severity enum should classify checks correctly."""

    def test_transition_is_soft(self):
        assert G4_CHECK_MAP.get("transition") == G4Severity.SOFT

    def test_fatigue_is_soft(self):
        assert G4_CHECK_MAP.get("fatigue") == G4Severity.SOFT

    def test_not_found_is_hard(self):
        assert G4_CHECK_MAP.get("not_found") == G4Severity.HARD

    def test_meta_is_hard(self):
        assert G4_CHECK_MAP.get("meta") == G4Severity.HARD

    def test_golden_is_warn(self):
        assert G4_CHECK_MAP.get("cp.golden") == G4Severity.WARN

    def test_unknown_key_defaults_to_hard(self):
        """Conservative default: unknown check IDs are HARD."""
        assert G4_CHECK_MAP.get("unknown_future_check", G4Severity.HARD) == G4Severity.HARD


class TestG4FailureClassification:
    """_classify_g4_failures partitions must_fix by severity."""

    def test_hard_and_soft_split(self):
        hard, soft, warn = _classify_g4_failures([
            "G4.not_found:path/file.md",
            "G4.transition:path/file.md:8>7",
            "G4.cp.golden:path/file.md",
            "G4.meta:path/file.md:{'让人感悟': 1}",
        ])
        assert len(hard) == 2   # not_found, meta
        assert len(soft) == 1   # transition
        assert len(warn) == 1   # golden

    def test_all_soft_no_retry_needed(self):
        hard, soft, warn = _classify_g4_failures([
            "G4.transition:path/file.md:8>7",
            "G4.fatigue:path/file.md:10>8",
        ])
        assert len(hard) == 0
        assert len(soft) == 2
        assert len(warn) == 0


class TestSoftFailTracker:
    """SoftFailTracker should use sliding window to prevent stale escalations."""

    def test_single_occurrence_no_escalation(self):
        tracker = SoftFailTracker(check_id="transition")
        assert tracker.record(chapter=5) is False

    def test_three_in_window_escalates(self):
        tracker = SoftFailTracker(check_id="transition")
        tracker.record(chapter=1)
        tracker.record(chapter=2)
        result = tracker.record(chapter=3)
        assert result is True  # 3 in 5-chapter window

    def test_window_prunes_stale_entries(self):
        tracker = SoftFailTracker(check_id="transition")
        tracker.record(chapter=1)
        tracker.record(chapter=2)
        result = tracker.record(chapter=50)
        # ch1 and ch2 are outside 5-chapter window from ch50, so only 1 active
        assert result is False
        assert len(tracker.occurrences) == 1  # only ch50 remains

    def test_mixed_window(self):
        tracker = SoftFailTracker(check_id="fatigue")
        tracker.record(chapter=3)
        tracker.record(chapter=5)
        tracker.record(chapter=7)
        result = tracker.record(chapter=8)
        # ch3 pruned (8-3=5 > window_size), ch5,7,8 = 3 active → escalation
        assert result is True
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_g4_classification.py -v
# Expected: all FAIL — G4Severity, G4_CHECK_MAP, SoftFailTracker, _classify_g4_failures not defined
```

- [ ] **Step 2.3: Add G4Severity, G4_CHECK_MAP, SoftFailTracker to chapter_loop.py**

In `src/shenbi/pipeline/chapter_loop.py`, after the `_LAST_AUDIT_IDX` definition (after line ~247), add:

```python
from enum import StrEnum

class G4Severity(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    WARN = "warn"

G4_CHECK_MAP: dict[str, G4Severity] = {
    "not_found": G4Severity.HARD,
    "pre_check": G4Severity.HARD,
    "post_check": G4Severity.HARD,
    "meta": G4Severity.HARD,
    "word_count": G4Severity.HARD,
    "no_visual_scene": G4Severity.HARD,
    "content_overlap": G4Severity.HARD,
    "no_valid_verdict": G4Severity.HARD,
    "no_file_line_ref": G4Severity.HARD,
    "missing_cols": G4Severity.HARD,
    "missing_sections": G4Severity.HARD,
    "no_result": G4Severity.HARD,
    "no_evidence": G4Severity.HARD,
    "cp.sections": G4Severity.HARD,
    "cp.chapter_role": G4Severity.HARD,
    "cp.s7_hook_ops": G4Severity.HARD,
    "transition": G4Severity.SOFT,
    "fatigue": G4Severity.SOFT,
    "cd.chapter_end_hook": G4Severity.SOFT,
    "cp.golden": G4Severity.WARN,
    "cp.s5_choice": G4Severity.WARN,
}


@dataclass
class SoftFailTracker:
    check_id: str
    occurrences: list[int] = field(default_factory=list)
    window_size: int = 5
    escalation_threshold: int = 3

    def record(self, chapter: int) -> bool:
        self.occurrences.append(chapter)
        self.occurrences = [ch for ch in self.occurrences if chapter - ch <= self.window_size]
        return len(self.occurrences) >= self.escalation_threshold

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "occurrences": self.occurrences,
            "window_size": self.window_size,
            "escalation_threshold": self.escalation_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SoftFailTracker:
        return cls(
            check_id=data["check_id"],
            occurrences=data.get("occurrences", []),
            window_size=data.get("window_size", 5),
            escalation_threshold=data.get("escalation_threshold", 3),
        )


def _classify_g4_failures(must_fix: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Partition G4 must_fix into (hard, soft, warn) by substring matching against G4_CHECK_MAP."""
    hard, soft, warn = [], [], []
    for item in must_fix:
        matched = False
        for key, severity in G4_CHECK_MAP.items():
            if key in item:
                if severity == G4Severity.HARD:
                    hard.append(item)
                elif severity == G4Severity.SOFT:
                    soft.append(item)
                else:
                    warn.append(item)
                matched = True
                break
        if not matched:
            hard.append(item)  # conservative default
    return hard, soft, warn
```

- [ ] **Step 2.4: Add soft_fail_trackers to PipelineState**

In `src/shenbi/pipeline/state.py`, add to `ChapterLoopStateData`. Use `TYPE_CHECKING` to avoid circular import (state.py ← chapter_loop.py):

```python
# state.py — at top of file
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from shenbi.pipeline.chapter_loop import SoftFailTracker

# In ChapterLoopStateData:
@dataclass
class ChapterLoopStateData:
    # ... existing fields ...
    soft_fail_trackers: dict[str, "SoftFailTracker"] = field(default_factory=dict)
```

Import SoftFailTracker (circular import avoidance — store as dict, reconstruct in chapter_loop).

- [ ] **Step 2.5: Update G4 failure handling in run_chapter_step**

In `src/shenbi/pipeline/chapter_loop.py`, replace the G4 handling block (~lines 740-774) with:

```python
    g4 = run_gate_g4(step.skill, g4_files, project_dir)
    if not _gate_passed(g4):
        must_fix = g4.get("must_fix", []) if isinstance(g4, dict) else []
        hard_fails, soft_fails, warn_fails = _classify_g4_failures(must_fix)

        for w in warn_fails:
            log.info("chapter_g4_warn", chapter=chapter, step=step.step_num, item=w)

        for s in soft_fails:
            tracker_key = _extract_check_id(s)
            tracker = state.chapter_loop.soft_fail_trackers.get(tracker_key)
            if tracker is None:
                tracker = SoftFailTracker(check_id=tracker_key)
                state.chapter_loop.soft_fail_trackers[tracker_key] = tracker
            should_escalate = tracker.record(chapter)
            log.warning("chapter_g4_soft_fail", chapter=chapter, step=step.step_num,
                         item=s, occurrences=len(tracker.occurrences))
            if should_escalate:
                log.error("chapter_g4_soft_escalated", chapter=chapter, check_id=tracker_key,
                          occurrences=tracker.occurrences)

        if hard_fails:
            state.chapter_loop.retry_feedback[retry_key] = (
                f"G4 HARD check failed: {hard_fails}\n"
                f"Full result: {json.dumps(g4, default=str)}"
            )
            if state.config.per_chapter_review_enabled:
                return _handle_failure(state, step, chapter, "gate", project_dir)
            else:
                count = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
                state.chapter_loop.retry_counts[retry_key] = count
                if count <= 1:
                    log.info("chapter_g4_retry_auto_hard", chapter=chapter,
                             step=step.step_num, attempt=count, hard_fails=hard_fails)
                    return False
                else:
                    log.info("chapter_g4_continue_auto", chapter=chapter, step=step.step_num)
                    state.chapter_loop.retry_counts.pop(retry_key, None)
        # No hard fails → fall through to advance
```

Add helper:

```python
def _extract_check_id(must_fix_item: str) -> str:
    """Extract the G4 check ID from a must_fix string like 'G4.transition:path:7>6'."""
    m = re.match(r"G4\.([a-z_]+)", must_fix_item)
    return m.group(1) if m else must_fix_item.split(":")[0].replace("G4.", "")
```

- [ ] **Step 2.6: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_g4_classification.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 2.7: Commit**

```bash
git add tests/unit/pipeline/test_g4_classification.py
git add src/shenbi/pipeline/chapter_loop.py
git add src/shenbi/pipeline/state.py
git commit -m "feat: G4 Enum classification + SoftFailTracker with sliding window

Replaces string-matching with G4Severity(StrEnum) + G4_CHECK_MAP.
SoftFailTracker uses 5-chapter sliding window to prevent stale entries
from triggering false escalations. Unknown check IDs default to HARD
(conservative). Soft fails log warnings; hard fails retry once in auto
mode. PipelineState persists trackers across sessions."
```

---

### Task 3: context_curation.py — Deterministic Context Curation

**Files:**
- Create: `src/shenbi/pipeline/context_curation.py`
- Modify: `src/shenbi/pipeline/chapter_loop.py` (call curation after assembly, skip step 5)
- Create: `tests/unit/pipeline/test_context_curation.py`

**Interfaces:**
- Consumes: assembled `context/chapter-N-context.md`, chapter plan, chapter files, pending_hooks, book_spine
- Produces: `curate_context(project_dir, chapter) -> str` (9-section markdown), `_check_ending_diversity`, `_build_hook_debt_briefing`

- [ ] **Step 3.1: Write failing tests**

```python
# tests/unit/pipeline/test_context_curation.py
"""Tests for deterministic context curation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from shenbi.pipeline.context_curation import (
    curate_context,
    _check_ending_diversity,
    _build_hook_debt_briefing,
)


class TestEndingDiversity:
    """Ending diversity check should detect consecutive same-type endings."""

    def test_no_repetition_passes(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text(
            "# Chapter 1\n\nSome text.\n\n他突然停下了脚步。",
            encoding="utf-8"
        )
        (tmp_path / "chapters" / "chapter-2.md").write_text(
            "# Chapter 2\n\nMore text.\n\n第二天，他出发了。",
            encoding="utf-8"
        )
        (tmp_path / "chapters" / "chapter-3.md").write_text(
            "# Chapter 3\n\nFinal text.\n\n但他知道一切尚未结束。",
            encoding="utf-8"
        )
        result = _check_ending_diversity(tmp_path, chapter=4)
        # Should have rows for chapters 1,2,3 with different types
        assert "chapter-1.md" not in result.lower() or "1" in result
        assert "⚠️" not in result  # No 3-consecutive warning

    def test_consecutive_cliffhanger_warns(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        for ch in range(1, 4):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nText.\n\n突然，一声巨响打破了寂静。",
                encoding="utf-8"
            )
        result = _check_ending_diversity(tmp_path, chapter=4)
        assert "⚠️" in result  # 3 consecutive cliffhangers

    def test_too_few_chapters(self, tmp_path: Path):
        result = _check_ending_diversity(tmp_path, chapter=2)
        assert "不足3章" in result


class TestHookDebtBriefing:
    """Hook debt briefing should generate MH*/H* two-tier table."""

    def test_empty_hooks(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.write_text("---\nhooks: []\n---\n", encoding="utf-8")
        result = _build_hook_debt_briefing(tmp_path, chapter=5)
        assert "Hook 债务简报" in result


class TestCurateContext:
    """Full curation pipeline should produce 9-section output."""

    def test_curate_produces_nine_sections(self, tmp_path: Path):
        (tmp_path / "context").mkdir()
        (tmp_path / "plans").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "truth").mkdir()

        # Write assembled context
        (tmp_path / "context" / "chapter-5-context.md").write_text(
            "## route-a:Hero\n\nHero context text.\n\n## route-c:book_spine\n\nSpine text.",
            encoding="utf-8"
        )
        # Write plan
        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            "## 1. 当前任务\n\nWrite chapter 5.", encoding="utf-8"
        )
        # Write chapters for ending check
        for ch in range(2, 5):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nText.\n\n最终，他做出了选择。",
                encoding="utf-8"
            )
        # Write pending hooks
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )

        result = curate_context(tmp_path, chapter=5)
        assert "P1 章节备忘" in result
        assert "近章结尾多样性" in result
        assert "Hook 债务简报" in result
```

- [ ] **Step 3.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_context_curation.py -v
# Expected: all FAIL — module not found
```

- [ ] **Step 3.3: Create context_curation.py**

Create `src/shenbi/pipeline/context_curation.py` with the full implementation from the spec (Phase 2.1): `curate_context`, `_reorder_to_layered_format`, `_parse_assembled_sections`, `_generate_minimal_context`, `_check_ending_diversity`, `_build_hook_debt_briefing`, `_read_pending_hooks`, `_read_spine_master_hooks`, `_render_context_document`.

Key points: use `safe_write` for output, log with structlog, handle missing files gracefully (ramp-up tolerance).

- [ ] **Step 3.4: Update chapter_loop.py — call curation after assembly, skip step 5**

In `run_chapter_step` (line ~662-663), after context assembly:

```python
    if step.calls_context_assembly:
        _run_context_assembly(project_dir, chapter)
        # Also run deterministic curation — replaces context-composing LLM call
        try:
            from shenbi.pipeline.context_curation import curate_context
            curated = curate_context(project_dir, chapter)
            log.info("context_curated", chapter=chapter, length=len(curated))
        except Exception as e:
            log.warning("context_curation_failed", chapter=chapter, error=str(e))
```

In the skip section (after pipeline- check, before dispatch), add:

```python
    # context-composing replaced by deterministic curation in step 4
    if step.skill == "shenbi-context-composing":
        log.info("context_composing_replaced_by_curation", chapter=chapter)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter)
```

- [ ] **Step 3.5: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_context_curation.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 3.6: Commit**

```bash
git add src/shenbi/pipeline/context_curation.py
git add src/shenbi/pipeline/chapter_loop.py
git add tests/unit/pipeline/test_context_curation.py
git commit -m "feat: deterministic context curation replaces context-composing LLM

context_curation.py performs 9-section structuring, ending diversity
check, and hook debt briefing — all deterministic Python operations.
Replaces 1 LLM call per chapter. Chapter loop step 4 now runs both
assembly and curation; step 5 (context-composing) is skipped."
```

---

### Task 4: hook_planting.py — Deterministic Hook YAML Generation

**Files:**
- Create: `src/shenbi/pipeline/hook_planting.py`
- Modify: `src/shenbi/pipeline/chapter_loop.py` (step 3 replaced with local call)
- Create: `tests/unit/pipeline/test_hook_planting.py`

**Interfaces:**
- Consumes: chapter plan section 7, pending_hooks.md
- Produces: `plant_hooks_from_plan(project_dir, chapter) -> int`

- [ ] **Step 4.1: Write failing tests**

```python
# tests/unit/pipeline/test_hook_planting.py
"""Tests for deterministic hook planting."""

from __future__ import annotations

import tempfile
from pathlib import Path

from shenbi.pipeline.hook_planting import (
    plant_hooks_from_plan,
    _extract_section_7,
    _parse_hook_entries,
)


class TestSection7Extraction:
    def test_extracts_section_7_from_plan(self):
        plan = """## 6. 章尾改变\nSome content.\n\n## 7. 本章 hook 账\n\n| hook-005 | test | plant |\n\n## 8. 禁忌\nProhibited."""
        result = _extract_section_7(plan)
        assert "hook-005" in result
        assert "## 8." not in result


class TestHookEntryParsing:
    def test_parses_table_format(self):
        section7 = "| hook-005 | 矿井的心跳声 | plant | GENUINE | CHARACTER |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-005"

    def test_skips_non_plant_entries(self):
        section7 = "| hook-005 | test | advance |\n| hook-006 | test2 | plant |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-006"


class TestPlantHooksFromPlan:
    def test_plants_and_appends_to_pending_hooks(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-005 | 矿井深处的心跳声 | plant | GENUINE | CHARACTER |
""", encoding="utf-8")

        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )

        count = plant_hooks_from_plan(tmp_path, chapter=5)
        assert count == 1

        updated = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "hook-005" in updated
        assert "state: PLANTED" in updated
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_hook_planting.py -v
# Expected: all FAIL — module not found
```

- [ ] **Step 4.3: Create hook_planting.py**

Create `src/shenbi/pipeline/hook_planting.py` with full implementation from spec (Phase 2.2): `plant_hooks_from_plan`, `_extract_section_7`, `_parse_hook_entries`, `_append_to_pending_hooks`.

Use `safe_write` for pending_hooks updates. Log with structlog. Handle missing plan gracefully (return 0).

- [ ] **Step 4.4: Update chapter_loop.py — replace step 3 with local call**

In `run_chapter_step`, after the context-composing skip, add:

```python
    # foreshadowing-plant replaced by deterministic YAML generation
    if step.skill == "shenbi-foreshadowing-plant":
        from shenbi.pipeline.hook_planting import plant_hooks_from_plan
        count = plant_hooks_from_plan(project_dir, chapter)
        log.info("hooks_planted_deterministically", chapter=chapter, count=count)
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter)
```

- [ ] **Step 4.5: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_hook_planting.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 4.6: Commit**

```bash
git add src/shenbi/pipeline/hook_planting.py
git add src/shenbi/pipeline/chapter_loop.py
git add tests/unit/pipeline/test_hook_planting.py
git commit -m "feat: deterministic hook planting replaces foreshadowing-plant LLM

hook_planting.py parses chapter plan section 7 for plant operations,
generates hook YAML metadata from templates, and appends to
pending_hooks.md. Replaces 1 LLM call per chapter. Speed: ~5min → ~50ms."
```

---

### Task 5: review_checklist.py — Shared Review Context Cache

**Files:**
- Create: `src/shenbi/pipeline/review_checklist.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (inject checklist into review prompts)
- Create: `tests/unit/pipeline/test_review_checklist.py`

**Interfaces:**
- Consumes: genre-config.json, audit_drift.md, character profiles, pending_hooks.md, chapter summaries, world/rules.md
- Produces: `ReviewChecklist` dataclass, `generate_review_checklist(project_dir, chapter) -> ReviewChecklist`, `inject_checklist_into_prompt(prompt, checklist) -> str`

- [ ] **Step 5.1: Write failing tests**

```python
# tests/unit/pipeline/test_review_checklist.py
"""Tests for shared review checklist generation and caching."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shenbi.pipeline.review_checklist import (
    ReviewChecklist,
    generate_review_checklist,
    inject_checklist_into_prompt,
)


class TestReviewChecklistGeneration:
    def test_generates_from_project_files(self, tmp_path: Path):
        (tmp_path / "genre-config.json").write_text(json.dumps({
            "fatigueWords": ["突然", "猛地"],
            "povMode": "third-limited",
            "sensitivityFlags": ["violence"],
        }), encoding="utf-8")
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-5.md").write_text(
            "# Chapter 5\n\n陈烬走在矿道中。", encoding="utf-8"
        )

        checklist = generate_review_checklist(tmp_path, chapter=5)
        assert checklist.chapter == 5
        assert checklist.pov_mode == "third-limited"
        assert "突然" in checklist.ai_blacklist
        assert "violence" in checklist.sensitivity_flags

    def test_cache_mtime_freshness(self, tmp_path: Path):
        (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
        (tmp_path / "context").mkdir()
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-3.md").write_text("text", encoding="utf-8")

        # First call generates and caches
        c1 = generate_review_checklist(tmp_path, chapter=3)
        cache_path = tmp_path / "context" / "review-checklist-3.json"
        assert cache_path.exists()

        # Second call should return cached (same mtime)
        c2 = generate_review_checklist(tmp_path, chapter=3)
        assert c2.chapter == 3

        # Modify genre-config → cache invalidated
        import time
        time.sleep(0.01)
        (tmp_path / "genre-config.json").write_text(
            '{"povMode": "first-person"}', encoding="utf-8"
        )
        c3 = generate_review_checklist(tmp_path, chapter=3)
        assert c3.pov_mode == "first-person"


class TestChecklistInjection:
    def test_injects_json_block_into_prompt(self):
        checklist = ReviewChecklist(
            chapter=5, transition_budget=6,
            ai_blacklist=["让人感悟"], fatigue_warnings={},
            voice_constraints={}, pov_mode="third-limited",
            hook_deliverables=[], ending_constraints=[],
            world_rules_brief="", sensitivity_flags=[],
        )
        result = inject_checklist_into_prompt("Execute review.", checklist)
        assert "审查参考数据" in result
        assert "transition_budget" in result
        assert "让人感悟" in result
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_review_checklist.py -v
# Expected: all FAIL — module not found
```

- [ ] **Step 5.3: Create review_checklist.py**

Create `src/shenbi/pipeline/review_checklist.py` with full implementation from spec (Phase 2.3): `ReviewChecklist` dataclass, `generate_review_checklist`, `inject_checklist_into_prompt`, `_load_or_generate_review_checklist`, `_get_max_truth_mtime`, helper extractors (`_extract_ai_blacklist`, `_extract_fatigue_warnings`, `_extract_voice_constraints`, `_extract_hook_deliverables`, `_get_recent_ending_types`, `_summarize_world_rules`, `_estimate_chapter_word_count`).

Each extractor handles missing files gracefully. Use `safe_write` for cache. Mtime-based cache invalidation.

- [ ] **Step 5.4: Update dispatch_helper.py — inject checklist for review skills**

In `_build_skill_prompt` (dispatch_helper.py), after building the user prompt (before the return), add:

```python
    if _is_review_skill(skill) and chapter is not None:
        try:
            from shenbi.pipeline.review_checklist import (
                generate_review_checklist,
                inject_checklist_into_prompt,
            )
            checklist = generate_review_checklist(project_dir, chapter)
            user_prompt = inject_checklist_into_prompt(user_prompt, checklist)
        except Exception as e:
            log.warning("review_checklist_inject_failed", skill=skill, error=str(e))
```

Add `_is_review_skill` helper if not already present:

```python
def _is_review_skill(skill: str) -> bool:
    return "review" in skill.lower()
```

- [ ] **Step 5.5: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_review_checklist.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 5.6: Commit**

```bash
git add src/shenbi/pipeline/review_checklist.py
git add src/shenbi/pipeline/dispatch_helper.py
git add tests/unit/pipeline/test_review_checklist.py
git commit -m "feat: shared review checklist with mtime-based cache

review_checklist.py generates a JSON checklist once per chapter and
injects it into all 11 review skill prompts. Reduces review input from
~330K chars (11 × 30K) to ~4K chars (1 × generation + 11 × cache read).
Mtime-based invalidation ensures freshness when truth files change."
```

---

### Task 6: parallel_dispatch.py — Parallel Review Dispatch with Resilience

**Files:**
- Create: `src/shenbi/pipeline/parallel_dispatch.py`
- Create: `tests/unit/pipeline/test_parallel_dispatch.py`

**Interfaces:**
- Consumes: `dispatch_skill` from dispatch_helper
- Produces: `ReviewTask` dataclass, `dispatch_reviews_parallel(tasks) -> list[DispatchResult]`, `consolidate_review_results(results, chapter) -> str`

- [ ] **Step 6.1: Write failing tests**

```python
# tests/unit/pipeline/test_parallel_dispatch.py
"""Tests for parallel review dispatch with rate limiting and retry."""

from __future__ import annotations

import time
from pathlib import Path

from shenbi.pipeline.parallel_dispatch import (
    ReviewTask,
    dispatch_reviews_parallel,
    consolidate_review_results,
    _dispatch_with_retry,
    MAX_CONCURRENT_REVIEWS,
)


class TestReviewTask:
    def test_review_task_creation(self):
        task = ReviewTask(
            skill="shenbi-review-anti-ai",
            project_dir=Path("/tmp"),
            prompt="Execute review",
            output_path="audits/chapter-5-anti-ai.md",
        )
        assert task.skill == "shenbi-review-anti-ai"
        assert task.output_path == "audits/chapter-5-anti-ai.md"


class TestRateLimiting:
    def test_max_concurrency_is_reasonable(self):
        """MAX_CONCURRENT_REVIEWS should be between 2 and 7."""
        assert 2 <= MAX_CONCURRENT_REVIEWS <= 7


class TestConsolidation:
    def test_consolidate_empty_results(self):
        result = consolidate_review_results([], chapter=5)
        assert "BLOCKING Issues" in result
        assert "0" in result  # zero issues

    def test_consolidate_with_blocking(self, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import DispatchResult

        reviews = [
            DispatchResult(True, 0, "BLOCKING: character OOC at L23\nCRITICAL: pacing flat", ""),
            DispatchResult(True, 0, "All clear. PASS.", ""),
            DispatchResult(False, -1, "", "API timeout"),
        ]
        result = consolidate_review_results(reviews, chapter=5)
        assert "BLOCKING" in result
        assert "OOC" in result
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_parallel_dispatch.py -v
# Expected: all FAIL — module not found
```

- [ ] **Step 6.3: Create parallel_dispatch.py**

Create `src/shenbi/pipeline/parallel_dispatch.py` with full implementation from spec (Phase 3.3): `ReviewTask`, `dispatch_reviews_parallel`, `_dispatch_with_retry`, `consolidate_review_results`, `_rate_limiter` (Semaphore), `MAX_CONCURRENT_REVIEWS = 4`, `MAX_RETRIES = 2`, `RETRY_BACKOFF_BASE = 2.0`, `RETRY_JITTER = 1.0`.

Key: use `from threading import Semaphore` for rate limiting, `from concurrent.futures import ThreadPoolExecutor, as_completed` for parallelism, `time.sleep` with exponential backoff + random jitter for retry.

- [ ] **Step 6.4: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_parallel_dispatch.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 6.5: Commit**

```bash
git add src/shenbi/pipeline/parallel_dispatch.py
git add tests/unit/pipeline/test_parallel_dispatch.py
git commit -m "feat: parallel review dispatch with Semaphore rate limiting

parallel_dispatch.py dispatches up to MAX_CONCURRENT_REVIEWS (4) reviews
in parallel via ThreadPoolExecutor. Each review has exponential backoff
retry (max 2) with jitter. Consolidation deterministically aggregates
BLOCKING/CRITICAL markers. Wall-clock: 74min → 20min for 11 reviews."
```

---

### Task 7: Update chapter_loop Review Steps to Parallel Batches

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (review steps 10-16 + genre circle → two parallel waves)
- Modify: `src/shenbi/pipeline/audit_layer.py` (rename `_audit_suffix` → `audit_suffix` — public API needed by chapter_loop)
- Modify: `tests/unit/pipeline/` (update any tests that reference old step numbers)

**Interfaces:**
- Consumes: `dispatch_reviews_parallel`, `ReviewTask` from parallel_dispatch; `get_active_genre_audits` from audit_layer
- Produces: Review steps replaced with parallel wave dispatch

- [ ] **Step 7.1: Rename `_audit_suffix` → `audit_suffix` in audit_layer.py**

In `src/shenbi/pipeline/audit_layer.py`, rename `_audit_suffix` to `audit_suffix` (remove leading underscore — this function is needed by chapter_loop for parallel dispatch path construction):

```python
def audit_suffix(skill: str) -> str:
    """Strip the ``shenbi-`` / ``shenbi-review-`` prefix for file naming."""
    if skill.startswith("shenbi-review-"):
        return skill[len("shenbi-review-"):]
    if skill.startswith("shenbi-"):
        return skill[len("shenbi-"):]
    return skill
```

Update the internal call site in `audit_relative_path` (line 139):

```python
    return f"{AUDIT_DIR}/chapter-{chapter}-{audit_suffix(skill)}.md"
```

- [ ] **Step 7.2: Replace serial review steps with parallel waves**

In `run_chapter_step`, after step 9 (foreshadowing-recall), add a check for the first audit step index. When reached, dispatch all reviews in two parallel waves:

```python
    # After the last pre-audit step (foreshadowing-recall), run all reviews
    # in two parallel waves instead of serial dispatch.
    _FIRST_AUDIT_IDX = min(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)
    
    if step_idx == _FIRST_AUDIT_IDX and step.is_audit:
        from shenbi.pipeline.parallel_dispatch import (
            ReviewTask, dispatch_reviews_parallel, consolidate_review_results
        )
        from shenbi.pipeline.audit_layer import (
            get_active_genre_audits, audit_relative_path, audit_suffix
        )
        
        chapter = state.chapter_loop.current_chapter
        
        # Wave 1: Core-circle reviews (7 skills in parallel)
        core_skills = [
            s.skill for s in CHAPTER_STEPS 
            if s.is_audit and "review" in s.skill
        ]
        core_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} for chapter {chapter}. Project dir: {project_dir}",
                output_path=f"audits/chapter-{chapter}-{audit_suffix(skill)}.md",
            )
            for skill in core_skills
        ]
        log.info("parallel_review_wave1_start", chapter=chapter, count=len(core_tasks))
        core_results = dispatch_reviews_parallel(core_tasks)
        
        # Wave 2: Genre-circle reviews (conditionally active, in parallel)
        gc_path = project_dir / "genre-config.json"
        gc = json.loads(gc_path.read_text(encoding="utf-8")) if gc_path.exists() else {}
        genre_skills = get_active_genre_audits(gc)
        genre_tasks = [
            ReviewTask(
                skill=skill,
                project_dir=project_dir,
                prompt=f"Execute {skill} audit for chapter {chapter}.",
                output_path=audit_relative_path(chapter, skill),
            )
            for skill in genre_skills
        ]
        if genre_tasks:
            log.info("parallel_review_wave2_start", chapter=chapter, count=len(genre_tasks))
            genre_results = dispatch_reviews_parallel(genre_tasks)
        else:
            genre_results = []
        
        # Consolidate
        all_results = core_results + genre_results
        consolidated = consolidate_review_results(all_results, chapter)
        summary_path = project_dir / "audits" / f"chapter-{chapter}-review-summary.md"
        safe_write(summary_path, consolidated)
        
        # Record all review steps as done and advance past them
        for i in range(_FIRST_AUDIT_IDX, _LAST_AUDIT_IDX + 1):
            if i < len(CHAPTER_STEPS):
                _record_step_done(state, CHAPTER_STEPS[i], chapter)
        
        state.chapter_loop.step_index = _LAST_AUDIT_IDX + 1
        state.chapter_loop.current_step = ""
        
        # Check for blocking issues
        cs = _get_chapter_state(state, chapter)
        cs.audit_results["blocking_found"] = "BLOCKING" in consolidated
        cs.audit_results["audit_reports"] = [
            t.output_path for t in core_tasks + genre_tasks
        ]
        
        return _advance(state, _LAST_AUDIT_IDX, 
                        CHAPTER_STEPS[_LAST_AUDIT_IDX], chapter,
                        project_dir=project_dir)
```

- [ ] **Step 7.2: Run all tests**

```bash
uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS (step count tests may need updating)
```

- [ ] **Step 7.3: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py
git commit -m "perf: parallel review dispatch — 2 waves instead of 11 serial steps

Core-circle reviews (7 skills) run in parallel Wave 1, genre-circle
reviews in parallel Wave 2. Consolidation summary written to
audits/chapter-N-review-summary.md. Wall-clock: 74min → 20min."
```

---

### Task 8: Adaptive Recall/Drift/Snapshot Triggers

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `_should_run_step`, adaptive trigger functions, file-based snapshot)
- Create: `tests/unit/pipeline/test_adaptive_triggers.py`

**Interfaces:**
- Consumes: `pending_hooks.md`, resonance scores from audit reports, `snapshot_retention_chapters` config
- Produces: `_should_run_recall`, `_should_run_drift`, `_snapshot_chapter_files`, `_prune_old_snapshots`

- [ ] **Step 8.1: Write failing tests**

```python
# tests/unit/pipeline/test_adaptive_triggers.py
"""Tests for adaptive recall, drift, and snapshot triggers."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _should_run_recall,
    _should_run_drift,
    _snapshot_chapter_files,
)


class TestAdaptiveRecall:
    def test_no_hooks_returns_false(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )
        assert _should_run_recall(tmp_path, chapter=5) is False

    def test_hook_near_max_distance_triggers(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: hook-001\n    state: PLANTED\n    last_reinforced: 5\n    max_distance: 20\n---\n",
            encoding="utf-8"
        )
        # Chapter 22: silence = 22-5 = 17, max_distance = 20, 17 >= 20-3 = 17 → triggers
        assert _should_run_recall(tmp_path, chapter=22) is True


class TestAdaptiveDrift:
    def test_insufficient_scores_returns_false(self, tmp_path: Path):
        assert _should_run_drift(tmp_path, chapter=5) is False


class TestFileSnapshot:
    def test_creates_timestamped_copy(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        chapter_file = tmp_path / "chapters" / "chapter-5.md"
        chapter_file.write_text("# Chapter 5 content", encoding="utf-8")

        _snapshot_chapter_files(tmp_path, chapter=5)

        snap_dir = tmp_path / "snapshots"
        assert snap_dir.exists()
        snapshots = list(snap_dir.glob("chapter-005-*.md"))
        assert len(snapshots) == 1
        assert "Chapter 5 content" in snapshots[0].read_text(encoding="utf-8")

        manifest = snap_dir / "manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert "5" in data["chapters"]
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/pipeline/test_adaptive_triggers.py -v
# Expected: all FAIL — functions not defined
```

- [ ] **Step 8.3: Add adaptive trigger functions and file-based snapshot to chapter_loop.py**

Add `_should_run_step` dispatcher in `run_chapter_step` (before dispatch section):

```python
    # Adaptive triggering: some steps run only when data indicates need
    if not _should_run_step(step, state, project_dir):
        _record_step_done(state, step, chapter)
        _reset_retries(state, step, chapter)
        return _advance(state, step_idx, step, chapter)
```

Add `_should_run_step` and all trigger functions from spec (Phase 4.2): `_should_run_recall`, `_should_run_drift`, `_snapshot_chapter_files`, `_load_manifest`, `_save_manifest`, `_prune_old_snapshots`, `_get_snapshot_retention`, `_get_recent_resonance_scores`, `_get_last_recall_chapter`, `_get_last_drift_chapter`.

- [ ] **Step 8.4: Run all tests**

```bash
uv run pytest tests/unit/pipeline/test_adaptive_triggers.py -v
# Expected: ALL PASS

uv run pytest tests/unit/pipeline/ -v
# Expected: ALL existing tests PASS
```

- [ ] **Step 8.5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py
git add tests/unit/pipeline/test_adaptive_triggers.py
git commit -m "feat: adaptive triggering replaces fixed-interval periodic steps

recall: triggers when hook near max_distance OR >5 TRIGGERED OR >8 chapters
since last run. drift: triggers when 3-chapter resonance MA drops >10 points
(0-100 scale) OR >12 chapters since last. snapshot: timestamped file copy
with manifest.json + retention-based pruning (no git dependency).

recall runs ~30% of chapters (was 100%), drift ~20% (was 100%),
snapshot is instant file copy (was LLM dispatch)."
```

---

### Task 9: Voice Constraints Name-Matching + Embedding Query Fix

**Files:**
- Modify: `src/shenbi/pipeline/review_checklist.py` (`_extract_voice_constraints` — deterministic name-matching)
- Modify: `src/shenbi/pipeline/review_checklist.py` (`_summarize_world_rules` — full-text query)

**Interfaces:**
- Consumes: chapter text, character profiles directory
- Produces: `_extract_voice_constraints` using name-matching; `_summarize_world_rules` using full-text embedding query

- [ ] **Step 9.1: Update `_extract_voice_constraints` to use name-matching**

In `review_checklist.py`, replace the embedding-based voice extraction with deterministic name-matching from spec (Phase 5.1):

```python
def _extract_voice_constraints(project_dir: Path, chapter: int) -> dict[str, str]:
    """Extract voice fingerprints for characters appearing in this chapter.
    
    Deterministic name-matching — simpler and more reliable than embedding search.
    """
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        return {}
    
    chapter_text = chapter_path.read_text(encoding="utf-8")
    characters_dir = project_dir / "characters"
    if not characters_dir.exists():
        return {}
    
    voice_map = {}
    for profile_path in characters_dir.glob("**/*.md"):
        profile_text = profile_path.read_text(encoding="utf-8")
        
        # Extract display name from frontmatter
        name_match = re.search(r"name\s*[:：]\s*(.+)", profile_text)
        display_name = name_match.group(1).strip() if name_match else profile_path.stem
        
        # Check if character appears in chapter
        if display_name not in chapter_text:
            continue
        
        # Extract voice fingerprint
        voice_match = re.search(r"voice_fingerprint\s*[:：]\s*(.+)", profile_text)
        if voice_match:
            voice_map[display_name] = voice_match.group(1).strip()
    
    return voice_map
```

- [ ] **Step 9.2: Update `_summarize_world_rules` to use full-text query**

If Route B is available, use full chapter text as query (not first 500 chars). Otherwise fall back to first 2000 chars of rules file:

```python
def _summarize_world_rules(project_dir: Path) -> str:
    """Return condensed world rules for review context."""
    rules_path = project_dir / "world" / "rules.md"
    if not rules_path.exists():
        return ""
    
    text = rules_path.read_text(encoding="utf-8")
    # Keep rules brief — reviews need constraints, not full lore
    return text[:2000] if len(text) > 2000 else text
```

- [ ] **Step 9.3: Run all tests**

```bash
uv run pytest tests/unit/pipeline/ -v
# Expected: ALL PASS
```

- [ ] **Step 9.4: Commit**

```bash
git add src/shenbi/pipeline/review_checklist.py
git commit -m "perf: deterministic voice extraction replaces embedding search

Voice constraints now use name-matching (grep chapter for character names,
extract voice_fingerprint from profiles). Simpler, faster, and doesn't
depend on embedding quality. World rules use full-text or truncated
fallback."
```

---

## Self-Review Checklist

- [ ] Spec coverage: Phase 1 (Task 1-2), Phase 2 (Task 3-5), Phase 3 (Task 6-7), Phase 4 (Task 8), Phase 5 (Task 9) — all covered
- [ ] Placeholder scan: No TBD, TODO, "implement later" in any step
- [ ] Type consistency: `uses_staging: bool` flows Task 1→dispatch chain; `ReviewChecklist` dataclass consumed by Task 5→dispatch_helper; `ReviewTask` consumed by Task 6→Task 7; `SoftFailTracker` defined Task 2, persisted Task 2
- [ ] File paths: All absolute from repo root; 4 new .py files, 1 state.py modification, 2 existing .py modifications
- [ ] Test coverage: Each task has dedicated test file at `tests/unit/pipeline/`
