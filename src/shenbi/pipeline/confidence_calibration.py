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
        log.info("calibration_skipped_insufficient_history", chapter=chapter)
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
