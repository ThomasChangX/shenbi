"""Filename-partition semantics of make_composite_checker (spec 13 R4a')."""

from __future__ import annotations

import json

from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker
from shenbi.gates.shared import passed


def _structural_stub(fps, rd, project_dir, repo_root):
    """Records what the structural slot received; per-file PASS entries."""
    return passed(
        "stub-structural",
        [{"id": f"stub-structural:{fp}", "s": "PASS"} for fp in (fps or [])],
    )


_VALID_SIDECAR = {
    "$schema": "shenbi-decisions-v1",
    "skill": "shenbi-genre-config",
    "chapter": 1,
    "selections": [],
    "adjustments": [],
    "produced_at": "2026-08-29T00:00:00",
}


class TestFilenamePartition:
    def test_non_decisions_json_routes_to_structural(self, tmp_path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps({"version": "1.0", "auditDimensions": {"texture": True}}),
            encoding="utf-8",
        )
        composite = make_composite_checker(_structural_stub, g4_decisions)
        result = composite(["genre-config.json"], str(tmp_path), None, None)
        data = json.loads(result)
        assert any("genre-config.json" in c.get("id", "") for c in data["checks"])
        assert data["status"] == "PASS"

    def test_decisions_json_routes_to_decisions_checker(self, tmp_path):
        (tmp_path / "genre-config-decisions.json").write_text(
            json.dumps(_VALID_SIDECAR), encoding="utf-8"
        )
        composite = make_composite_checker(_structural_stub, g4_decisions)
        result = composite(["genre-config-decisions.json"], str(tmp_path), None, None)
        data = json.loads(result)
        assert any(
            c.get("file") == "genre-config-decisions.json" and c.get("s") == "PASS"
            for c in data["checks"]
        )
        assert all("genre-config-decisions" not in c.get("id", "") for c in data["checks"])
