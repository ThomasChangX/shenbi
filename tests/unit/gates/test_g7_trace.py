from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def _write_two_events(rd: Path) -> list[str]:
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    w.append(actor="d", actor_role="GATE", action="B", target="t")
    p = rd / "trace.jsonl"
    return p.read_text(encoding="utf-8").strip().splitlines()


@pytest.mark.c13_regression
def test_g7_midfile_bad_line_is_tamper_candidate(tmp_path: Path) -> None:
    """F535: an injected invalid-JSON line mid-file must be detected as a
    tamper candidate, not silently truncate the chain to a PASS prefix.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    lines = _write_two_events(rd)
    bad = lines[:1] + ["{not json"] + lines[1:]
    (rd / "trace.jsonl").write_text("\n".join(bad) + "\n", encoding="utf-8")
    issues, checks = audit_trace(rd)
    assert any("torn" in i for i in issues)
    torn = [c for c in checks if c["id"] == "G7T.torn"]
    assert torn and torn[0]["s"] == "FAIL"
    # F410: line-number and total disclosure so truncation is observable
    assert torn[0]["torn_line"] == 2
    assert torn[0]["total_lines"] >= 3


@pytest.mark.c13_regression
def test_g7_tail_torn_line_disclosed(tmp_path: Path) -> None:
    """F410: a torn final line is disclosed with counts instead of a silent
    prefix-PASS.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    lines = _write_two_events(rd)
    torn_text = "\n".join(lines + ['{"seq": 3, "trunc']) + "\n"
    (rd / "trace.jsonl").write_text(torn_text, encoding="utf-8")
    issues, checks = audit_trace(rd)
    assert any("torn" in i for i in issues)
    torn = [c for c in checks if c["id"] == "G7T.torn"]
    assert torn and torn[0]["total_lines"] == 3
