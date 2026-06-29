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
