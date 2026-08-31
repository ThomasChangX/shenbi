"""Spec #36 T5: IDE + legacy subprocess dispatch record estimated rows (F796)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from shenbi.pipeline import dispatch_helper as dh


class _FakeRun:
    returncode = 0
    stdout = "### FILE: out.md\nhi"
    stderr = ""


def _ledger_rows(tmp_path: Path) -> list[dict[str, Any]]:
    f = tmp_path / "cost" / "token-ledger.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").strip().splitlines() if l]


def test_record_estimate_row_writes_estimated_true(tmp_path: Path):
    dh._record_estimate_row("skill-x", 3, "中文 prompt " * 100, tmp_path)
    rows = _ledger_rows(tmp_path)
    assert len(rows) == 1
    data = rows[0]
    assert data["estimated"] is True and data["chapter"] == 3
    assert data["prompt_tokens"] > 0 and data["completion_tokens"] == 0
    assert data["pricing_status"] == "ok"


def test_record_estimate_row_fail_safe_no_project_dir():
    dh._record_estimate_row("s", None, "p", None)  # WARN, must not raise


def test_ide_dispatch_records_estimate_row(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeRun())
    monkeypatch.setattr(dh, "_find_ide_cli", lambda: ["cat", "{dir}"])
    monkeypatch.setattr(dh, "_build_skill_prompt", lambda *a, **k: ("sys", "user", ["out.md"]))
    monkeypatch.setattr(dh, "_write_parsed_outputs", lambda *a, **k: True)
    res = dh._dispatch_via_ide("skill-x", tmp_path, "写第 3 章 chapter-003.md")
    assert res.success, res.stderr
    assert any(r["estimated"] is True for r in _ledger_rows(tmp_path))


def test_legacy_subprocess_records_estimate_row(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeRun())
    monkeypatch.setattr(dh, "_build_skill_prompt", lambda *a, **k: ("sys", "user", ["out.md"]))
    # force legacy route: no API key, no IDE CLI
    monkeypatch.delenv("SHENBI_LLM_API_KEY", raising=False)
    monkeypatch.setattr(dh, "_find_ide_cli", list)
    res = dh.dispatch_skill("skill-x", tmp_path, "写第 3 章 chapter-003.md")
    assert res.success, res.stderr
    assert any(r["estimated"] is True for r in _ledger_rows(tmp_path))
