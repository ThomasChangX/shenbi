"""Tests for TokenLedger wire-up in the dispatch path (spec §3.1 dead-wire fix)."""

import json
from pathlib import Path
from types import SimpleNamespace


def test_record_token_usage_persists_to_ledger(tmp_path: Path):
    """_record_token_usage must write to cost/token-ledger.jsonl (spec §3.1).

    Before this fix, _record_token_usage only mutated an in-memory dict and
    the ledger stayed empty (dead-wire).
    """
    from shenbi.pipeline.dispatch_helper import _record_token_usage

    state = SimpleNamespace(token_usage={})
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    _record_token_usage(state, "test-skill", usage, project_dir=tmp_path)

    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists(), "ledger file must be created"
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["skill"] == "test-skill"
    assert records[0]["prompt_tokens"] == 100
    assert records[0]["completion_tokens"] == 50


def test_record_token_usage_still_updates_in_memory_state(tmp_path: Path):
    """The in-memory state.token_usage accumulation still works alongside ledger."""
    from shenbi.pipeline.dispatch_helper import _record_token_usage

    state = SimpleNamespace(token_usage={})
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    _record_token_usage(state, "skill-a", usage, project_dir=tmp_path)
    _record_token_usage(state, "skill-a", usage, project_dir=tmp_path)

    assert state.token_usage["skill-a"]["calls"] == 2
    assert state.token_usage["skill-a"]["prompt_tokens"] == 20
