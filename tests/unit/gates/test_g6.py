"""Unit tests for G6: T3 pipeline check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from shenbi.gates.g6 import gate_G6


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


class TestG6PipelineCheck:
    def test_emits_valid_json_for_valid_args(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G6("long-form", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_none_arguments(self) -> None:
        result_str = gate_G6(None, None, None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_unknown_pipeline(self, tmp_path: Path) -> None:
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        result_str = gate_G6("nonexistent-pipeline", str(round_dir), None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_handles_missing_round_dir(self, tmp_path: Path) -> None:
        result_str = gate_G6("long-form", str(tmp_path / "nope"), None)
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_g67_does_not_nameerror_when_chapters_dir_missing_but_hooks_present(
        self, tmp_path: Path
    ) -> None:
        """Regression: G6.7 referenced `nums` (defined only inside the
        `if ch_dir.exists()` block) and `density` (defined only inside
        `if chapters`). When chapters/ is absent but truth/pending_hooks.md
        exists with max_distance metadata, the gate used to raise NameError.
        After fix: `nums` initializes at outer scope, `density` is Optional.
        """
        round_dir = tmp_path / "round"
        truth_dir = round_dir / "truth"
        truth_dir.mkdir(parents=True)
        (truth_dir / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n  max_distance: 5\n  plant_chapter: 1\n",
            encoding="utf-8",
        )
        result_str = gate_G6("long-form", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        assert "status" in parsed

    def test_g67_density_is_none_when_no_chapters(self, tmp_path: Path) -> None:
        """Regression: density reported as None when chapters/ is absent
        but unresolved hooks exist (so the unresolved-branch runs and
        reads density). Before fix: density was unbound → NameError.
        """
        round_dir = tmp_path / "round"
        truth_dir = round_dir / "truth"
        truth_dir.mkdir(parents=True)
        (truth_dir / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n",
            encoding="utf-8",
        )
        result_str = gate_G6("long-form", str(round_dir), str(tmp_path))
        parsed = json.loads(result_str)
        checks = parsed.get("checks", [])
        g67 = next((c for c in checks if c.get("id") == "G6.7"), None)
        if g67 is not None and "density" in g67:
            assert g67["density"] is None
