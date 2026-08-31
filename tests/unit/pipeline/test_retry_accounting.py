"""Spec #36 T7: retry-attempt usage accounting bifurcation + DISPATCH trace events."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from shenbi.pipeline import dispatch_helper as dh


def _fake_client(stream: Any) -> Any:
    class Client:
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: stream))

    return Client()


class _MidstreamStream:
    """Stream established, broken mid-stream — usage never delivered."""

    def __iter__(self):  # type: ignore[no-untyped-def]
        yield SimpleNamespace(
            usage=None,
            choices=[SimpleNamespace(finish_reason=None, delta=SimpleNamespace(content="部分"))],
        )
        raise ConnectionError("reset")


class _UsageThenErrorStream:
    """Usage delivered, then failure — stream-end failure form."""

    def __iter__(self):  # type: ignore[no-untyped-def]
        yield SimpleNamespace(
            usage=None,
            choices=[SimpleNamespace(finish_reason="stop", delta=SimpleNamespace(content="ok"))],
        )
        yield SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=4, total_tokens=14),
            choices=[],
        )
        raise ConnectionError("reset-after-usage")


def _ledger_rows(tmp_path: Path) -> list[dict[str, Any]]:
    f = tmp_path / "cost" / "token-ledger.jsonl"
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text(encoding="utf-8").strip().splitlines() if line]


def _dispatch(monkeypatch, tmp_path: Path, stream: Any):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "k")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    with (
        patch("openai.OpenAI") as mock_openai,
        patch(
            "shenbi.pipeline.dispatch_helper._build_skill_prompt",
            return_value=("sys", "user", ["chapters/chapter-1.md"]),
        ),
    ):
        mock_openai.return_value.chat.completions.create.return_value = stream
        return dh._dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")


def test_usage_acc_semantics_midstream():
    acc: dict[str, Any] = {}
    try:
        dh._call_llm_streaming(
            _fake_client(_MidstreamStream()),
            "m",
            [{"role": "user", "content": "写"}],
            usage_acc=acc,
        )
    except ConnectionError:
        pass
    assert acc.get("usage") is None
    assert acc.get("attempts", 0) >= 1


def test_midstream_failure_gets_estimate_row(tmp_path: Path, monkeypatch):
    res = _dispatch(monkeypatch, tmp_path, _MidstreamStream())
    assert not res.success
    rows = _ledger_rows(tmp_path)
    assert any(r.get("estimated") is True and r["attempt"] >= 1 for r in rows)


def test_stream_end_failure_records_real_usage(tmp_path: Path, monkeypatch):
    res = _dispatch(monkeypatch, tmp_path, _UsageThenErrorStream())
    assert not res.success
    rows = _ledger_rows(tmp_path)
    assert any(
        r.get("estimated") is not True and r["prompt_tokens"] == 10 and r["attempt"] >= 1
        for r in rows
    )


def test_success_emits_dispatch_trace_with_finish_reason(tmp_path: Path, monkeypatch):
    (tmp_path / "trace.jsonl").write_text("", encoding="utf-8")  # pre-existing trace stream
    fake_stream = [
        SimpleNamespace(
            usage=None,
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    delta=SimpleNamespace(content="### FILE: chapters/chapter-1.md\nbody\n"),
                )
            ],
        ),
        SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=1, total_tokens=6), choices=[]
        ),
    ]
    res = _dispatch(monkeypatch, tmp_path, fake_stream)
    assert res.success, res.stderr
    events = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
        if line
    ]
    disp = [e for e in events if e["action"] == "DISPATCH"]
    assert disp and disp[-1]["payload"]["finish_reason"] == "stop"
    assert disp[-1]["payload"]["success"] is True
