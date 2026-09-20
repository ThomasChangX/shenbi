"""Spec #68 T4: observations — ledger per-chapter, truth growth, coverage."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _record(
    tmp_path: Path,
    chapter: int,
    *,
    cost: float = 0.01,
    minutes: int = 0,
    attempt: int = 1,
) -> None:
    """经真实写方 TokenLedger.record 追加一行；timestamp/cost 回写为受控值。

    行仍由 record 追加，字段集与 iter_records 兼容契约一致。
    """
    from shenbi.cost.ledger import TokenLedger

    led = TokenLedger(tmp_path)
    usage = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    led.record("shenbi-chapter-drafting", chapter, usage, attempt=attempt)
    lines = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[-1])
    row["timestamp"] = (
        datetime(2026, 9, 21, 12, 0, tzinfo=UTC) + timedelta(minutes=minutes)
    ).isoformat()
    row["estimated_cost_usd"] = cost
    lines[-1] = json.dumps(row, ensure_ascii=False)
    (tmp_path / "cost" / "token-ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestLedgerStats:
    """ledger 按章聚合 + 墙钟 + 跳行披露。"""

    def test_per_chapter_aggregation_and_wallclock(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        _record(tmp_path, 1, cost=0.01, minutes=0, attempt=1)
        _record(tmp_path, 1, cost=0.02, minutes=30, attempt=2)
        _record(tmp_path, 2, cost=0.03, minutes=90)
        stats = ledger_stats(tmp_path, [1, 2], {1: 10000, 2: 20000})
        by_ch = {e["chapter"]: e for e in stats["per_chapter"]}
        assert by_ch[1]["cost_usd"] == pytest.approx(0.03)
        assert by_ch[1]["wall_clock_s"] == 1800.0
        assert by_ch[2]["cost_per_10k"] == pytest.approx(0.015)
        assert by_ch[1]["attempts"] == 2  # max(attempt) 语义（spec §1「attempt 聚合」）
        assert stats["skipped_rows"] == 0 and stats["chapters_covered"] == 2

    def test_skipped_rows_disclosed(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        _record(tmp_path, 1)
        led = tmp_path / "cost" / "token-ledger.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + "{corrupt\n", encoding="utf-8")
        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["skipped_rows"] == 1

    def test_missing_ledger_zero_coverage(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["per_chapter"] == [] and stats["chapters_covered"] == 0


class TestTruthGrowth:
    """truth 增长曲线 + 条件性注记 + 真实 fixture 面。"""

    def test_current_sizes_and_conditional_note(self, tmp_path):
        from tools.report_longitudinal import truth_growth

        truth = tmp_path / "truth"
        truth.mkdir()
        (truth / "current_state.md").write_text("# 状态\n" + "x" * 500, encoding="utf-8")
        out = truth_growth(tmp_path)
        assert any(e["file"] == "current_state.md" and e["bytes"] > 500 for e in out["current"])
        assert "快照" in out["note"] or "snapshot" in out["note"]

    def test_real_fixture_truth_face(self, tmp_path):
        """spec 验收：chapter-025 真实产物提供 truth 面基准——真实尺寸可读且非空。"""
        import shutil

        from tools.report_longitudinal import truth_growth

        src = (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / "snapshots"
            / "chapter-025"
            / "truth"
        )
        shutil.copytree(src, tmp_path / "truth")
        out = truth_growth(tmp_path)
        assert {e["file"] for e in out["current"]} >= {
            "current_state.md",
            "character_matrix.md",
            "pending_hooks.md",
        }
        assert all(e["bytes"] > 0 for e in out["current"])
