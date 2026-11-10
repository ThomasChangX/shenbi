from __future__ import annotations

from pathlib import Path

from shenbi.trace.compaction import verify_chain
from shenbi.trace.event import TraceEvent
from shenbi.trace.writer import TraceWriter


def _read_events(round_dir: Path) -> list[TraceEvent]:
    """Pure reader: parse trace.jsonl, stop at first torn line / bad signature.

    The pre-#86 replay reader also truncated the file on torn lines; tests
    only consume the returned events, so the helper is read-only.
    """
    from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign

    path = Path(round_dir) / "trace.jsonl"
    if not path.exists():
        return []
    prev = GENESIS_PREV
    out: list[TraceEvent] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            event = TraceEvent.model_validate_json(ln)
        except Exception:
            break
        if sign(prev, canonical_payload(event), event.schema_version) != event.signature:
            break
        out.append(event)
        prev = event.signature
    return out


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
    evs = _read_events(tmp_path)
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
    evs = _read_events(tmp_path)
    issues = verify_chain(evs)
    assert any("gap" in i.lower() or "monotonic" in i.lower() for i in issues)
