"""Tests for the cost report CLI (spec §3.5)."""

from __future__ import annotations

from pathlib import Path

from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import main, render_report


def _seed_ledger(tmp_path: Path) -> None:
    led = TokenLedger(tmp_path)
    led.record(
        "drafting", 1, {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    )
    led.record(
        "drafting", 2, {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500}
    )
    led.record("review", 1, {"prompt_tokens": 300, "completion_tokens": 100, "total_tokens": 400})


class TestRenderReport:
    def test_report_has_total_and_breakdown(self, tmp_path: Path):
        _seed_ledger(tmp_path)
        out = render_report(tmp_path)
        assert "Total" in out
        assert "drafting" in out
        assert "review" in out
        # per-skill percentage
        assert "%" in out

    def test_report_on_empty_ledger(self, tmp_path: Path):
        out = render_report(tmp_path)
        assert "no token usage" in out.lower() or "$0" in out or "Total" in out


class TestCli:
    def test_main_returns_zero_on_existing(self, tmp_path: Path, capsys):
        _seed_ledger(tmp_path)
        rc = main(["report", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "drafting" in captured.out

    def test_main_returns_nonzero_on_missing_dir(self, tmp_path: Path):
        rc = main(["report", str(tmp_path / "does-not-exist")])
        assert rc != 0
