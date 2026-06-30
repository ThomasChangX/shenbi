from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.record import record_audit_outcome
from shenbi.audit.write_audit import AuditResult


def _res(violations: tuple[str, ...] = (), drift: tuple[str, ...] = ()) -> AuditResult:
    return AuditResult(skill="s", violations=violations, drift=drift, checked_files=("a",))


def test_pass_writes_unblocked_ledger(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res())
    assert ok is True
    line = json.loads((rd / "write-audit.jsonl").read_text(encoding="utf-8").strip())
    assert line["blocked"] is False


def test_fail_writes_blocked_ledger(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res(violations=("越权",)))
    assert ok is False
    lines = (rd / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    assert last["blocked"] is True
    assert last["violations"] == ["越权"]


def test_drift_also_blocks(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res(drift=("drift: x",)))
    assert ok is False
