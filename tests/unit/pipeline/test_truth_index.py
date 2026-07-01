"""Tests for Route A truth entity index (wave2 task1).

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 7.1.
Route A extracts named entities deterministically from truth files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.truth_index import (
    IndexEntry,
    build_index,
    extract_entities_from_plan,
    query_index,
)


@pytest.fixture
def project_with_truth(tmp_path: Path) -> Path:
    """Project with one character, one hook, and two rules."""
    p = tmp_path / "project"
    (p / "truth").mkdir(parents=True)
    (p / "truth" / "pending_hooks.md").write_text(
        "---\nhooks:\n  - id: H01\n    content: Magic sword hidden in cave\n"
        "    state: PLANTED\n    last_reinforced: 3\n    max_distance: 25\n"
        "    characters: [Hero]\n    planted_chapter: 3\n---\n# Hooks\n",
        encoding="utf-8",
    )
    (p / "characters").mkdir()
    (p / "characters" / "protagonist.md").write_text(
        "---\nname: Hero\nrole: protagonist\n---\n# Hero\nBrave warrior.",
        encoding="utf-8",
    )
    (p / "world").mkdir()
    (p / "world" / "rules.md").write_text("## R1: Magic exists\n## R2: Dragons\n", encoding="utf-8")
    return p


class TestBuildIndex:
    def test_characters_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "Hero" in idx.characters
        assert idx.characters["Hero"].category == "character"

    def test_character_uses_frontmatter_name(self, project_with_truth):
        idx = build_index(project_with_truth)
        # File basename is "protagonist.md" but the indexed key is "Hero".
        assert idx.characters["Hero"].file == "characters/protagonist.md"

    def test_character_falls_back_to_stem_when_no_frontmatter(self, tmp_path: Path):
        p = tmp_path / "project"
        (p / "characters").mkdir(parents=True)
        (p / "characters" / "nameless.md").write_text("# No frontmatter here.", encoding="utf-8")
        idx = build_index(p)
        assert "nameless" in idx.characters

    def test_hooks_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "H01" in idx.hooks
        assert idx.hooks["H01"].extra["state"] == "PLANTED"
        assert idx.hooks["H01"].extra["last_reinforced"] == 3
        assert idx.hooks["H01"].extra["max_distance"] == 25
        assert idx.hooks["H01"].extra["content_keywords"] == "Magic sword hidden in cave"

    def test_rules_indexed(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert "R1" in idx.rules
        assert idx.rules["R1"].extra["content"] == "Magic exists"
        assert "R2" in idx.rules
        assert idx.rules["R2"].extra["content"] == "Dragons"

    def test_empty_project_returns_empty_index(self, tmp_path: Path):
        idx = build_index(tmp_path / "empty")
        assert idx.characters == {}
        assert idx.hooks == {}
        assert idx.rules == {}


class TestQueryIndex:
    def test_query_known_character(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=["Hero"])
        assert any(e.entity_id == "Hero" for e in results)

    def test_query_unknown_character_empty(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert query_index(idx, characters=["Ghost"]) == []

    def test_query_known_hook(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, hooks=["H01"])
        assert len(results) == 1
        assert results[0].entity_id == "H01"

    def test_query_known_rule(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, rules=["R1", "R2"])
        assert {e.entity_id for e in results} == {"R1", "R2"}

    def test_query_mixed_and_filters_unknown(self, project_with_truth):
        idx = build_index(project_with_truth)
        results = query_index(idx, characters=["Hero", "Ghost"], hooks=["H01", "H99"])
        assert {e.entity_id for e in results} == {"Hero", "H01"}

    def test_query_with_no_kwargs_returns_empty(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert query_index(idx) == []


class TestExtractEntitiesFromPlan:
    def test_extracts_characters_by_known_name(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "Hero enters the dark cave.")
        assert found["characters"] == ["Hero"]

    def test_does_not_match_unknown_name(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "A stranger arrives.")
        assert found["characters"] == []

    def test_extracts_hook_ids(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "Resolve H01 in this chapter.")
        assert found["hooks"] == ["H01"]

    def test_hook_regex_ignores_non_id_letter_prefixes(self, project_with_truth):
        # "Hero" starts with H but is not followed by digits -> not a hook id.
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "Hero walks home.")
        assert found["hooks"] == []

    def test_extracts_rules(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "This scene uses R1 and R2.")
        assert set(found["rules"]) == {"R1", "R2"}

    def test_empty_plan_returns_all_empty(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "")
        assert found == {"characters": [], "hooks": [], "rules": []}

    def test_duplicate_hook_ids_are_deduped(self, project_with_truth):
        idx = build_index(project_with_truth)
        found = extract_entities_from_plan(idx, "Resolve H01 then pay off H01 again.")
        assert found["hooks"] == ["H01"]


class TestCJKEntityExtraction:
    """CJK text is this module's primary domain; exercise non-ASCII names.

    ``shenbi.text.find_terms`` does exact substring matching where every CJK
    character position is a valid boundary, so Chinese character names must
    round-trip cleanly through indexing and plan extraction.
    """

    @pytest.fixture
    def cjk_project(self, tmp_path: Path) -> Path:
        """A project with Chinese-named characters and a CJK hook body."""
        p = tmp_path / "project"
        (p / "truth").mkdir(parents=True)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n"
            "  - id: H01\n"
            "    content: 林晚晴在山洞中发现古剑\n"
            "    state: PLANTED\n    last_reinforced: 3\n"
            "    max_distance: 25\n---\n# 钩子\n",
            encoding="utf-8",
        )
        (p / "characters").mkdir()
        (p / "characters" / "lin_wanqing.md").write_text(
            "---\nname: 林晚晴\nrole: 主角\n---\n# 林晚晴\n勇敢的战士。",
            encoding="utf-8",
        )
        (p / "characters" / "yingxiong.md").write_text(
            "---\nname: 英雄\nrole: 配角\n---\n# 英雄\n忠诚的伙伴。",
            encoding="utf-8",
        )
        (p / "world").mkdir()
        (p / "world" / "rules.md").write_text("## R1: 魔法存在\n## R2: 龙族\n", encoding="utf-8")
        return p

    def test_cjk_character_indexed_by_chinese_name(self, cjk_project: Path):
        idx = build_index(cjk_project)
        assert "林晚晴" in idx.characters
        assert idx.characters["林晚晴"].file == "characters/lin_wanqing.md"

    def test_cjk_character_extracted_from_plan(self, cjk_project: Path):
        idx = build_index(cjk_project)
        found = extract_entities_from_plan(idx, "林晚晴走进幽暗的山洞。")
        assert "林晚晴" in found["characters"]

    def test_multiple_cjk_characters_extracted(self, cjk_project: Path):
        idx = build_index(cjk_project)
        found = extract_entities_from_plan(idx, "林晚晴与英雄并肩作战。")
        assert set(found["characters"]) == {"林晚晴", "英雄"}

    def test_cjk_hook_content_stored_and_id_extracted(self, cjk_project: Path):
        idx = build_index(cjk_project)
        assert idx.hooks["H01"].extra["content_keywords"] == "林晚晴在山洞中发现古剑"
        found = extract_entities_from_plan(idx, "本章解决H01。")
        assert found["hooks"] == ["H01"]


class TestTruthIndexSerialization:
    def test_all_known_names(self, project_with_truth):
        idx = build_index(project_with_truth)
        assert idx.all_known_names == {"Hero", "H01", "R1", "R2"}

    def test_to_json_round_trip(self, project_with_truth):
        idx = build_index(project_with_truth)
        data = json.loads(idx.to_json())
        assert "Hero" in data["characters"]
        hero = data["characters"]["Hero"]
        assert hero["category"] == "character"
        assert hero["file"] == "characters/protagonist.md"
        assert "H01" in data["hooks"]
        assert data["hooks"]["H01"]["extra"]["state"] == "PLANTED"
        assert set(data["rules"]) == {"R1", "R2"}

    def test_to_json_empty_index_is_valid_json(self, tmp_path: Path):
        idx = build_index(tmp_path / "empty")
        data = json.loads(idx.to_json())
        assert data == {"characters": {}, "hooks": {}, "rules": {}}

    def test_entry_is_dataclass(self):
        entry = IndexEntry(category="character", entity_id="X", file="f.md", ref="f.md#X")
        assert entry.extra == {}
