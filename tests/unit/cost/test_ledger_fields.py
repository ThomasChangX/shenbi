"""Spec #36 ledger compat contract: defaulted new fields + T404 pricing_status."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.cost.ledger import TokenLedger


def _old_row(skill: str = "chapter-drafting") -> str:
    """A pre-spec36 ledger line: none of the new fields present."""
    return json.dumps(
        {
            "timestamp": "2026-08-16T00:00:00+00:00",
            "skill": skill,
            "chapter": 1,
            "model": "deepseek-v4-flash",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "estimated_cost_usd": 0.001,
        }
    )


def _last_line(tmp_path: Path) -> str:
    return TokenLedger(tmp_path).ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1]


def test_mixed_old_and_new_rows_all_readable(tmp_path: Path):
    ledger = TokenLedger(tmp_path)
    ledger.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
    with ledger.ledger_path.open("a", encoding="utf-8") as f:
        f.write(_old_row() + "\n")
    recs = list(ledger.iter_records())
    assert len(recs) == 2  # compat contract: old rows never TypeError-skipped
    assert recs[1].skill == "chapter-drafting" and recs[1].estimated is False


def test_record_estimated_and_attempt_flags(tmp_path: Path):
    rec = TokenLedger(tmp_path).record(
        "s", 2, {"prompt_tokens": 100, "total_tokens": 100}, estimated=True, attempt=3
    )
    data = json.loads(_last_line(tmp_path))
    assert data["estimated"] is True and data["attempt"] == 3
    assert rec.estimated is True and rec.pricing_status == "ok"


def test_unknown_model_marked_not_silent_zero(tmp_path: Path):
    rec = TokenLedger(tmp_path).record(
        "s", 1, {"prompt_tokens": 10, "total_tokens": 10}, model="no-such-model-v9"
    )
    assert rec.pricing_status == "unknown-model"
    assert rec.model == "no-such-model-v9"  # real model name preserved (T404)
