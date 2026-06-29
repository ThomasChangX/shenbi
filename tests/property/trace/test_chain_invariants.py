from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


@given(actions=st.lists(st.sampled_from(["A", "B", "C"]), min_size=1, max_size=20))
@settings(max_examples=25)
def test_chain_always_verifies(actions: list[str]) -> None:
    """写任意序列 → replay 全部签名通过。"""
    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        for a in actions:
            w.append(actor="d", actor_role="GATE", action=a, target="t")
        evs = replay(Path(d))
        assert [e.seq for e in evs] == list(range(1, len(actions) + 1))


@given(seed=st.text(min_size=1, max_size=10))
@settings(max_examples=25)
def test_tamper_any_field_breaks_chain(seed: str) -> None:
    """改任一字段 → 签名不匹配 → replay 截断。"""
    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        w.append(actor="d", actor_role="GATE", action="A", target=seed)
        p = Path(d) / "trace.jsonl"
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        rec["target"] = "TAMPERED"
        p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        assert replay(Path(d)) == []
