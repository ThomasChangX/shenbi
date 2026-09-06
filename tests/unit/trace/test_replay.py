from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def test_replay_returns_chained_events(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    w.append(actor="d", actor_role="GATE", action="B", target="t")
    evs = replay(tmp_path)
    assert [e.seq for e in evs] == [1, 2]


def test_replay_truncates_torn_tail(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + '{"seq":2,"incomplete":', encoding="utf-8")
    evs = replay(tmp_path)
    assert [e.seq for e in evs] == [1]  # 撕裂行被截断
    assert "incomplete" not in p.read_text(encoding="utf-8")


def test_replay_drops_bad_signature(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    rec["actor"] = "tampered"  # 改了内容但签名没重算
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    assert replay(tmp_path) == []


def test_replay_truncation_warns_with_reason(tmp_path: Path) -> None:
    """C29 R4 (F620): torn tail triggers replay_truncated WARN with byte accounting."""
    from structlog.testing import capture_logs

    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    torn = '{"seq":2,"incomplete":'
    p.write_text(p.read_text(encoding="utf-8") + torn, encoding="utf-8")

    with capture_logs() as logs:
        evs = replay(tmp_path)

    assert [e.seq for e in evs] == [1]
    warns = [
        e for e in logs if e.get("log_level") == "warning" and e["event"] == "replay_truncated"
    ]
    assert len(warns) == 1
    entry = warns[0]
    assert entry["drop_reason"] == "torn_line"
    assert entry["kept_events"] == 1
    assert entry["dropped_chars"] == len(torn)


def test_replay_signature_gap_warns(tmp_path: Path) -> None:
    """C29 R4 (F620): signature-gap truncation also WARNs."""
    from structlog.testing import capture_logs

    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    rec["actor"] = "tampered"
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")

    with capture_logs() as logs:
        assert replay(tmp_path) == []

    warns = [
        e for e in logs if e.get("log_level") == "warning" and e["event"] == "replay_truncated"
    ]
    assert len(warns) == 1
    assert warns[0]["drop_reason"] == "signature_gap"
    assert warns[0]["kept_events"] == 0
