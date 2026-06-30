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
    project_dir.mkdir()

    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "volume_map.md").write_text("## 第一卷\nchapters 1-10\n", encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g611 = next((c for c in result["checks"] if c.get("id") == "G6.11"), None)
    assert g611 is not None
    assert g611["note"] == "no chapters/ to verify"


@pytest.mark.unit
def test_g6_volume_map_no_ranges_skips(tmp_path: Path) -> None:
    """volume_map.md without chapter ranges -> G6.11 SKIP."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    outline = project_dir / "outline"
    outline.mkdir(parents=True)
    (outline / "volume_map.md").write_text("## 第一卷\nContent without ranges.\n", encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g611 = next((c for c in result["checks"] if c.get("id") == "G6.11"), None)
    assert g611 is not None
    assert g611["s"] == "SKIP"


@pytest.mark.unit
def test_g6_g61_passes_with_sufficient_chapters(tmp_path: Path) -> None:
    """Enough chapters to meet G6.1 min requirement -> G6.1 PASS."""
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "novel.json").write_text('{"target_words": 5000}', encoding="utf-8")
    (project_dir / "genre-config.json").write_text(
        '{"chapter_word": {"default": 5000}}', encoding="utf-8"
    )
    (project_dir / "chapters").mkdir()
    (project_dir / "chapters" / "chapter-001.md").write_text(
        "# 第1章\n\n正文内容。\n", encoding="utf-8"
    )
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g61 = next((c for c in result["checks"] if c.get("id") == "G6.1"), None)
    assert g61 is not None
    assert g61["s"] == "PASS"


@pytest.mark.unit
def test_g6_g66_passes_when_no_ghosts(tmp_path: Path) -> None:
    """character_matrix with no dead characters -> G6.6 PASS."""
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "novel.json").write_text('{"target_words": 5000}', encoding="utf-8")
    (project_dir / "genre-config.json").write_text(
        '{"chapter_word": {"default": 5000}}', encoding="utf-8"
    )
    (project_dir / "chapters").mkdir()
    (project_dir / "chapters" / "chapter-002.md").write_text(
        "# 第2章\n\n正文内容。\n", encoding="utf-8"
    )
    (project_dir / "chapters" / "chapter-003.md").write_text(
        "# 第3章\n\n正文内容。\n", encoding="utf-8"
    )
    truth = project_dir / "truth"
    truth.mkdir()
    (truth / "character_matrix.md").write_text(
        "| 角色 | 状态 |\n| 主角 | 存活 |\n", encoding="utf-8"
    )
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g66 = next((c for c in result["checks"] if c.get("id") == "G6.6"), None)
    assert g66 is not None
    assert g66["s"] == "PASS"


@pytest.mark.unit
def test_g6_volume_boundary_passes_with_chapters(tmp_path: Path) -> None:
    """volume_map.md with ranges and chapters -> G6.11 PASS."""
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "novel.json").write_text('{"target_words": 5000}', encoding="utf-8")
    (project_dir / "genre-config.json").write_text(
        '{"chapter_word": {"default": 5000}}', encoding="utf-8"
    )
    ch_dir = project_dir / "chapters"
    ch_dir.mkdir()
    (ch_dir / "chapter-001.md").write_text("正文内容。\n", encoding="utf-8")
    (ch_dir / "chapter-002.md").write_text("正文内容。\n", encoding="utf-8")
    outline = project_dir / "outline"
    outline.mkdir()
    (outline / "volume_map.md").write_text("## 第一卷\nchapters 1-2\n", encoding="utf-8")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g611 = next((c for c in result["checks"] if c.get("id") == "G6.11"), None)
    assert g611 is not None
    assert g611["s"] == "PASS"


# ---------------------------------------------------------------------------
# G6.8 / G6.9 / G6.11 branch coverage (PR-56 coverage fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_g68_ghost_voice_detected(tmp_path: Path) -> None:
    """A character without a voice_profile who appears in a chapter -> G6.8:ghost_voice.

    Covers the ghost-detection branch (g6.py:175-179): name >=2 chars, no
    voice_profile, name substring present in a sampled chapter.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_chapter(project_dir, 1, "老王走了过来。正文内容。" * 100)
    char_dir = project_dir / "characters"
    char_dir.mkdir()
    (char_dir / "wang.md").write_text("name: 老王\n\n# 老王\n\n一个配角。\n", encoding="utf-8")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    assert any("G6.8:ghost_voice:老王" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g68_catchphrase_not_found_warns(tmp_path: Path) -> None:
    """Character with a voice_profile whose catchphrase is absent from chapters -> G6.8 WARN.

    Covers the catchphrase-not-found branch (g6.py:191-198).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_chapter(project_dir, 1, "主角说了一些普通的话。正文内容。" * 100)
    char_dir = project_dir / "characters"
    char_dir.mkdir()
    (char_dir / "hero.md").write_text(
        'name: 主角\nvoice_profile:\n  "专属口头禅"\n', encoding="utf-8"
    )
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g68_warns = [c for c in result["checks"] if c.get("id") == "G6.8" and c.get("s") == "WARN"]
    assert any("主角" in c.get("r", "") for c in g68_warns)


@pytest.mark.unit
def test_g68_voice_profile_pass_when_catchphrase_present(tmp_path: Path) -> None:
    """Character whose catchphrase appears in a chapter -> no G6.8 WARN, PASS emitted.

    Covers the found_any=True break (g6.py:187-190) and the trailing PASS check
    (g6.py:199-206).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_chapter(project_dir, 1, "主角大喊：必胜口号。正文内容。" * 100)
    char_dir = project_dir / "characters"
    char_dir.mkdir()
    (char_dir / "hero.md").write_text(
        'name: 主角\nvoice_profile:\n  "必胜口号"\n', encoding="utf-8"
    )
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g68 = [c for c in result["checks"] if c.get("id") == "G6.8"]
    assert any(c.get("s") == "PASS" for c in g68)
    assert not any(c.get("s") == "WARN" and "主角" in c.get("r", "") for c in g68)


@pytest.mark.unit
def test_g69_world_rule_limit_exceeded(tmp_path: Path) -> None:
    """A chapter violating an upper-bound numerical rule -> G6.9:limit_exceeded.

    Covers the constraint-extraction + chapter-scan violation branch
    (g6.py:213-258). rules.md declares 队伍人数 不超过3人; a chapter states
    队伍人数 reached 5人.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_chapter(project_dir, 1, "队伍人数达到了5人。正文内容。" * 100)
    world = project_dir / "world"
    world.mkdir()
    (world / "rules.md").write_text("# 世界规则\n\n队伍人数：不超过3人。\n", encoding="utf-8")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    assert any("G6.9:limit_exceeded" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g69_world_rule_pass_with_constraints_extracted(tmp_path: Path) -> None:
    """rules.md with a constraint no chapter violates -> G6.9 PASS with count.

    Covers the no-violation path and the PASS append (g6.py:259).
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _make_chapter(project_dir, 1, "队伍人数3人。正文内容。" * 100)
    world = project_dir / "world"
    world.mkdir()
    (world / "rules.md").write_text("# 世界规则\n\n队伍人数：不超过10人。\n", encoding="utf-8")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    g69 = next((c for c in result["checks"] if c.get("id") == "G6.9"), None)
    assert g69 is not None
    assert g69["s"] == "PASS"
    assert g69["constraints_extracted"] >= 1


@pytest.mark.unit
def test_g611_missing_ending_hook_on_non_final_volume(tmp_path: Path) -> None:
    """A non-final volume whose last chapter lacks a hook marker -> G6.11:no_ending_hook.

    Covers the nested _ch_num helper and ending-hook check (g6.py:319-329)
    which only run for non-final volumes.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "novel.json").write_text('{"target_words": 5000}', encoding="utf-8")
    (project_dir / "genre-config.json").write_text(
        '{"chapter_word": {"default": 5000}}', encoding="utf-8"
    )
    ch_dir = project_dir / "chapters"
    ch_dir.mkdir()
    # chapter-002 is vol 1's last chapter and contains no hook marker.
    (ch_dir / "chapter-001.md").write_text("正文内容平淡结束。\n", encoding="utf-8")
    (ch_dir / "chapter-002.md").write_text("正文内容平淡结束。\n", encoding="utf-8")
    (ch_dir / "chapter-003.md").write_text("正文内容。\n", encoding="utf-8")
    outline = project_dir / "outline"
    outline.mkdir()
    (outline / "volume_map.md").write_text(
        "## 第一卷\nchapters 1-2\n## 第二卷\nchapters 3-3\n", encoding="utf-8"
    )
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    assert any("G6.11:no_ending_hook" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_g612_detects_sensitive_word_embedded_in_cjk(tmp_path: Path) -> None:
    r"""Sensitive word embedded mid-sentence (no spaces) -> G6.12 finds it.

    Old \w-anchored regex missed this because \w matches CJK in Python's
    Unicode mode. cjk.find_terms uses exact substring match.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    _make_chapter(project_dir, 1, "正文反对台独行径是底线内容\n")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    assert any(mf.startswith("G6.12:台独") for mf in result["must_fix"])


@pytest.mark.unit
def test_g612_dedupes_repeated_sensitive_word_per_chapter(tmp_path: Path) -> None:
    r"""A sensitive word repeated many times in one chapter yields a single
    G6.12 entry for that (term, chapter), not one per occurrence.

    Regression for the find_terms wiring: find_terms returns one TermHit per
    occurrence, so naively extending sw_found blew up the must_fix output.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    _make_chapter(project_dir, 1, ("正文反对台独行径" * 5) + "\n")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    dupe_hits = [mf for mf in result["must_fix"] if mf.startswith("G6.12:台独")]
    assert len(dupe_hits) == 1


@pytest.mark.unit
def test_g6_returns_fail_not_crash_when_deps_json_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed deps.json -> G6 returns FAIL JSON, never raises."""
    import shenbi.gates.g6 as g6_mod

    def boom(_p: object) -> dict[str, object]:
        raise json.JSONDecodeError("bad", "doc", 0)

    monkeypatch.setattr(g6_mod, "jload", boom)
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G6("long-form", str(round_dir), str(tmp_path)))
    assert result["status"] == "FAIL"
