"""Bespoke error-path tests for g4_worldbuilding.

worldbuilding resolves project_dir = fps[0].parent.parent, so each test
places files at <project_dir>/<sub>/<file> and passes <sub>/<file> as
fps[0] so the checker reads <project_dir>/<file>.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.worldbuilding import g4_worldbuilding


def _result(s: str) -> dict[str, Any]:
    return json.loads(s)


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    """Build a <project>/<sub>/ tree; return (project_dir, marker file).

    fps[0] lives at <project>/<sub>/<file> so fps[0].parent.parent == project_dir.
    """
    project_dir = tmp_path / "project"
    sub_dir = project_dir / "skill-output"
    sub_dir.mkdir(parents=True)
    marker = sub_dir / "out.md"
    marker.write_text("x", encoding="utf-8")
    return project_dir, marker


def _novel(project_dir: Path, **overrides: object) -> None:
    data: dict[str, object] = {
        "title": "T",
        "genre": ["x"],
        "language": "zh",
        "target_words": 100000,
    }
    data.update(overrides)
    (project_dir / "novel.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.unit
def test_fails_when_novel_json_missing_required_field(tmp_path: Path) -> None:
    """novel.json missing a required field (title) -> FAIL with G4.novel.missing_title."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir, title=None)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )

    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.novel.missing_title" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_novel_json_not_found(tmp_path: Path) -> None:
    """No novel.json at all -> FAIL with G4.novel.not_found."""
    project_dir, marker = _setup(tmp_path)

    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.novel.not_found" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_genre_config_not_found(tmp_path: Path) -> None:
    """No genre-config.json -> FAIL with G4.genre_config.not_found."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)

    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any(mf == "G4.genre_config.not_found" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_story_bible_has_too_few_sections(tmp_path: Path) -> None:
    """story_bible.md with < 4 '## ' headings -> FAIL with G4.sb.sections."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    (world / "story_bible.md").write_text(
        "# Bible\n\n## One\n\n## Two\n\n",
        encoding="utf-8",
    )

    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.sb.sections:found_2_need_4" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_story_bible_bullet_density_above_threshold(tmp_path: Path) -> None:
    """story_bible.md dominated by bullet lines (>5%) -> FAIL with G4.sb.bullet_density."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    body = (
        "# Bible\n\n## One\n- a\n- b\n- c\n\n"
        "## Two\n- d\n- e\n- f\n\n"
        "## Three\n- g\n- h\n\n"
        "## Four\n- i\n- j\n"
    )
    (world / "story_bible.md").write_text(body, encoding="utf-8")

    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "FAIL"
    assert any("G4.sb.bullet_density:" in mf for mf in result["must_fix"])


# ---------------------------------------------------------------------------
# Happy-path + remaining error branches (PR-56 coverage fill)
# ---------------------------------------------------------------------------


def _full_valid_project(tmp_path: Path) -> tuple[Path, Path]:
    """Build a project where every worldbuilding artifact is valid -> overall PASS."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    (world / "story_bible.md").write_text(
        "# Bible\n\n## 世界观\n散文式描述世界观细节内容。\n\n"
        "## 历史\n散文式描述历史背景内容。\n\n"
        "## 魔法\n散文式描述魔法体系内容。\n\n"
        "## 社会\n散文式描述社会结构内容。\n",
        encoding="utf-8",
    )
    (world / "rules.md").write_text(
        "# Rules\n\n## 规则一：守恒\n可测试标准：施法消耗灵力。\n\n"
        "## 规则二：因果\n验证条件：事件皆有原因。\n",
        encoding="utf-8",
    )
    (world / "locations.md").write_text(
        "# Loc\n\n## 地点：城\n首都。\n\n## 地点：林\n森林。\n\n## 地点：山\n山脉。\n",
        encoding="utf-8",
    )
    truth = project_dir / "truth"
    truth.mkdir()
    for tmpl in (
        "current_state.md",
        "character_matrix.md",
        "emotional_arcs.md",
        "chapter_summaries.md",
    ):
        (truth / tmpl).write_text(
            "---\ntype: data\ncategory: record\nstatus: active\n---\n# Data\n",
            encoding="utf-8",
        )
    return project_dir, marker


@pytest.mark.unit
def test_passes_when_all_worldbuilding_files_valid(tmp_path: Path) -> None:
    """A complete valid project -> overall PASS.

    Covers the success branches: story_bible PASS (g4 74), rules PASS (89-90),
    locations PASS (102-103), truth template PASS (116-124), and the trailing
    `return passed` (134).
    """
    project_dir, marker = _full_valid_project(tmp_path)
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    assert result.get("must_fix", []) == []


@pytest.mark.unit
def test_fails_when_novel_missing_target_words(tmp_path: Path) -> None:
    """novel.json with target_words absent/null -> G4.novel.missing_target_words.

    Covers g4 line 38 (the `if not tw:` branch).
    """
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir, target_words=None)
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any(mf == "G4.novel.missing_target_words" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_novel_json_invalid(tmp_path: Path) -> None:
    """Malformed novel.json -> G4.novel.invalid_json (covers g4 lines 41-42)."""
    project_dir, marker = _setup(tmp_path)
    (project_dir / "novel.json").write_text("{not valid json", encoding="utf-8")
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any(mf == "G4.novel.invalid_json" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_genre_config_invalid_json(tmp_path: Path) -> None:
    """Malformed genre-config.json -> G4.genre_config.invalid_json (covers g4 52-53)."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text("{broken", encoding="utf-8")
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any(mf == "G4.genre_config.invalid_json" for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_rules_count_out_of_range(tmp_path: Path) -> None:
    """rules.md with no valid '## 规则N' headers -> G4.rules.count (covers g4 86)."""
    project_dir, marker = _setup(tmp_path)
    _novel(project_dir)
    (project_dir / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3000}}), encoding="utf-8"
    )
    world = project_dir / "world"
    world.mkdir()
    (world / "story_bible.md").write_text(
        "# B\n\n## 一\n散文。\n\n## 二\n散文。\n\n## 三\n散文。\n\n## 四\n散文。\n",
        encoding="utf-8",
    )
    (world / "rules.md").write_text("# Rules\n\n没有规则头的内容。\n", encoding="utf-8")
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any("G4.rules.count:" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_truth_template_missing_field(tmp_path: Path) -> None:
    """A truth template missing a frontmatter field -> G4.truth.{tmpl}.missing_{field} (covers g4 123)."""
    project_dir, marker = _full_valid_project(tmp_path)
    (project_dir / "truth" / "current_state.md").write_text(
        "---\ntype: data\ncategory: record\n---\n# Data\n",
        encoding="utf-8",  # no status
    )
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any("G4.truth.current_state.md.missing_status" in mf for mf in result["must_fix"])


# ---------------------------------------------------------------------------
# Contract-vocabulary acceptance (canary escalation 2026-09-28): SKILL.md's
# own terms (铁律, bare-name location H2s) must satisfy the count checks.
# ---------------------------------------------------------------------------


def _swap_rules_locations(project_dir: Path, rules_body: str, locations_body: str) -> None:
    (project_dir / "world" / "rules.md").write_text(rules_body, encoding="utf-8")
    (project_dir / "world" / "locations.md").write_text(locations_body, encoding="utf-8")


@pytest.mark.unit
def test_passes_with_tielu_heading_rules_and_bare_name_locations(tmp_path: Path) -> None:
    """铁律-numbered rule headings + bare-name location H2s count correctly.

    This is the exact shape the canary produced (10 铁律, 5 bare-name
    locations) that the keyword-only regexes counted as 0.
    """
    project_dir, marker = _full_valid_project(tmp_path)
    _swap_rules_locations(
        project_dir,
        "# 世界铁律\n\n## 铁律一：等价支付律\n任何超常效果都必须支付。\n\n"
        "## 铁律二：自动清算律\n账册不接受指定支付物。\n",
        "# 地点图谱\n\n## 灰烬渡口\n河海贸易城邦。\n\n## 白垩塔\n议会所在。\n\n## 钟城\n教团圣地。\n",
    )
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    rules_check = next(ch for ch in result["checks"] if ch["id"] == "G4.rules")
    assert rules_check["count"] == 2
    locs_check = next(ch for ch in result["checks"] if ch["id"] == "G4.locations")
    assert locs_check["count"] == 3


@pytest.mark.unit
def test_tielu_rule_count_over_10_still_fails(tmp_path: Path) -> None:
    """铁律 headings beyond the 1-10 range still fail the count check."""
    project_dir, marker = _full_valid_project(tmp_path)
    cn = "一二三四五六七八九十"
    rules = (
        "# 世界铁律\n\n"
        + "".join(f"## 铁律{cn[i]}：律{i}\n内容。\n\n" for i in range(10))
        + "## 铁律十一：溢出\n内容。\n"
    )
    _swap_rules_locations(project_dir, rules, "# L\n\n## A\nx\n\n## B\ny\n\n## C\nz\n")
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any("G4.rules.count:11" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_bare_h2_locations_out_of_range_still_fails(tmp_path: Path) -> None:
    """Bare-name H2 fallback respects the 3-5 bound (6 sections -> count:6)."""
    project_dir, marker = _full_valid_project(tmp_path)
    locations = "# 地点图谱\n\n" + "".join(f"## 地点{i}\n描述。\n\n" for i in range(6))
    _swap_rules_locations(project_dir, "# R\n\n## 规则一：律\n内容。\n", locations)
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert any("G4.locations.count:6" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_story_bible_missing_timeline_gets_warn_not_fail(tmp_path: Path) -> None:
    """Batch #10 #18: a story_bible without the 世界史时间线 single-source
    table yields a WARN (G4.sb.timeline), not a must-fix — the section
    becomes required through the SKILL template and the foundation-review
    chronology cross-check; the gate surfaces its absence without breaking
    pre-existing compliant fixtures.
    """
    project_dir, marker = _full_valid_project(tmp_path)
    (project_dir / "world" / "story_bible.md").write_text(
        "# Bible\n\n## 世界观\n散文式描述世界观细节内容。\n\n"
        "## 历史\n散文式描述历史背景内容。\n\n"
        "## 魔法\n散文式描述魔法体系内容。\n\n"
        "## 社会\n散文式描述社会结构内容。\n",
        encoding="utf-8",
    )
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    assert result.get("must_fix", []) == []
    checks = result.get("checks", [])
    assert any(c.get("id") == "G4.sb.timeline" and c.get("s") == "WARN" for c in checks), checks


@pytest.mark.unit
def test_story_bible_with_timeline_no_warn(tmp_path: Path) -> None:
    project_dir, marker = _full_valid_project(tmp_path)
    (project_dir / "world" / "story_bible.md").write_text(
        "# Bible\n\n## 世界观\n散文式描述世界观细节内容。\n\n"
        "## 历史\n散文式描述历史背景内容。\n\n"
        "## 魔法\n散文式描述魔法体系内容。\n\n"
        "## 社会\n散文式描述社会结构内容。\n\n"
        "## 世界史时间线\n\n| 锚名 | 距今 | 事件 | 关联 |\n|---|---|---|---|\n"
        "| 净场 | 110 年前 | 教廷特使清剿 | 铁律会 |\n",
        encoding="utf-8",
    )
    result = _result(g4_worldbuilding([str(marker)], rd=str(project_dir)))
    assert result["status"] == "PASS"
    checks = result.get("checks", [])
    assert not any(c.get("id") == "G4.sb.timeline" for c in checks), checks
