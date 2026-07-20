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

    def test_record_returns_token_usage_record(self, tmp_path: Path):
        """record() returns a TokenUsageRecord with correct fields."""
        led = TokenLedger(tmp_path)
        rec = led.record(
            skill="review",
            chapter=3,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        assert isinstance(rec, TokenUsageRecord)
        assert rec.skill == "review"
        assert rec.chapter == 3
        assert rec.prompt_tokens == 10
        assert rec.completion_tokens == 20
        assert rec.total_tokens == 30

    def test_record_missing_total_tokens_defaults_zero(self, tmp_path: Path):
        """Missing total_tokens in usage defaults to 0."""
        led = TokenLedger(tmp_path)
        rec = led.record("s", 1, {"prompt_tokens": 10, "completion_tokens": 5})
        assert rec.total_tokens == 0

    def test_record_missing_all_usage_fields_defaults_zero(self, tmp_path: Path):
        """Empty usage dict produces zero-cost record without crashing."""
        led = TokenLedger(tmp_path)
        rec = led.record("s", 1, {})
        assert rec.prompt_tokens == 0
        assert rec.completion_tokens == 0
        assert rec.total_tokens == 0
        assert rec.estimated_cost_usd == 0.0

    def test_record_model_none_resolves_to_default(self, tmp_path: Path):
        """When model=None, the resolved model is the default."""
        led = TokenLedger(tmp_path)
        rec = led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1}, model=None)
        assert rec.model == "deepseek-v4-pro"

    def test_record_timestamp_is_iso8601_utc(self, tmp_path: Path):
        """Timestamp must be ISO 8601 with timezone info."""
        led = TokenLedger(tmp_path)
        rec = led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1})
        # Should contain T separator and either Z or +00:00
        assert "T" in rec.timestamp
        assert rec.timestamp.endswith("+00:00") or rec.timestamp.endswith("Z")


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

    def test_summarize_includes_cost_aggregation(self, tmp_path: Path):
        """Summarize must track estimated_cost_usd in totals and by-skill."""
        led = TokenLedger(tmp_path)
        led.record("drafting", 1, {"prompt_tokens": 1_000_000, "completion_tokens": 0})
        s = led.summarize()
        assert s["total"]["estimated_cost_usd"] > 0
        assert s["by_skill"]["drafting"]["estimated_cost_usd"] > 0


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

    def test_iter_records_skips_corrupt_json_line(self, tmp_path: Path):
        """A line with invalid JSON is skipped, not crashed on."""
        led = TokenLedger(tmp_path)
        led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        with led.ledger_path.open("a", encoding="utf-8") as f:
            f.write("{this is not valid json}\n")
        records = list(led.iter_records())
        assert len(records) == 1
        assert records[0].skill == "s"

    def test_iter_records_skips_malformed_record_wrong_keys(self, tmp_path: Path):
        """A line with valid JSON but wrong field names is skipped."""
        led = TokenLedger(tmp_path)
        led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        with led.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"wrong_field": 42}) + "\n")
        records = list(led.iter_records())
        assert len(records) == 1
        assert records[0].skill == "s"

    def test_iter_records_empty_file_returns_nothing(self, tmp_path: Path):
        """An empty ledger (no file) yields no records without crashing."""
        led = TokenLedger(tmp_path)
        # Never wrote anything — ledger file doesn't exist
        records = list(led.iter_records())
        assert records == []

    def test_iter_records_returns_token_usage_records(self, tmp_path: Path):
        """All yielded items are TokenUsageRecord instances."""
        led = TokenLedger(tmp_path)
        led.record("a", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        led.record("b", 2, {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7})
        for rec in led.iter_records():
            assert isinstance(rec, TokenUsageRecord)
