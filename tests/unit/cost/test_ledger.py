"""Tests for the TokenLedger JSONL persistence (spec §3.2)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.cost.ledger import TokenLedger, TokenUsageRecord


class TestRecord:
    def test_record_appends_one_jsonl_line(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record(
            skill="shenbi-chapter-drafting",
            chapter=1,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            model="deepseek-v4-pro",
        )
        lines = led.ledger_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["skill"] == "shenbi-chapter-drafting"
        assert rec["chapter"] == 1
        assert rec["prompt_tokens"] == 100
        assert rec["completion_tokens"] == 50
        assert rec["total_tokens"] == 150
        assert "estimated_cost_usd" in rec
        assert "model" in rec
        assert "timestamp" in rec

    def test_multiple_records_append(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        for ch in range(3):
            led.record("s", ch, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
        assert len(led.ledger_path.read_text().splitlines()) == 3


class TestSummarize:
    def test_summarize_aggregates_by_skill_and_chapter(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record(
            "drafting", 1, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        )
        led.record(
            "drafting", 2, {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
        )
        led.record("review", 1, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50})

        s = led.summarize()
        assert s["total"]["prompt_tokens"] == 330
        assert s["total"]["completion_tokens"] == 170
        assert s["total"]["total_tokens"] == 500
        assert s["total"]["calls"] == 3
        # by skill
        assert set(s["by_skill"]) == {"drafting", "review"}
        assert s["by_skill"]["drafting"]["total_tokens"] == 450
        # by chapter
        assert set(s["by_chapter"]) == {"1", "2"}
        assert s["by_chapter"]["1"]["total_tokens"] == 200  # 150 + 50

    def test_summarize_empty_ledger(self, tmp_path: Path):
        s = TokenLedger(tmp_path).summarize()
        assert s["total"]["calls"] == 0
        assert s["total"]["total_tokens"] == 0
        assert s["by_skill"] == {}


class TestIterRecords:
    def test_iter_records_tolerates_blank_line(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        # append a blank/corrupt line to simulate partial write
        with led.ledger_path.open("a", encoding="utf-8") as f:
            f.write("\n")
        records = list(led.iter_records())
        assert len(records) == 1
        assert isinstance(records[0], TokenUsageRecord)
        assert records[0].skill == "s"
