"""Tests for the G4 checker that consumes post-write integrity findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.gates.g4.generic import g4_post_write_integrity


def _write_findings(project_dir: Path, chapter: int, findings: list[dict[str, Any]]) -> None:
    p = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in findings) + "\n",
        encoding="utf-8",
    )


class TestG4PostWriteIntegrity:
    def test_no_findings_passes(self, tmp_path):
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "PASS"

    def test_model_leakage_fails(self, tmp_path):
        _write_findings(
            tmp_path,
            56,
            [
                {
                    "file": "chapters/chapter-56.md",
                    "finding": "G4.pi.model_leakage:chapter-56.md — leak",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=56)
        assert result["status"] == "FAIL"
        assert any("model_leakage" in c["id"] for c in result["checks"])

    def test_fence_imbalance_warns(self, tmp_path):
        _write_findings(
            tmp_path,
            1,
            [
                {
                    "file": "chapters/chapter-1.md",
                    "finding": "G4.pi.fence_imbalance:chapter-1.md — odd",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "WARN"
