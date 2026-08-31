"""Post-dispatch confidence calibration (spec #33 T1b-2).

The review-resonance skill self-reports a per-chapter confidence
(``calibration: reported=<high|mid|low>`` line). LLM scorers are
overconfident; the framework recalibrates via anchor hit-rate
(``shenbi.skill_utils.calibration.confidence.calibrate_confidence``) and
patches the calibrated value into the winning trend row's confidence cell.

Anchor ground truth is cross-signal, not self-reported: an anchor row's
``correct`` count is framework-derived from whether the chapter's scored
outcome held up (score at/above floor), recorded when the trend row is
persisted. Hit-rate with fewer than 3 accumulated high-confidence anchors
fails open (no downgrade) with explicit disclosure.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from shenbi.skill_utils.calibration.confidence import HitRate, calibrate_confidence

log = structlog.get_logger(__name__)

_ANCHOR_TRUTH_FILE = "resonance_anchors.md"
#: Minimum accumulated high-confidence anchors before calibration engages.
_MIN_ANCHOR_DENOMINATOR = 3

_REPORTED_RE = re.compile(r"calibration:\s*reported=(high|mid|low)")

#: ``anchors: high=4 | 情感落地=45 | ...`` — capture the per-dimension
#: anchor line numbers that follow the high= count.
_ANCHOR_LINE_RE = re.compile(r"=(\d+)")


def parse_reported_confidence(report_path: Path) -> str | None:
    """Extract the skill's self-reported confidence from its report."""
    if not report_path.exists():
        return None
    match = _REPORTED_RE.search(report_path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def record_anchor_outcome(
    project_dir: Path, chapter: int, high_conf_anchors: int, correct: int
) -> None:
    """Upsert one chapter's anchor outcome row ``| {N} | {high} | {correct} |``."""
    from shenbi.pipeline.truth_io import write_truth_file

    write_truth_file(
        project_dir,
        _ANCHOR_TRUTH_FILE,
        f"| {chapter} | {high_conf_anchors} | {correct} |",
        mode="insert_markdown_row",
        key_field="chapter",
    )


def compute_anchor_hit_rate(project_dir: Path) -> HitRate | None:
    """Aggregate accumulated anchor rows into a HitRate (None = cold start)."""
    truth = project_dir / "truth" / _ANCHOR_TRUTH_FILE
    if not truth.exists():
        return None
    total = 0
    correct = 0
    for line in truth.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        try:
            high, ok = int(cells[1]), int(cells[2])
        except ValueError:
            log.warning("anchor_row_unparseable", row=line[:40])
            continue
        if high < 0 or ok < 0 or ok > high:
            log.warning("anchor_row_out_of_range", row=line[:40])
            continue
        total += high
        correct += ok
    if total < _MIN_ANCHOR_DENOMINATOR:
        log.info("calibration_insufficient_history", total=total)
        return None
    return HitRate(high_confidence=correct / total)


def calibrate_and_patch_trend(
    project_dir: Path,
    chapter: int,
    reported: str,
    *,
    overall: int | None = None,
) -> None:
    """Recalibrate ``reported`` and patch the trend row's confidence cell.

    Works on whichever row won the insert-only trend write (skill rich row or
    framework placeholder). When no row exists yet, a placeholder row is
    written first (requires ``overall``).
    """
    from shenbi.pipeline.chapter_loop import build_resonance_trend_row
    from shenbi.pipeline.truth_io import patch_markdown_table_cell, write_truth_file

    hr = compute_anchor_hit_rate(project_dir)
    if hr is None:
        # already disclosed as calibration_insufficient_history inside compute_anchor_hit_rate
        return
    calibrated = calibrate_confidence(reported, hr)
    if calibrated != reported:
        log.info(
            "confidence_calibrated",
            chapter=chapter,
            before=reported,
            after=calibrated,
            hit_rate=hr.high_confidence,
        )
    trend_path = project_dir / "truth" / "resonance_trend.md"
    if not patch_markdown_table_cell(trend_path, str(chapter), "chapter", 7, calibrated):
        if overall is None:
            log.warning("calibration_patch_no_row", chapter=chapter)
            return
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            build_resonance_trend_row(chapter, overall),
            mode="insert_markdown_row",
            key_field="chapter",
        )
        if not patch_markdown_table_cell(trend_path, str(chapter), "chapter", 7, calibrated):
            log.warning("calibration_patch_failed_after_placeholder", chapter=chapter)


def record_anchor_outcome_from_report(
    project_dir: Path, chapter: int, report_path: Path, high_anchors: int
) -> None:
    """Record one chapter's anchor outcome using the block-level cross-signal.

    Spec v8 block-level cross-signal: an anchor judgment is "correct" when
    the chapter's preceding revision actually rewrote the text the anchor
    covered. Called from the resonance re-parse, which runs BEFORE the next
    revision's backup exists — so on a first pass the row is 0/0
    (unverifiable), and on a re-score pass the diff measures the revision
    that just happened. Ground truth = pre-revision backup vs current prose
    line diff; anchor line numbers relocate within a ±5-line window. Rows
    with a ``high=``/dimension-line parse shortfall are 0/0 (unverifiable —
    excluded from numerator and denominator, disclosed via log, never
    silently scored).
    """
    import difflib

    backup = project_dir / "chapters" / f"chapter-{chapter}-pre-rev.md"
    current = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not report_path.exists():
        log.info("anchor_unverifiable", chapter=chapter, reason="no_report")
        record_anchor_outcome(project_dir, chapter, 0, 0)
        return
    report_text = report_path.read_text(encoding="utf-8")
    anchor_match = re.search(r"anchors: high=(\d+)(.*)", report_text)
    if anchor_match is None:
        log.info("anchor_unverifiable", chapter=chapter, reason="no_anchor_block")
        record_anchor_outcome(project_dir, chapter, 0, 0)
        return
    dim_lines = [int(m) for m in _ANCHOR_LINE_RE.findall(anchor_match.group(2))]
    if not dim_lines:
        log.info("anchor_unverifiable", chapter=chapter, reason="parse_shortfall")
        record_anchor_outcome(project_dir, chapter, 0, 0)
        return
    if not backup.exists() or not current.exists():
        log.info("anchor_unverifiable", chapter=chapter, reason="no_revision_backup")
        record_anchor_outcome(project_dir, chapter, 0, 0)
        return
    old = backup.read_text(encoding="utf-8").splitlines()
    new = current.read_text(encoding="utf-8").splitlines()
    if old == new:
        log.info("anchor_unverifiable", chapter=chapter, reason="text_unchanged")
        record_anchor_outcome(project_dir, chapter, 0, 0)
        return
    # Changed regions in the CURRENT text (replace/insert opcodes).
    changed: list[int] = []
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            changed.extend(range(j1 + 1, j2 + 1))  # 1-based lines
    window = {ln + d for ln in changed for d in range(-5, 6)}
    correct = sum(1 for ln in dim_lines if ln in window)
    # Denominator = parsed dimension anchors, not the declared high= count:
    # keeps numerator and denominator consistent under format drift.
    record_anchor_outcome(project_dir, chapter, len(dim_lines), correct)
    log.info(
        "anchor_outcome_recorded",
        chapter=chapter,
        high=high_anchors,
        anchors=len(dim_lines),
        correct=correct,
    )
