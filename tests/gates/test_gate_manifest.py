# tests/gates/test_gate_manifest.py
import json
import tempfile
from pathlib import Path

from shenbi.gates.gate_manifest import (
    GATE_MANIFEST_FILENAME,
    get_gate_result,
    record_gate_result,
)


def test_record_and_retrieve_gate_result():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        record_gate_result(
            gate_manifest_dir=manifest_dir,
            phase="chapter_loop",
            chapter=5,
            skill="shenbi-review-continuity",
            gate="G4",
            result={"passed": True, "checks": {"G4.cd.verdict": "passed"}},
        )
        record_gate_result(
            gate_manifest_dir=manifest_dir,
            phase="chapter_loop",
            chapter=5,
            skill="shenbi-review-resonance",
            gate="G4",
            result={"passed": False, "checks": {"G4.rr.verdict": "failed"}},
        )

        # Retrieve
        result = get_gate_result(manifest_dir, "chapter_loop", 5, "shenbi-review-continuity", "G4")
        assert result is not None
        assert result["passed"] is True

        result2 = get_gate_result(manifest_dir, "chapter_loop", 5, "shenbi-review-resonance", "G4")
        assert result2 is not None
        assert result2["passed"] is False


def test_manifest_structure_is_hierarchical():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        record_gate_result(
            manifest_dir, "genesis", 0, "shenbi-worldbuilding", "G2", {"passed": True}
        )
        record_gate_result(
            manifest_dir, "chapter_loop", 1, "shenbi-chapter-drafting", "G4", {"passed": True}
        )
        record_gate_result(
            manifest_dir, "chapter_loop", 2, "shenbi-chapter-drafting", "G4", {"passed": False}
        )

        manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "gates" in data
        assert "genesis" in data["gates"]
        assert "chapter_loop" in data["gates"]
        # Chapter 1 and 2 should both be present
        assert "1" in data["gates"]["chapter_loop"] or 1 in data["gates"]["chapter_loop"]


def test_get_gate_result_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        result = get_gate_result(manifest_dir, "chapter_loop", 99, "nonexistent", "G4")
        assert result is None


def test_concurrent_manifest_writes_do_not_lose_results():
    """The read-modify-write is NOT atomic; concurrent writers must be serialized
    by a per-path threading.Lock so no results are lost. See Spec §3.1.1.
    """
    import threading

    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        n_writers = 10
        n_writes_each = 20

        def writer(skill_suffix: int) -> None:
            for ch in range(n_writes_each):
                record_gate_result(
                    gate_manifest_dir=manifest_dir,
                    phase="chapter_loop",
                    chapter=ch,
                    skill=f"shenbi-skill-{skill_suffix}",
                    gate="G4",
                    result={"passed": True},
                )

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writers should have recorded their results (no lost updates)
        manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        chapter_skills = data["gates"]["chapter_loop"]
        # For each chapter, all n_writers distinct skills must be present
        for ch in range(n_writes_each):
            skills_for_ch = chapter_skills[str(ch)]
            assert len(skills_for_ch) == n_writers, (
                f"chapter {ch}: expected {n_writers} skill entries, got {len(skills_for_ch)}"
            )
