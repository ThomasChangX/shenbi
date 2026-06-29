from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.event import GENESIS_PREV
from shenbi.trace.writer import TraceWriter


def test_append_writes_jsonl_line(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    e = w.append(actor="d", actor_role="GATE", action="INIT", target="progress.json")
    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["seq"] == 1 and rec["action"] == "INIT"
    assert rec["signature"] == e.signature


def test_seq_monotonic_and_chained(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    e1 = w.append(actor="d", actor_role="GATE", action="A", target="t")
    e2 = w.append(actor="d", actor_role="GATE", action="B", target="t")
    assert e1.seq == 1 and e2.seq == 2
    assert e2.signature != e1.signature
    assert w.last_signature() == e2.signature


def test_new_writer_resumes_existing_trace(tmp_path: Path) -> None:
    w1 = TraceWriter(tmp_path)
    w1.append(actor="d", actor_role="GATE", action="A", target="t")
    w2 = TraceWriter(tmp_path)  # 复用同一文件
    e = w2.append(actor="d", actor_role="GATE", action="B", target="t")
    assert e.seq == 2  # 接续而非重置
    # GENESIS_PREV import ensures the module-level anchor is exercised.
    assert GENESIS_PREV == "0" * 64
