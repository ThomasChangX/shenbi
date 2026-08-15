"""Tests for TokenLedger wire-up in the dispatch path (spec §3.1 dead-wire fix).

C10 spec T1/T2 (2026-08-16): the durable ledger write moved inside the API
dispatch path and is no longer gated on a PipelineState being threaded
through. ``_record_usage_to_ledger`` is the single fail-safe entry point;
the former in-memory ``state.token_usage`` accumulation was removed (single
source of truth = ledger).
"""

import json
from pathlib import Path
from types import SimpleNamespace


def test_record_usage_to_ledger_persists_row(tmp_path: Path):
    """_record_usage_to_ledger must write to cost/token-ledger.jsonl (spec §3.1).

    Before the fix chain, the in-memory-only accumulator left the ledger
    empty (dead-wire); after C10 T1 the write is stateless and unconditional.
    """
    from shenbi.pipeline.dispatch_helper import _record_usage_to_ledger

    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    _record_usage_to_ledger("test-skill", 3, usage, project_dir=tmp_path)

    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists(), "ledger file must be created"
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["skill"] == "test-skill"
    assert records[0]["chapter"] == 3
    assert records[0]["prompt_tokens"] == 100
    assert records[0]["completion_tokens"] == 50


def test_record_usage_to_ledger_chapter_none_falls_back_to_zero(tmp_path: Path):
    """Chapter-less (genesis-style) usage records chapter=0, never crashes."""
    from shenbi.pipeline.dispatch_helper import _record_usage_to_ledger

    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    _record_usage_to_ledger("skill-a", None, usage, project_dir=tmp_path)

    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert records[0]["chapter"] == 0


def test_record_usage_to_ledger_fail_safes(tmp_path: Path):
    """No project_dir → WARN skip; write error → WARN skip, never raise."""
    from shenbi.pipeline.dispatch_helper import _record_usage_to_ledger

    usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    # Missing project_dir: no-op, no file created.
    _record_usage_to_ledger("skill-a", 1, usage, project_dir=None)
    assert not (tmp_path / "cost" / "token-ledger.jsonl").exists()


def test_log_token_usage_handles_bare_usage_object(tmp_path: Path):
    """_log_token_usage must accept a bare Usage object (streaming path).

    The streaming path (_call_llm_streaming_with_retry) returns chunk.usage
    directly — a bare Usage object with prompt_tokens/completion_tokens, NOT
    a response object with a nested .usage attribute. The original hasattr
    (response, "usage") guard would skip it (latent dead-wire). This test
    guards the dual-form handling.
    """
    from shenbi.pipeline.dispatch_helper import _log_token_usage

    # Bare usage object (no nested .usage attr) — the streaming form.
    bare_usage = SimpleNamespace(prompt_tokens=200, completion_tokens=100, total_tokens=300)
    _log_token_usage(bare_usage, "streaming-skill", chapter=5, project_dir=tmp_path)

    # The ledger must have a row (would be empty if the guard skipped it).
    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists()
    records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["prompt_tokens"] == 200
    assert records[0]["chapter"] == 5


def test_log_token_usage_handles_response_wrapper(tmp_path: Path):
    """_log_token_usage still accepts a response object with nested .usage."""
    from shenbi.pipeline.dispatch_helper import _log_token_usage

    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=50, completion_tokens=25, total_tokens=75)
    )
    _log_token_usage(response, "wrapped-skill", chapter=1, project_dir=tmp_path)

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
    _log_token_usage(SimpleNamespace(), "no-usage-skill", chapter=1, project_dir=None)
