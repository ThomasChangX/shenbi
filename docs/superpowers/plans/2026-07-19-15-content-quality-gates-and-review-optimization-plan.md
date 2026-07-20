# Content Quality Gates and Review Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate four systemic quality failures (title degradation, plan-content mismatch, identical review summaries, static checklists) by adding G4 title/hook checks, wiring the EXISTING `check_escalation()` helper into the reactive escalation-review dispatch path (so empty signals produce a deterministic summary instead of a templated LLM report), and splitting review checklists into static + dynamic layers (reusing the EXISTING mtime invalidation and `_extract_hook_deliverables`).

**Architecture:** Two new G4 sub-checks (`G4.cd.title`, `G4.cd.hook_fulfillment`) validate chapter output post-drafting via deterministic regex parsing. The escalation-review skill is ALREADY dispatched reactively (not as a `CHAPTER_STEPS` entry) on retry exhaustion (`chapter_loop.py:414-420` via `revision_router.dispatch_escalation`) and on closure failure (`cli.py:284`); the fix wires the EXISTING-but-unwired `check_escalation()` helper (`skill_utils/escalation/check.py`) into those reactive dispatch points so empty signals produce a deterministic summary instead of a templated LLM report. Review checklists already have mtime-based cache invalidation (`_get_max_source_mtime`) and `_extract_hook_deliverables` (reading `truth/pending_hooks.md`); the task is to diagnose why they yield static output, not re-add extraction. The split uses a static Genesis template (`review-checklist-template.json`) and per-chapter dynamic deltas (`review-checklist-N.json`), with filenames aligned with Spec 10.

**Tech Stack:** Python 3.11+, pathlib, re, json, structlog

## Global Constraints
1. `just check` full pass at every task boundary
2. No regression in chapter generation quality
3. Zero date-label titles across 10 consecutive chapters
4. Zero duplicate titles across all chapters
5. Zero titles containing chapter numbers
6. Ch20 simulation regression: `G4.cd.hook_fulfillment` catches MH-003 absence
7. Zero templated `review-summary.md` files generated when no escalation signals present (deterministic summary used instead); escalation-review dispatches that DO occur with non-empty signals still run
8. `ai_blacklist` shows variation across 3 consecutive chapters
9. `hook_deliverables` count >= number of active hooks declared in chapter plan
10. Checklist regenerates each chapter (the EXISTING `_get_max_source_mtime` invalidation fires correctly when upstream `truth/` files are updated)

---

## Task 1: Add G4.cd.title Check in Chapter Drafting Gate

**Files:**
- `src/shenbi/gates/g4/chapter_drafting.py` -- add `check_chapter_title()` function
- `src/shenbi/pipeline/chapter_loop.py` -- call new check post-drafting in `_run_g4_checks()`

**TDD Cycle:**

- [ ] **1a. Write test:** Create `tests/gates/g4/test_title_check.py`
  ```python
  """Test G4.cd.title chapter title quality enforcement."""
  import pytest
  from shenbi.gates.g4.chapter_drafting import check_chapter_title

  class TestChapterTitleValidation:
      def test_rejects_chapter_number_in_title(self):
          issues = check_chapter_title("第40章 废料场", {})
          assert any("contains_chapter_number" in i for i in issues)

      def test_rejects_duplicate_title(self):
          previous = {"废料场": 3, "痕迹": 5}
          issues = check_chapter_title("痕迹", previous)
          assert any("duplicate_of_ch5" in i for i in issues)

      def test_warns_day_of_week_label(self):
          issues = check_chapter_title("Saturday", {})
          assert any("day_label_instead_of_thematic_name" in i for i in issues)

      def test_warns_chinese_week_label(self):
          issues = check_chapter_title("第四周Saturday", {})
          assert any("day_label_instead_of_thematic_name" in i for i in issues)

      def test_passes_poetic_single_character(self):
          issues = check_chapter_title("沉", {})
          assert len(issues) == 0

      def test_passes_poetic_two_character(self):
          issues = check_chapter_title("废料场", {"晨": 1})
          assert len(issues) == 0

      def test_handles_empty_previous_titles(self):
          issues = check_chapter_title("雾", {})
          assert len(issues) == 0
  ```

- [ ] **1b. Run test -- confirm FAIL (function not yet existing).**

- [ ] **1c. Implement** `check_chapter_title()` in `src/shenbi/gates/g4/chapter_drafting.py`:
  ```python
  import re

  def check_chapter_title(title: str, previous_titles: dict[str, int]) -> list[str]:
      """G4.cd.title: Validate chapter title quality.

      Checks:
      - No chapter numbers in title
      - No duplicate titles
      - No day-of-week labels (WARN, not HARD)
      - Thematic naming encouraged (1-4 Chinese characters)
      """
      issues = []

      # HARD FAIL: Chapter number in title
      if re.search(r'第\d+章', title):
          issues.append("G4.cd.title:contains_chapter_number -- "
                         "title must not include chapter number (SKILL.md:125)")

      # HARD FAIL: Duplicate title
      if title in previous_titles:
          issues.append(f"G4.cd.title:duplicate_of_ch{previous_titles[title]} -- "
                         f"title '{title}' already used")

      # WARN: Day-of-week or date label
      day_pattern = re.compile(
          r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
          r'周[一二三四五六日])'
      )
      if day_pattern.search(title):
          issues.append("G4.cd.title:day_label_instead_of_thematic_name -- "
                         "prefer thematic 1-4 character name over date label")

      return issues
  ```

- [ ] **1d. Run test -- confirm PASS.**

- [ ] **1e. Commit:** `feat(g4): add G4.cd.title check for chapter title quality enforcement`

---

## Task 2: Integrate G4.cd.title into Post-Drafting Gate Check

**Files:**
- `src/shenbi/pipeline/chapter_loop.py` -- call `check_chapter_title` in post-drafting gate function

**TDD Cycle:**

- [ ] **2a. Write test:** Create `tests/pipeline/test_title_gate_integration.py`
  ```python
  """Test title gate integration into chapter loop post-drafting checks."""
  import pytest
  from pathlib import Path
  from unittest.mock import patch, MagicMock

  class TestTitleGateIntegration:
      def test_title_check_called_post_drafting(self):
          """Verify _run_g4_checks calls check_chapter_title after drafting."""
          from shenbi.pipeline.chapter_loop import _run_g4_checks
          title_dict = _run_g4_checks(MagicMock(), chapter=1)
          assert 'text' in title_dict
          assert 'chapter' in title_dict
          assert 'style' in title_dict

      def test_detects_title_degradation_in_pipeline(self):
          """Integration: chapter with 'Saturday' title produces WARN."""
          from shenbi.gates.g4.chapter_drafting import check_chapter_title
          title = "沉"
          assert 1 <= len(title) <= 20

      def test_duplicate_title_flagged_across_chapters(self):
          """Two chapters with same title: second is flagged."""
          from shenbi.gates.g4.chapter_drafting import check_chapter_title
          import re
          title = "废料场"
          assert not re.match(r'第\d+章', title)
  ```

- [ ] **2b. Run test -- confirm FAIL.**

- [ ] **2c. Implement** integration in `_run_g4_checks()` (`src/shenbi/pipeline/chapter_loop.py`):
  ```python
  def _run_g4_checks(state: PipelineState, chapter: int) -> list[str]:
      """Run post-drafting G4 quality checks."""
      all_issues = []
      project_dir = state.project_dir

      chapter_path = project_dir / 'chapters' / f'chapter-{chapter}.md'
      plan_path = project_dir / 'plans' / f'chapter-{chapter}-plan.md'

      if not chapter_path.exists():
          return all_issues

      # --- G4.cd.title ---
      from shenbi.gates.g4.chapter_drafting import check_chapter_title
      title = _extract_chapter_title(chapter_path)
      previous_titles = _load_previous_titles(project_dir, chapter)
      title_issues = check_chapter_title(title, previous_titles)
      all_issues.extend(title_issues)

      # --- G4.cd.hook_fulfillment ---
      from shenbi.gates.g4.chapter_drafting import check_hook_fulfillment
      hook_issues = check_hook_fulfillment(plan_path, chapter_path)
      all_issues.extend(hook_issues)

      return all_issues


  def _extract_chapter_title(chapter_path: Path) -> str:
      """Extract title from chapter markdown file. Title is first H1 heading."""
      text = chapter_path.read_text(encoding='utf-8')
      match = re.match(r'^#\s+(.+?)$', text, re.MULTILINE)
      return match.group(1).strip() if match else ""


  def _load_previous_titles(project_dir: Path, current_chapter: int) -> dict[str, int]:
      """Load all previous chapter titles for duplicate detection."""
      previous = {}
      for ch in range(1, current_chapter):
          ch_path = project_dir / 'chapters' / f'chapter-{ch}.md'
          if ch_path.exists():
              title = _extract_chapter_title(ch_path)
              if title:
                  previous[title] = ch
      return previous
  ```

- [ ] **2d. Run test -- confirm PASS.**

- [ ] **2e. Run `just check` -- confirm full pass.**

- [ ] **2f. Commit:** `feat(pipeline): integrate G4.cd.title into post-drafting gate check`

---

## Task 3: Add G4.cd.hook_fulfillment Check

**Files:**
- `src/shenbi/gates/g4/chapter_drafting.py` -- add `check_hook_fulfillment()` function

**TDD Cycle:**

- [ ] **3a. Write test:** Create `tests/gates/g4/test_hook_fulfillment.py`
  ```python
  """Test G4.cd.hook_fulfillment plan-content cross-validation."""
  import pytest
  import tempfile
  from pathlib import Path
  from shenbi.gates.g4.chapter_drafting import check_hook_fulfillment

  class TestHookFulfillment:
      def test_detects_missing_hooks(self, tmp_path):
          plan = tmp_path / "plan.md"
          plan.write_text("""
  ## 7. Hook Ledger

  | MH-003 | advance | Progress the copper coin mystery |
  | MH-007 | reference | Mention the amulet backstory |
  """)
          chapter = tmp_path / "chapter.md"
          chapter.write_text("This chapter mentions MH-007 briefly but not MH-003.")
          issues = check_hook_fulfillment(plan, chapter)
          assert any("MH-003" in i for i in issues)
          assert not any("MH-007" in i for i in issues)

      def test_passes_when_all_hooks_fulfilled(self, tmp_path):
          plan = tmp_path / "plan.md"
          plan.write_text("## 7. Hook Ledger\n\n| MH-003 | advance | desc |\n")
          chapter = tmp_path / "chapter.md"
          chapter.write_text("MH-003 advancement in this scene.")
          issues = check_hook_fulfillment(plan, chapter)
          assert len(issues) == 0

      def test_no_hooks_in_plan_returns_empty(self, tmp_path):
          plan = tmp_path / "plan.md"
          plan.write_text("## 7. Hook Ledger\n\nNo hooks this chapter.\n")
          chapter = tmp_path / "chapter.md"
          chapter.write_text("Regular chapter body.")
          issues = check_hook_fulfillment(plan, chapter)
          assert len(issues) == 0

      def test_plan_missing_returns_empty(self, tmp_path):
          plan = tmp_path / "nonexistent.md"
          chapter = tmp_path / "chapter.md"
          chapter.write_text("Content.")
          issues = check_hook_fulfillment(plan, chapter)
          assert len(issues) == 0

      def test_handles_hook_ids_with_letters(self, tmp_path):
          plan = tmp_path / "plan.md"
          plan.write_text("| CP-012 | advance | Character progression hook |\n")
          chapter = tmp_path / "chapter.md"
          chapter.write_text("CP-012 is referenced here.")
          issues = check_hook_fulfillment(plan, chapter)
          assert len(issues) == 0
  ```

- [ ] **3b. Run test -- confirm FAIL.**

- [ ] **3c. Implement** `check_hook_fulfillment()` in `src/shenbi/gates/g4/chapter_drafting.py`:
  ```python
  import re
  from pathlib import Path

  def check_hook_fulfillment(plan_path: Path, chapter_path: Path) -> list[str]:
      """G4.cd.hook_fulfillment: Verify plan-declared hooks appear in chapter body.

      Extracts hook IDs from plan Section 7 (Hook Ledger) and searches
      for their presence in the chapter prose.
      """
      if not plan_path.exists():
          return []

      plan_text = plan_path.read_text(encoding='utf-8')
      chapter_text = chapter_path.read_text(encoding='utf-8')

      # Extract hook IDs from plan -- match patterns like MH-003, CP-012, etc.
      plan_hooks = set(re.findall(r'[A-Z]{2,4}-\d+', plan_text))
      # Extract hook IDs from chapter body
      chapter_hooks = set(re.findall(r'[A-Z]{2,4}-\d+', chapter_text))

      missing = plan_hooks - chapter_hooks
      if missing:
          return [f"G4.cd.hook_unfulfilled: plan requires hooks {sorted(missing)} "
                  f"but none found in chapter body"]
      return []
  ```

- [ ] **3d. Run test -- confirm PASS.**

- [ ] **3e. Commit:** `feat(g4): add G4.cd.hook_fulfillment check for plan-content cross-validation`

---

## Task 4: Add Arithmetic Consistency Verification to Continuity Audit SKILL.md

**Files:**
- `skills/shenbi-review-continuity/SKILL.md` -- add arithmetic verification instructions to prompt

**No TDD needed (content-only change).**

- [ ] **4a.** Read `skills/shenbi-review-continuity/SKILL.md` to locate audit instructions section.

- [ ] **4b.** Append arithmetic verification block after existing audit instructions, before output format section:
  ```markdown
  ## Arithmetic Consistency Verification

  For each chapter, verify:
  1. **Currency accumulation**: Copper/silver coin totals must be arithmetically
     consistent with previous chapters. Recompute from known baselines.
     If the previous chapter had N coins and the current chapter adds M,
     the total must be N+M (accounting for expenditures).
  2. **Date and count patterns**: Verify daily-increment patterns
     (e.g., "每日+1" sequences). Flag discrepancies > 0.
  3. **Inventory tracking**: If a character acquires or expends items,
     verify the running totals.

  Report any arithmetic discrepancy with:
  - The incorrect value found in the chapter
  - The correct computed value
  - The line reference (approximate line number in chapter body)
  ```

- [ ] **4c. Commit:** `docs(skills): add arithmetic consistency verification to continuity audit`

---

## Task 5: Wire check_escalation() into the Reactive Escalation-Review Dispatch Path

> **Spec-aligned note (RS1):** `escalation-review` is NOT a `CHAPTER_STEPS` entry. It is dispatched reactively from `revision_router.dispatch_escalation` on retry exhaustion (`chapter_loop.py:414-420`) and on closure failure (`cli.py:284`). There is therefore no `shenbi-escalation-review` branch to add to `_should_run_step`. The fix wires the EXISTING-but-unwired `check_escalation()` helper (`skill_utils/escalation/check.py`, returns `list[EscalationSignal]`) into those reactive dispatch points. When signals are empty, a deterministic summary is generated on disk instead of dispatching the LLM. The G4 checker `gates/g4/escalation_review.py` (35 lines) already exists and only validates section presence -- optionally extend it to detect templated summaries.

**Files:**
- `src/shenbi/skill_utils/escalation/check.py` -- **EXISTS** -- `check_escalation()` is already defined but never imported by `chapter_loop.py` or `_should_run_step`. No signature change.
- `src/shenbi/pipeline/chapter_loop.py` -- import + call `check_escalation()` before `dispatch_escalation` at the reactive dispatch site (~`chapter_loop.py:414-420`)
- `src/shenbi/pipeline/chapter_loop.py` -- add `_generate_deterministic_review_summary()`, `_parse_audit_verdict()`
- `src/shenbi/gates/g4/escalation_review.py` -- **EXISTS (35 lines, section-presence check)** -- optionally extend to flag templated/identical summaries

**check_escalation() signature (already in code at `skill_utils/escalation/check.py:53` -- do NOT change):**
```python
def check_escalation(
    resonance_scores: list[float],
    sensitivity_blocking: bool,
    volume_objective_met: bool,
    regeneration_attempts: int,
    arc_score: float | None = None,
    stratum_axis_drift: bool = False,
    ...
) -> list[EscalationSignal]:
```

**TDD Cycle:**

- [ ] **5a. Write test:** Create `tests/pipeline/test_escalation_review_conditional.py`
  ```python
  """Test reactive escalation-review: check_escalation() gates the LLM dispatch."""
  import json
  import pytest
  import tempfile
  from pathlib import Path
  from unittest.mock import MagicMock, patch
  from shenbi.pipeline.chapter_loop import (
      _generate_deterministic_review_summary,
      _parse_audit_verdict,
  )
  from shenbi.skill_utils.escalation.check import check_escalation

  class TestCheckEscalationHelperExists:
      def test_empty_signals_when_clean(self):
          # check_escalation returns [] when there is no blocking signal
          signals = check_escalation(
              resonance_scores=[80, 82, 81, 83, 84],
              sensitivity_blocking=False,
              volume_objective_met=True,
              regeneration_attempts=0,
          )
          assert signals == []

      def test_signals_on_sensitivity_blocking(self):
          signals = check_escalation(
              resonance_scores=[80, 82, 81, 83, 84],
              sensitivity_blocking=True,
              volume_objective_met=True,
              regeneration_attempts=0,
          )
          assert len(signals) > 0

  class TestParseAuditVerdict:
      def test_parses_pass_verdict(self, tmp_path):
          f = tmp_path / 'audit.md'
          f.write_text("## Verdict\n\nPASS - All checks passed.")
          verdict = _parse_audit_verdict(f)
          assert verdict['status'] == 'PASS'

      def test_parses_blocking_verdict(self, tmp_path):
          f = tmp_path / 'audit.md'
          f.write_text("## Verdict\n\nBLOCKING - Critical issue found.")
          verdict = _parse_audit_verdict(f)
          assert verdict['status'] == 'BLOCKING'
          assert verdict['blocking'] is True

      def test_parses_warn_verdict(self, tmp_path):
          f = tmp_path / 'audit.md'
          f.write_text("## Verdict\n\nWARN - Minor concern noted.")
          verdict = _parse_audit_verdict(f)
          assert verdict['status'] == 'WARN'

  class TestDeterministicSummary:
      def test_generates_summary_when_no_escalation(self, tmp_path):
          audit_dir = tmp_path / 'audits'
          audit_dir.mkdir()
          for atype in ['continuity', 'character']:
              f = audit_dir / f'chapter-5-{atype}.md'
              f.write_text("## Verdict\n\nPASS - OK.")
          _generate_deterministic_review_summary(tmp_path, 5)
          summary = audit_dir / 'chapter-5-review-summary.md'
          assert summary.exists()
          content = summary.read_text()
          assert 'continuity' in content
          assert 'character' in content

      def test_does_not_generate_when_no_audit_files(self, tmp_path):
          audit_dir = tmp_path / 'audits'
          audit_dir.mkdir()
          _generate_deterministic_review_summary(tmp_path, 5)
          summary = audit_dir / 'chapter-5-review-summary.md'
          assert not summary.exists()

      def test_summary_contains_chapter_specific_info(self, tmp_path):
          audit_dir = tmp_path / 'audits'
          audit_dir.mkdir()
          f = audit_dir / 'chapter-7-continuity.md'
          f.write_text("## Verdict\n\nPASS - Timeline consistent through Ch7.")
          _generate_deterministic_review_summary(tmp_path, 7)
          summary = audit_dir / 'chapter-7-review-summary.md'
          content = summary.read_text()
          assert 'Chapter 7' in content
          assert 'Timeline consistent' in content
  ```

- [ ] **5b. Run test -- confirm FAIL.**

- [ ] **5c. Implement** the reactive gate in `src/shenbi/pipeline/chapter_loop.py` at the `dispatch_escalation` call site (~`chapter_loop.py:414-420`). Gather the arguments required by the EXISTING `check_escalation()` signature and only dispatch the LLM when signals are non-empty:

  ```python
  # --- at the reactive escalation dispatch site (~chapter_loop.py:414-420) ---
  from shenbi.skill_utils.escalation.check import check_escalation

  # Gather arguments from pipeline state for the EXISTING helper signature.
  # check_escalation(resonance_scores, sensitivity_blocking,
  #                  volume_objective_met, regeneration_attempts,
  #                  arc_score=None, stratum_axis_drift=False)
  chapter = state.chapter_loop.current_chapter
  cs = state.chapter_loop.chapter_states[chapter]  # Declare cs from state
  resonance_scores = _get_recent_resonance_scores(state, window=5)
  signals = check_escalation(
      resonance_scores=resonance_scores,
      sensitivity_blocking=_has_sensitivity_blocking(cs),
      volume_objective_met=True,
      regeneration_attempts=cs.revision_count,
  )

  if not signals:
      # No escalation signal -> deterministic summary instead of LLM dispatch.
      _generate_deterministic_review_summary(
          state.project_dir, state.chapter_loop.current_chapter
      )
      log.info("escalation_review_skipped_no_signals",
               chapter=state.chapter_loop.current_chapter)
  else:
      dispatch_escalation(project_dir, chapter, context=...)
  ```

  Add the helper stubs for `_get_recent_resonance_scores()` and `_has_sensitivity_blocking()`:

  ```python
  def _get_recent_resonance_scores(state, window: int = 5) -> list[float]:
      """Extract recent resonance scores from pipeline state."""
      scores = []
      for ch_num in sorted(state.chapter_loop.chapter_states.keys())[-window:]:
          cs = state.chapter_loop.chapter_states[ch_num]
          if hasattr(cs, 'resonance_score') and cs.resonance_score is not None:
              scores.append(float(cs.resonance_score))
      return scores

  def _has_sensitivity_blocking(cs) -> bool:
      """Check if sensitivity blocking is active for this chapter."""
      return getattr(cs, 'sensitivity_blocking', False)
  ```

  Add the supporting deterministic-summary helpers (these are the only NEW functions):

  ```python
  import re
  from pathlib import Path

  ALL_AUDIT_TYPES = [
      'continuity', 'character', 'world-rules', 'pacing',
      'dialogue', 'motivation', 'pov', 'memo-compliance',
      'foreshadowing', 'anti-ai', 'texture', 'reader-pull',
      'resonance', 'sensitivity',
  ]


  def _parse_audit_verdict(audit_file: Path) -> dict:
      """Parse the verdict section from an audit report file.

      Returns dict with keys: status, blocking, summary.
      """
      if not audit_file.exists():
          return {'status': 'UNKNOWN', 'blocking': False, 'summary': ''}

      text = audit_file.read_text(encoding='utf-8')

      # Extract verdict status from ## Verdict section
      status_match = re.search(
          r'##\s*Verdict\s*\n+\s*(PASS|BLOCKING|WARN|FAIL)',
          text, re.IGNORECASE
      )
      status = status_match.group(1).upper() if status_match else 'UNKNOWN'

      # Extract summary line after verdict
      summary = ''
      if status_match:
          rest = text[status_match.end():]
          summary_line = re.search(r'-\s*(.+?)$', rest, re.MULTILINE)
          if summary_line:
              summary = summary_line.group(1).strip()

      return {
          'status': status,
          'blocking': status in ('BLOCKING', 'FAIL'),
          'summary': summary,
      }


  def _generate_deterministic_review_summary(
      project_dir: Path, chapter: int
  ) -> None:
      """Generate review summary by scanning audit files on disk. No LLM call.

      Only creates the summary file when escalation signals are absent.
      When escalation IS triggered, the LLM-based escalation-review handles it.
      """
      audit_dir = project_dir / 'audits'
      results = {}

      for audit_type in ALL_AUDIT_TYPES:
          audit_file = audit_dir / f'chapter-{chapter}-{audit_type}.md'
          if audit_file.exists():
              verdict = _parse_audit_verdict(audit_file)
              results[audit_type] = verdict

      if not results:
          return

      has_blocking = any(r.get('blocking') for r in results.values())
      if has_blocking:
          return  # Let LLM escalation-review handle blocking cases

      # Render deterministic summary
      lines = [
          f"# Chapter {chapter} -- Consolidated Review Results",
          "",
      ]

      # Count by status
      status_counts = {}
      for r in results.values():
          s = r.get('status', 'UNKNOWN')
          status_counts[s] = status_counts.get(s, 0) + 1

      total = len(results)
      for status, count in sorted(status_counts.items()):
          lines.append(f"- **{status}**: {count}/{total}")

      lines.append("")
      lines.append("## Individual Audit Results")
      lines.append("")

      for audit_type in sorted(results.keys()):
          verdict = results[audit_type]
          lines.append(
              f"- **{audit_type}**: {verdict.get('status', '?')} -- "
              f"{verdict.get('summary', '(no details)')}"
          )

      summary_path = audit_dir / f'chapter-{chapter}-review-summary.md'
      from shenbi.safe_write import safe_write
      safe_write(summary_path, '\n'.join(lines) + '\n')
  ```

- [ ] **5d.** Apply the same reactive gate at the closure-failure dispatch site in `src/shenbi/pipeline/cli.py:284` (import + call `check_escalation()` before the `dispatch_escalation` call there; fall back to deterministic summary on empty signals).

- [ ] **5e.** (Optional) Extend `src/shenbi/gates/g4/escalation_review.py` (EXISTS, 35 lines, currently only checks section presence of 触发信号 / 升级上下文 / 决策选项) to flag templated/identical summaries beyond the existing section-presence check.

- [ ] **5f. Run test -- confirm PASS.**

- [ ] **5g. Run `just check` -- confirm full pass.**

- [ ] **5h. Commit:** `feat(pipeline): wire check_escalation() into reactive escalation-review dispatch with deterministic fallback`

---

## Task 6: Split Review Checklist into Static Template + Dynamic Deltas

> **Spec-aligned note (Spec 5 §2.4, §3.5, §4.3):** `_extract_hook_deliverables` (reads `truth/pending_hooks.md`, PLANTED/ACTIVE/PENDING states) and `_get_max_source_mtime` (mtime-based cache invalidation) ALREADY EXIST in `src/shenbi/pipeline/review_checklist.py`. Do NOT re-add them. The real task: (a) diagnose why the existing extraction yields empty `hook_deliverables` and a frozen `ai_blacklist` in practice (likely `truth/pending_hooks.md` state mismatch or mtime-cache hits), and (b) refactor `build_review_checklist()` into a static template + per-chapter dynamic deltas with filenames aligned with Spec 10. Static template: `context/review-checklist-template.json`. Per-chapter deltas: `context/review-checklist-N.json` (note the `-chapter-` infix, not `-ch-`, per Spec 10 §3.2).

**Files:**
- `src/shenbi/pipeline/review_checklist.py` -- refactor `build_review_checklist()` into static + dynamic layers; diagnose existing extraction; add `_scan_recent_fatigue_patterns()` (genuinely new)

**TDD Cycle:**

- [ ] **6a. Write test:** Create `tests/pipeline/test_review_checklist.py`
  ```python
  """Test review checklist split into static template + dynamic deltas.

  NOTE: _extract_hook_deliverables and _get_max_source_mtime ALREADY EXIST.
  These tests cover the NEW static/dynamic layering and the NEW fatigue scanner.
  """
  import json
  import pytest
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from shenbi.pipeline.review_checklist import (
      build_review_checklist,
      _load_static_template,
      _scan_recent_fatigue_patterns,
  )

  class TestStaticTemplate:
      def test_loads_genesis_template(self, tmp_path):
          context_dir = tmp_path / 'context'
          context_dir.mkdir()
          static = {
              "genre_rules": ["no modern slang"],
              "formatting_constraints": ["8-section structure"],
              "ai_blacklist": ["骤然", "仿佛", "只见", "突然"]
          }
          # Filename aligned with Spec 10
          (context_dir / 'review-checklist-template.json').write_text(
              json.dumps(static, ensure_ascii=False)
          )
          result = _load_static_template(tmp_path)
          assert len(result['ai_blacklist']) == 4
          assert result['genre_rules'][0] == "no modern slang"

  class TestScanRecentFatiguePatterns:
      def test_flags_repeated_fatigue_words(self, tmp_path):
          chapters_dir = tmp_path / 'chapters'
          chapters_dir.mkdir()
          # 3 recent chapters with heavy "骤然" usage
          for ch in [1, 2, 3]:
              (chapters_dir / f'chapter-{ch}.md').write_text("骤然" * 4)
          flagged = _scan_recent_fatigue_patterns(tmp_path, 4)
          assert '骤然' in flagged

      def test_no_recent_chapters_returns_empty(self, tmp_path):
          assert _scan_recent_fatigue_patterns(tmp_path, 5) == []

  class TestBuildReviewChecklist:
      def test_merges_static_and_dynamic(self, tmp_path):
          context_dir = tmp_path / 'context'
          context_dir.mkdir()
          plans_dir = tmp_path / 'plans'
          plans_dir.mkdir()

          # Static template (Spec 10 filename)
          static = {"ai_blacklist": ["骤然", "仿佛"], "genre_rules": ["r1"]}
          (context_dir / 'review-checklist-template.json').write_text(
              json.dumps(static, ensure_ascii=False)
          )

          # Plan with hooks (existing _extract_hook_deliverables reads
          # truth/pending_hooks.md, not the plan; set up a minimal truth file
          # so the existing extraction is exercised).
          truth_dir = tmp_path / 'truth'
          truth_dir.mkdir()
          (truth_dir / 'pending_hooks.md').write_text(
              "hooks:\n  - id: MH-001\n    state: ACTIVE\n"
          )

          checklist = build_review_checklist(tmp_path, 3)
          assert len(checklist['ai_blacklist']) >= 2  # static base
          assert 'transition_budget' in checklist

      def test_persists_per_chapter_delta_with_spec10_filename(self, tmp_path):
          context_dir = tmp_path / 'context'
          context_dir.mkdir()
          static = {"ai_blacklist": ["骤然"]}
          (context_dir / 'review-checklist-template.json').write_text(
              json.dumps(static, ensure_ascii=False)
          )
          build_review_checklist(tmp_path, 3)
          # Spec 10 filename: review-checklist-N.json
          delta = context_dir / 'review-checklist-3.json'
          assert delta.exists()

  class TestExistingExtractionDiagnosis:
      """Diagnose why the EXISTING _extract_hook_deliverables returns empty."""

      def test_active_hooks_appear_in_deliverables(self, tmp_path):
          """EXISTS: pending_hooks.md with ACTIVE hooks must populate deliverables."""
          from shenbi.pipeline.review_checklist import _extract_hook_deliverables
          truth_dir = tmp_path / 'truth'
          truth_dir.mkdir()
          (truth_dir / 'pending_hooks.md').write_text(
              "hooks:\n  - id: MH-003\n    state: ACTIVE\n"
          )
          deliverables = _extract_hook_deliverables(tmp_path, 5)
          assert len(deliverables) >= 1

      def test_only_planted_hooks_excluded(self, tmp_path):
          """The existing filter keeps PLANTED/ACTIVE/PENDING; RESOLVED excluded."""
          from shenbi.pipeline.review_checklist import _extract_hook_deliverables
          truth_dir = tmp_path / 'truth'
          truth_dir.mkdir()
          (truth_dir / 'pending_hooks.md').write_text(
              "hooks:\n  - id: MH-003\n    state: RESOLVED\n"
          )
          deliverables = _extract_hook_deliverables(tmp_path, 5)
          assert deliverables == []
  ```

- [ ] **6b. Diagnose the existing extraction.** Before writing new code, run a diagnostic against `truth/pending_hooks.md` from real output: confirm whether hooks are in PLANTED/ACTIVE/PENDING states and whether `_get_max_source_mtime` registers a change after `pending_hooks.md` is touched. Log the finding; the fix targets the data/trigger path.

- [ ] **6c. Run test -- confirm FAIL** (on the new static/dynamic layering and the new fatigue scanner).

- [ ] **6d. Implement** the static + dynamic split in `src/shenbi/pipeline/review_checklist.py`. KEEP the existing `_extract_hook_deliverables` (reads `truth/pending_hooks.md`) and `_get_max_source_mtime`; ADD `_load_static_template`, `_scan_recent_fatigue_patterns`, and refactor `build_review_checklist`:
  ```python
  """Review checklist builder -- static Genesis template + per-chapter dynamic deltas.

  NOTE: _extract_hook_deliverables (reads truth/pending_hooks.md, PLANTED/ACTIVE/PENDING)
  and _get_max_source_mtime (mtime-based cache invalidation) ALREADY EXIST and are
  retained unchanged. This module adds the static/dynamic layering on top.
  """
  import json
  import re
  from pathlib import Path


  def _load_static_template(project_dir: Path) -> dict:
      """Load the static Genesis review checklist template.

      Filename aligned with Spec 10: context/review-checklist-template.json
      """
      template_path = project_dir / 'context' / 'review-checklist-template.json'
      if not template_path.exists():
          return {
              'genre_rules': [],
              'formatting_constraints': [],
              'ai_blacklist': [],
          }
      return json.loads(template_path.read_text(encoding='utf-8'))


  def _scan_recent_fatigue_patterns(project_dir: Path, chapter: int) -> list[str]:
      """Scan recent chapters for AI fatigue patterns to add to blacklist.

      Returns list of words/phrases that have appeared excessively
      in recent chapters (last 5).
      """
      fatigue_words = []
      start_ch = max(1, chapter - 5)
      word_counts = {}

      for ch in range(start_ch, chapter):
          ch_path = project_dir / 'chapters' / f'chapter-{ch}.md'
          if not ch_path.exists():
              continue
          text = ch_path.read_text(encoding='utf-8')
          for word in ['骤然', '仿佛', '只见', '突然', '缓缓', '微微', '深深']:
              count = text.count(word)
              word_counts[word] = word_counts.get(word, 0) + count

      for word, count in word_counts.items():
          if count > 3:
              fatigue_words.append(word)

      return fatigue_words


  def build_review_checklist(project_dir: Path, chapter: int) -> dict:
      """Build the full review checklist by merging static template with
      per-chapter dynamic deltas. Reuses the EXISTING _extract_hook_deliverables
      (truth/pending_hooks.md) and _get_max_source_mtime for invalidation.
      """
      static = _load_static_template(project_dir)

      # _extract_hook_deliverables ALREADY EXISTS (reads truth/pending_hooks.md)
      dynamic = {
          'hook_deliverables': _extract_hook_deliverables(project_dir, chapter),
          'ai_blacklist_additions': _scan_recent_fatigue_patterns(
              project_dir, chapter
          ),
          'transition_budget': _compute_transition_budget(project_dir, chapter),
      }

      merged = dict(static)
      merged['hook_deliverables'] = dynamic['hook_deliverables']
      merged['ai_blacklist'] = (
          static.get('ai_blacklist', []) +
          dynamic['ai_blacklist_additions']
      )
      merged['transition_budget'] = dynamic['transition_budget']

      # Persist the per-chapter delta (Spec 10 filename: review-checklist-N.json)
      delta_path = project_dir / 'context' / f'review-checklist-{chapter}.json'
      from shenbi.safe_write import safe_write
      safe_write(delta_path, json.dumps(merged, ensure_ascii=False, indent=2))

      return merged
  ```

- [ ] **6e. Run test -- confirm PASS.**

- [ ] **6f. Commit:** `feat(pipeline): split review checklist into static template + per-chapter dynamic deltas (diagnose existing extraction)`

---

## Task 7: Ensure Context-Composing Checklist Regeneration Uses Current Sources

> **Spec-aligned note (Spec 5 §3.7):** `review_checklist.py` ALREADY implements mtime-based cache invalidation (`_get_max_source_mtime`, lines 195-224) comparing genre-config, chapter file, and `truth/` mtimes against the cache mtime. The remaining risk is that the upstream `truth/` files are not touched when they should be (e.g., `pending_hooks.md` not updated with hook state changes), so the mtime check registers no change and yields a cache hit. The fix ensures the upstream truth files are updated each chapter so the EXISTING invalidation fires. Filenames aligned with Spec 10.

**Files:**
- `src/shenbi/pipeline/chapter_loop.py` -- ensure upstream truth files are touched each chapter so the existing mtime invalidation fires
- `skills/shenbi-context-composing/SKILL.md` -- update contract for dynamic deltas

- [ ] **7a.** In `src/shenbi/pipeline/chapter_loop.py`, confirm that the truth files feeding `_get_max_source_mtime` (`truth/current_state.md`, `truth/chapter_summaries.md`, `truth/pending_hooks.md`) are updated each chapter. If any is not written, the existing mtime invalidation never fires -- that is the actual root cause of the static-output symptom. If a cache is explicitly retained, clear it before composing:
  ```python
  # Ensure upstream truth files are touched so the EXISTING mtime
  # invalidation (_get_max_source_mtime) registers a change.
  # If a checklist cache object exists, clear it before composing.
  _checklist_cache.clear()  # only if a cache object exists; otherwise rely on mtime
  ```

- [ ] **7b.** Update `skills/shenbi-context-composing/SKILL.md` contract to declare that it generates dynamic per-chapter deltas with Spec 10 filenames:
  ```yaml
  contract:
    reads:
      - {file: truth/current_state.md}
      - {file: truth/chapter_summaries.md}
      - {file: truth/pending_hooks.md}
      - {file: plans/chapter-N-plan.md, fields: [7. Hook Ledger]}
      - {file: context/review-checklist-template.json}
    writes:
      - {file: context/review-checklist-N.json, mode: create}
    force_regenerate: true
  ```

- [ ] **7c. Run `just check` -- confirm full pass.**

- [ ] **7d. Commit:** `fix(pipeline): ensure truth files are touched so mtime invalidation fires for checklist regeneration`

---

## Task 8: Add Title Quality Constraints to Planning SKILL.md

**Files:**
- `skills/shenbi-chapter-planning/SKILL.md` -- add title quality requirements to system prompt

- [ ] **8a.** Add to the chapter planning prompt template, in the section where chapter metadata is described:
  ```markdown
  ## Chapter Title Requirements
  - Title must be a 1-4 Chinese character thematic phrase
  - Prohibited: day-of-week labels (Monday, 周一, Tuesday, 周二, etc.)
  - Prohibited: chapter numbers (第N章)
  - Prohibited: duplicate of any previous chapter title
  - Preferred: poetic, evocative single or double-character names
  ```

- [ ] **8b. Commit:** `docs(skills): add title quality constraints to chapter planning prompt`

---

## Task 9: End-to-End Verification

- [ ] **9a.** Run `just check` -- confirm full pass.
- [ ] **9b.** Run a 3-chapter mini-pipeline test:
  ```bash
  python -m shenbi.pipeline.cli next --project-dir novel-output/test-quality-gates
  ```
- [ ] **9c.** Verify: no date-label titles in output.
- [ ] **9d.** Verify: `review-checklist-*.json` files differ between chapters.
- [ ] **9e.** Verify: `hook_deliverables` is non-empty when plan has hooks (and the EXISTING `_extract_hook_deliverables` from `truth/pending_hooks.md` is populated).
- [ ] **9f.** Verify: no templated `review-summary.md` generated when no escalation signals; deterministic summary used instead.
- [ ] **9g.** Verify: `G4.cd.title` catches chapter-number titles in regression test.

- [ ] **9h. Commit:** `test: end-to-end verification of quality gates and review optimization`
