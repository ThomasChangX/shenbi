"""Spec #36 T6'b: report honesty — per-chapter average caveat + estimated split."""

from __future__ import annotations

from pathlib import Path

from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import render_report


def test_per_chapter_average_has_caveat_line(tmp_path: Path):
    TokenLedger(tmp_path).record("s", 1, {"prompt_tokens": 5, "total_tokens": 5})
    text = render_report(tmp_path)
    assert "Per-chapter average cost" in text
    assert "total cost / chapter count" in text  # T406' caveat line


def test_estimated_rows_broken_out(tmp_path: Path):
    TokenLedger(tmp_path).record("metered", 1, {"prompt_tokens": 5, "total_tokens": 5})
    TokenLedger(tmp_path).record(
        "unmetered", 2, {"prompt_tokens": 50, "total_tokens": 50}, estimated=True
    )
    text = render_report(tmp_path)
    assert "Estimated (lower-bound) rows**: 1" in text
    after = text.split("Estimated (lower-bound) rows**: 1")[1].splitlines()[0]
    assert "50" in after  # estimated tokens surfaced separately
