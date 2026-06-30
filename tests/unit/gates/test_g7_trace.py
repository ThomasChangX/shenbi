from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g7_trace import audit_trace
from shenbi.trace.writer import TraceWriter


def test_audit_clean_trace(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    issues, checks = audit_trace(rd)
    assert issues == []
    assert any(c["id"] == "G7T.chain" for c in checks)


def test_audit_detects_tamper(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = rd / "trace.jsonl"
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    rec["actor"] = "hacker"
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    issues, _ = audit_trace(rd)
    assert any("signature" in i.lower() or "tamper" in i.lower() for i in issues)


def test_audit_no_trace_ok(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    issues, checks = audit_trace(rd)
    assert issues == []
    assert any(c["id"] == "G7T.absent" for c in checks)
