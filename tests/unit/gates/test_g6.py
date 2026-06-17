"""Unit tests for G6: T3 pipeline check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shenbi.gates.g6 import gate_G6
pytestmark = pytest.mark.unit



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
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)
        (truth_dir / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n  max_distance: 5\n  plant_chapter: 1\n",
            encoding="utf-8",
        )
        result_str = gate_G6("long-form", str(round_dir), str(project_dir))
        parsed = json.loads(result_str)
        # Strong assertions: gate must complete structured output.
        assert parsed["status"] in {"PASS", "FAIL"}, "gate must complete, not raise"
        assert parsed["gate"] == "G6"
        assert isinstance(parsed["checks"], list)

    def test_g67_density_is_none_when_no_chapters(self, tmp_path: Path) -> None:
        """Regression: density reported as None when chapters/ is absent
        but unresolved hooks exist (so the unresolved-branch runs and
        reads density). Before fix: density was unbound → NameError.
        """
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)
        (truth_dir / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n",
            encoding="utf-8",
        )
        result_str = gate_G6("long-form", str(round_dir), str(project_dir))
        parsed = json.loads(result_str)
        assert parsed["status"] in {"PASS", "FAIL"}, "gate must complete, not raise"
        assert parsed["gate"] == "G6"
        checks = parsed["checks"]
        # The G6.7 hook-density check MUST run when truth/pending_hooks.md
        # exists — that's the branch where density was previously unbound.
        g67 = next((c for c in checks if c.get("id") == "G6.7"), None)
        assert g67 is not None, "G6.7 must execute when pending_hooks.md exists"
        assert "density" in g67, "G6.7 must include density field even when chapters absent"
        assert g67["density"] is None, "density must be None when chapters/ is absent"


def _make_chapter(parent: Path, num: int, body: str) -> Path:
    ch = parent / "chapters" / f"chapter-{num:03d}.md"
    ch.parent.mkdir(parents=True, exist_ok=True)
    ch.write_text(body, encoding="utf-8")
    return ch


class TestG6ErrorPaths:
    """Gate-level error paths for G6 (PR-52 Step 6).

    G6 reads tests/tiers/deps.json for t3-pipelines min_chapter_ratio and
    derives expected chapter counts from project_dir/novel.json and
    genre-config.json. Default min_ratio is 0.5. With default
    target_words=100000 and chapter_word floor 3000, expected ~= 34 and
    min_chapters ~= 17, so any small chapter set triggers G6.1.
    """

    @pytest.mark.unit
    def test_g6_no_chapters_dir_fails(self, tmp_path: Path) -> None:
        """A project_dir with no chapters/ directory -> G6.1:no_chapters_dir."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert result["status"] == "FAIL"
        assert "G6.1:no_chapters_dir" in result["must_fix"]

    @pytest.mark.unit
    def test_g6_below_min_chapter_count_fails(self, tmp_path: Path) -> None:
        """Fewer chapters than min_chapters -> G6.1:count<min reason."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)  # only 1 chapter
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        # G6.1 below-min reason format: "G6.1:{len}<{min}(ceil({expected}*{ratio}))".
        # "(ceil(" is unique to this reason (not present in no_chapters_dir).
        assert any(mf.startswith("G6.1:") and "(ceil(" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_numbering_gap_warns(self, tmp_path: Path) -> None:
        """Chapters 1 and 3 (missing 2) -> G6.2:chapter_gaps."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)
        _make_chapter(project_dir, 3, "正文内容。" * 400)
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert "G6.2:chapter_gaps" in result["must_fix"]

    @pytest.mark.unit
    def test_g6_g4_failure_on_short_chapter(self, tmp_path: Path) -> None:
        """A chapter under the 3000-char floor fails G4 -> G6.3:{ch.name}."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "短内容。")  # well below floor
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any(mf.startswith("G6.3:") for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_high_hook_density_warns(self, tmp_path: Path) -> None:
        """Many hooks across few chapters -> G6.7:high_hook_density (>3/chapter)."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)
        truth = project_dir / "truth"
        truth.mkdir()
        hooks = "## hooks\n"
        for i in range(6):  # 6 hooks / 1 chapter = 6.0 > 3
            hooks += f"\n- id: hook-{i:03d}\n  state: RESOLVED\n"
        (truth / "pending_hooks.md").write_text(hooks, encoding="utf-8")
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any("G6.7:high_hook_density" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_low_hook_density_warns(self, tmp_path: Path) -> None:
        """One hook across many chapters -> G6.7:low_hook_density (<0.3/chapter)."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        for i in range(1, 9):  # 8 chapters
            _make_chapter(project_dir, i, "正文内容。" * 400)
        truth = project_dir / "truth"
        truth.mkdir()
        (truth / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: RESOLVED\n", encoding="utf-8"
        )
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any("G6.7:low_hook_density" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_hook_max_distance_exceeded_warns(self, tmp_path: Path) -> None:
        """A hook planted early with a long-since-passed max_distance -> G6.7:max_distance_exceeded."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)
        _make_chapter(project_dir, 10, "正文内容。" * 400)
        truth = project_dir / "truth"
        truth.mkdir()
        (truth / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n  max_distance: 3\n  plant_chapter: 1\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any("G6.7:max_distance_exceeded" in mf for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_unresolved_hooks_reported_in_check(self, tmp_path: Path) -> None:
        """Unresolved hooks surface in the G6.7 check dict (status may still be PASS)."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)
        truth = project_dir / "truth"
        truth.mkdir()
        (truth / "pending_hooks.md").write_text(
            "## hooks\n\n- id: hook-001\n  state: PENDING\n", encoding="utf-8"
        )
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        g67 = next(c for c in result["checks"] if c.get("id") == "G6.7")
        assert g67["unresolved"] >= 1

    @pytest.mark.unit
    def test_g6_volume_mismatch_fails(self, tmp_path: Path) -> None:
        """A volume_map defining a range with no matching chapters -> G6.11:no_chapters."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。" * 400)
        outline = project_dir / "outline"
        outline.mkdir()
        (outline / "volume_map.md").write_text(
            "# Volume Map\n\n第一卷 chapters 100-110\n第二卷 chapters 200-210\n",
            encoding="utf-8",
        )
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any(mf.startswith("G6.11:no_chapters") for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_ghost_character_detected(self, tmp_path: Path) -> None:
        """A dead character in character_matrix.md who still appears in a chapter -> G6.6."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。老王走了过来。\n")
        truth = project_dir / "truth"
        truth.mkdir()
        (truth / "character_matrix.md").write_text(
            "| 角色 | 状态 |\n| 老王 | 死亡 |\n", encoding="utf-8"
        )
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any(mf.startswith("G6.6:老王") for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_sensitive_words_detected(self, tmp_path: Path) -> None:
        """A chapter containing a sensitive-word token -> G6.12:{word}:{ch.name}."""
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        project_dir = tmp_path / "project"
        _make_chapter(project_dir, 1, "正文内容。 台独 。\n")
        result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
        assert any(mf.startswith("G6.12:台独") for mf in result["must_fix"])

    @pytest.mark.unit
    def test_g6_empty_chapters_yield_skip_for_continuity_and_pacing(self) -> None:
        """Empty chapters list -> check_continuity and check_pacing both SKIP.
        Exercised at the extracted-check level (G6.4/G6.5 delegates).
        """
        from shenbi.gates.g6_checks import check_continuity, check_pacing

        cc, cmf = check_continuity([])
        pc, pmf = check_pacing([])
        assert any(c["s"] == "SKIP" and c["id"] == "G6.4" for c in cc)
        assert any(c["s"] == "SKIP" and c["id"] == "G6.5" for c in pc)

@pytest.mark.unit
def test_g611_passes_with_volume_map_and_no_chapters(tmp_path: Path) -> None:
    """volume_map.md with volume ranges but no chapters/ -> G6.11 PASS with note."""
    project_dir = tmp_path / "project"
    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "volume_map.md").write_text(
        "## 第一卷\nchapters 1-10\n", encoding="utf-8"
    )
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g611 = next((c for c in result["checks"] if c.get("id") == "G6.11"), None)
    assert g611 is not None
    assert g611["note"] == "no chapters/ to verify"
