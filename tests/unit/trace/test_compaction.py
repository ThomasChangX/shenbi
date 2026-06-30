from __future__ import annotations

from pathlib import Path

from shenbi.trace.compaction import compact, verify_chain
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def test_compact_keeps_only_compaction_event(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    w.append(actor="d", actor_role="GATE", action="B", target="t")
    c = compact(tmp_path, snapshot={"done": ["x"]})
    assert c.action == "COMPACTION"
    evs = replay(tmp_path)
    assert len(evs) == 1 and evs[0].action == "COMPACTION"
    assert evs[0].payload["snapshot"] == {"done": ["x"]}


def test_verify_chain_first_legacy_anchor_ok(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="LEGACY_MIGRATION", target="t")
    compact(tmp_path, snapshot={})
    evs = replay(tmp_path)
    assert verify_chain(evs) == []  # 首条 COMPACTION prev=None 合法


def test_verify_chain_detects_gap(tmp_path: Path) -> None:
    compact(tmp_path, snapshot={})  # rewrites trace.jsonl: COMPACTION seq=1, prev=None
    # N1 fix: compact() rewrote the file, so the old TraceWriter is stale.
    # Use a FRESH writer so the second COMPACTION chains from the real last sig.
    w = TraceWriter(tmp_path)
    w.append(
        actor="d",
        actor_role="GATE",
        action="COMPACTION",
        target="trace.jsonl",
        payload={"prev_compaction_seq": 99, "snapshot": {}, "truncated_at_seq": 1},
    )
    evs = replay(tmp_path)
    issues = verify_chain(evs)
    assert any("gap" in i.lower() or "monotonic" in i.lower() for i in issues)
