"""Tests for post-dispatch confidence calibration (spec #33 T1b-2)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.confidence_calibration import (
    calibrate_and_patch_trend,
    compute_anchor_hit_rate,
    parse_reported_confidence,
    record_anchor_outcome,
)
from shenbi.pipeline.revision_router import MAX_AUTO_REVISIONS, revision_cap_exceeded


def test_parse_reported_confidence(tmp_path: Path) -> None:
    report = tmp_path / "audits" / "chapter-5-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "---\nresonance_score: 72\n---\n\n# 报告\n\ncalibration: reported=high\n",
        encoding="utf-8",
    )
    assert parse_reported_confidence(report) == "high"


def test_parse_reported_confidence_missing(tmp_path: Path) -> None:
    report = tmp_path / "audits" / "chapter-5-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 报告，无校准行\n", encoding="utf-8")
    assert parse_reported_confidence(report) is None


def test_hit_rate_from_accumulated_rows(tmp_path: Path) -> None:
    # correct/total = 1/4 high-confidence anchors correct → 0.25 < 0.8.
    for n, high, correct in [(1, 2, 1), (2, 1, 0), (3, 1, 0)]:
        record_anchor_outcome(tmp_path, n, high, correct)
    hr = compute_anchor_hit_rate(tmp_path)
    assert hr is not None
    assert hr.high_confidence == 0.25


def test_hit_rate_cold_start_fail_open(tmp_path: Path) -> None:
    record_anchor_outcome(tmp_path, 1, 2, 1)  # denominator 2 < 3
    assert compute_anchor_hit_rate(tmp_path) is None


def test_calibrate_and_patch_trend_downgrades(tmp_path: Path) -> None:
    truth = tmp_path / "truth" / "resonance_trend.md"
    truth.parent.mkdir(parents=True)
    truth.write_text(
        "| chapter | role | d1 | d2 | d3 | d4 | overall | confidence | human |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| 5 | 高潮 | 70 | 65 | 80 | 75 | 72 | high |  |\n",
        encoding="utf-8",
    )
    for n, high, correct in [(1, 2, 0), (2, 1, 0), (3, 1, 0)]:
        record_anchor_outcome(tmp_path, n, high, correct)  # hit rate 0.0
    calibrate_and_patch_trend(tmp_path, 5, "high")
    line = next(
        ln for ln in truth.read_text(encoding="utf-8").splitlines() if ln.startswith("| 5 ")
    )
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    assert cells[7] == "mid"


def test_calibrate_insufficient_history_no_downgrade(tmp_path: Path) -> None:
    truth = tmp_path / "truth" / "resonance_trend.md"
    truth.parent.mkdir(parents=True)
    truth.write_text("| 3 | - | - | - | - | - | 61 | high |  |\n", encoding="utf-8")
    record_anchor_outcome(tmp_path, 1, 1, 0)  # denominator 1 < 3 → fail-open
    calibrate_and_patch_trend(tmp_path, 3, "high")
    assert "| 3 | - | - | - | - | - | 61 | high |  |" in truth.read_text(encoding="utf-8")


def test_calibrate_writes_placeholder_when_row_missing(tmp_path: Path) -> None:
    truth = tmp_path / "truth" / "resonance_trend.md"
    truth.parent.mkdir(parents=True)
    truth.write_text("", encoding="utf-8")
    for n, high, correct in [(1, 2, 0), (2, 1, 0), (3, 1, 0)]:
        record_anchor_outcome(tmp_path, n, high, correct)
    calibrate_and_patch_trend(tmp_path, 4, "high", overall=58)
    text = truth.read_text(encoding="utf-8")
    assert "| 4 |" in text and " mid |" in text


def test_revision_cap():
    assert MAX_AUTO_REVISIONS == 2
    assert not revision_cap_exceeded(0)
    assert not revision_cap_exceeded(2)
    assert revision_cap_exceeded(3)
