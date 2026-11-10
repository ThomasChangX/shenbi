from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

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


@given(actions=st.lists(st.sampled_from(["A", "B", "C"]), min_size=1, max_size=20))
@settings(max_examples=25)
def test_chain_always_verifies(actions: list[str]) -> None:
    """写任意序列 → 读取器全部签名通过。"""
    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        for a in actions:
            w.append(actor="d", actor_role="GATE", action=a, target="t")
        evs = _read_events(Path(d))
        assert [e.seq for e in evs] == list(range(1, len(actions) + 1))


@given(seed=st.text(min_size=1, max_size=10))
@settings(max_examples=25)
def test_tamper_any_field_breaks_chain(seed: str) -> None:
    """改任一字段 → 签名不匹配 → 读取器截断。"""
    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        w.append(actor="d", actor_role="GATE", action="A", target=seed)
        p = Path(d) / "trace.jsonl"
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        rec["target"] = "TAMPERED"
        p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        assert _read_events(Path(d)) == []
