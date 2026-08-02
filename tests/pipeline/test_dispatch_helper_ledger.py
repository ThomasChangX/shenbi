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


def test_log_token_usage_handles_bare_usage_object(tmp_path: Path):
    """_log_token_usage must accept a bare Usage object (streaming path).

    The streaming path (_call_llm_streaming_with_retry) returns chunk.usage
    directly — a bare Usage object with prompt_tokens/completion_tokens, NOT
    a response object with a nested .usage attribute. The original hasattr
    (response, "usage") guard would skip it (latent dead-wire). This test
    guards the dual-form handling.
    """
    from shenbi.pipeline.dispatch_helper import _log_token_usage

    state = SimpleNamespace(token_usage={})
    # Bare usage object (no nested .usage attr) — the streaming form.
    bare_usage = SimpleNamespace(prompt_tokens=200, completion_tokens=100, total_tokens=300)
    _log_token_usage(bare_usage, "streaming-skill", state=state, project_dir=tmp_path)

    # The ledger must have a row (would be empty if the guard skipped it).
    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists()
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["prompt_tokens"] == 200


def test_log_token_usage_handles_response_wrapper(tmp_path: Path):
    """_log_token_usage still accepts a response object with nested .usage."""
    from shenbi.pipeline.dispatch_helper import _log_token_usage

    state = SimpleNamespace(token_usage={})
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=50, completion_tokens=25, total_tokens=75)
    )
    _log_token_usage(response, "wrapped-skill", state=state, project_dir=tmp_path)

    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists()
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert records[0]["prompt_tokens"] == 50


def test_log_token_usage_skips_none_usage():
    """Objects with no usage info are skipped silently (no crash)."""
    from shenbi.pipeline.dispatch_helper import _log_token_usage

    # Should not raise; should be a no-op.
    _log_token_usage(SimpleNamespace(), "no-usage-skill", state=SimpleNamespace(), project_dir=None)
