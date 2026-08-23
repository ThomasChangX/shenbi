"""F408: run_gate_g3 must not fabricate progress.json evidence (fail-closed)."""

import json
from pathlib import Path
from typing import Any

from shenbi.pipeline.dispatch_helper import run_gate_g3


def _entries(data: Any) -> list[dict[str, Any]]:
    """Flatten gate_manifest storage (nested or list) into gate-record dicts."""
    out: list[dict[str, Any]] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict) and "gate" in v:
            out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(data)
    return out


def _status(e: dict[str, Any]) -> Any:
    r = e.get("result")
    return r.get("status") if isinstance(r, dict) else e.get("status")


def test_missing_progress_fails_closed_and_writes_nothing(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    result = run_gate_g3("shenbi-review-pacing", rd, chapter=1, phase="chapter_loop")
    assert result["status"] == "FAIL"
    assert "F408" in result.get("error", "")
    assert not (rd / "progress.json").exists()  # no fabricated evidence written


def test_manifest_records_fail(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    run_gate_g3("shenbi-review-pacing", rd, chapter=1, phase="chapter_loop")
    manifest = rd / "pipeline-manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    g3 = [e for e in _entries(data) if e.get("gate") == "G3"]
    assert g3 and all(_status(e) == "FAIL" for e in g3)


def test_existing_progress_still_runs_gate(tmp_path: Path) -> None:
    """With progress.json present, the real G3 CLI subprocess still runs."""
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text("{}", encoding="utf-8")
    result = run_gate_g3("shenbi-review-pacing", rd)  # no chapter/phase → no manifest
    assert "status" in result  # subprocess-produced result (not the fail-closed early return)
    assert "F408" not in result.get("error", "")
