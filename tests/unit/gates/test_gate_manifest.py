"""F417: behavior tests for gates/gate_manifest.py (previously 0% covered)."""

import json
import threading
from pathlib import Path

from shenbi.gates.gate_manifest import record_gate_result


def test_record_and_read_roundtrip(tmp_path: Path) -> None:
    record_gate_result(
        gate_manifest_dir=tmp_path,
        phase="chapter_loop",
        chapter=3,
        skill="shenbi-review-pacing",
        gate="G3",
        result={"status": "FAIL", "error": "x"},
    )
    data = json.loads((tmp_path / "pipeline-manifest.json").read_text(encoding="utf-8"))
    entry = data["gates"]["chapter_loop"]["3"]["shenbi-review-pacing"]["G3"]
    assert entry["gate"] == "G3"
    assert entry["result"] == {"status": "FAIL", "error": "x"}


def test_record_is_idempotent_merge_not_replace(tmp_path: Path) -> None:
    record_gate_result(tmp_path, "chapter_loop", 1, "shenbi-a", "G2", {"status": "PASS"})
    record_gate_result(tmp_path, "chapter_loop", 1, "shenbi-b", "G4", {"status": "PASS"})
    record_gate_result(tmp_path, "chapter_loop", 2, "shenbi-a", "G2", {"status": "PASS"})
    data = json.loads((tmp_path / "pipeline-manifest.json").read_text(encoding="utf-8"))
    ch1 = data["gates"]["chapter_loop"]["1"]
    assert set(ch1) == {"shenbi-a", "shenbi-b"}
    assert "2" in data["gates"]["chapter_loop"]


def test_concurrent_writes_no_lost_update(tmp_path: Path) -> None:
    """The per-path lock must serialize read-merge-write: all 20 concurrent
    gate records survive (no lost-update clobbering).
    """

    def worker(i: int) -> None:
        record_gate_result(
            tmp_path, "chapter_loop", 1, f"shenbi-skill-{i}", "G3", {"status": "PASS"}
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    data = json.loads((tmp_path / "pipeline-manifest.json").read_text(encoding="utf-8"))
    recorded = data["gates"]["chapter_loop"]["1"]
    assert len(recorded) == 20
