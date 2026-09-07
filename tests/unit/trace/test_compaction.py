from __future__ import annotations

from pathlib import Path

from shenbi.trace.compaction import verify_chain
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def test_verify_chain_first_legacy_anchor_ok(tmp_path: Path) -> None:
    # C37: compact() deleted (zero production callers) — set up the
    # COMPACTION anchor event directly via TraceWriter instead.
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="LEGACY_MIGRATION", target="t")
    w.append(
        actor="d",
        actor_role="GATE",
        action="COMPACTION",
        target="trace.jsonl",
        payload={"prev_compaction_seq": None, "snapshot": {}, "truncated_at_seq": 1},
    )
    evs = replay(tmp_path)
    assert verify_chain(evs) == []  # 首条 COMPACTION prev=None 合法


def test_verify_chain_detects_gap(tmp_path: Path) -> None:
    # C37: compact() deleted — write the first COMPACTION anchor directly,
    # then a FRESH writer so the second COMPACTION chains from the real last sig.
    w = TraceWriter(tmp_path)
    w.append(
        actor="d",
        actor_role="GATE",
        action="COMPACTION",
        target="trace.jsonl",
        payload={"prev_compaction_seq": None, "snapshot": {}, "truncated_at_seq": 1},
    )
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
