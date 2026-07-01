"""Tests for seed file parsing."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import PROJECT
from shenbi.pipeline.seed_parser import parse_seed

FIXTURE = PROJECT / "tests" / "fixtures" / "outline-example.md"


class TestParseSeed:
    def test_parse_basic_info(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert data.novel_json["genre"] == ["fantasy", "adventure"]
        assert data.novel_json["era"] == "medieval"
        assert data.novel_json["core_concept"] == "A test novel"
        assert data.novel_json["target_word_count"] == 200000
        assert data.novel_json["ending_direction"] == "Happy ending"

    def test_parse_protagonist(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Test Hero" in data.genesis_context["protagonist"]

    def test_parse_world_rules(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Magic exists" in data.genesis_context["world_rules"]
        assert "Dragons are real" in data.genesis_context["world_rules"]

    def test_parse_core_conflict(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Kingdom at war" in data.genesis_context["surface_conflict"]
        assert "Hero seeks revenge" in data.genesis_context["personal_conflict"]
        assert "Freedom vs duty" in data.genesis_context["deep_conflict"]

    def test_parse_three_act(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "Hero discovers powers" in data.genesis_context["three_act"]

    def test_parse_narrative_techniques(self, sample_seed_content, tmp_path):
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert data.genre_config.get("show_tell_ratio") == "70/30"
        assert "courage" in str(data.genre_config.get("deep_themes", ""))

    def test_parse_does_not_set_total_chapters(self, sample_seed_content, tmp_path):
        """Seed parser must NOT set total_chapters -- that's volume-outlining's job."""
        seed_path = tmp_path / "seed.md"
        seed_path.write_text(sample_seed_content, encoding="utf-8")

        data = parse_seed(seed_path)

        assert "total_chapters" not in data.novel_json

    def test_parse_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_seed(tmp_path / "nonexistent.md")

    def test_parse_real_chinese_fixture(self):
        """Bilingual parsing of the real outline-example.md (spec section 4.1 mapping)."""
        data = parse_seed(FIXTURE)

        # 基本信息 -> novel.json
        assert "架空历史" in str(data.novel_json["genre"])
        assert "穿越" in str(data.novel_json["genre"])
        assert "中世纪" in str(data.novel_json["era"])
        assert "穿越" in str(data.novel_json["core_concept"])
        assert data.novel_json["target_word_count"] == 200000
        assert "total_chapters" not in data.novel_json

        # section -> genesis context
        assert "林烽" in data.genesis_context["protagonist"]
        assert "灵能" in data.genesis_context["world_rules"]
        assert "梅德兰" in data.genesis_context["forces"]
        assert "侵略" in data.genesis_context["surface_conflict"]
        assert "良知" in data.genesis_context["personal_conflict"]
        assert "压迫" in data.genesis_context["deep_conflict"]
        assert data.genesis_context["plot_lines"]
        assert data.genesis_context["chapter_outline"]
        assert "主角" in data.genesis_context["three_act"]

        # 叙事技巧 -> genre-config
        assert "殖民" in str(data.genre_config.get("deep_themes", ""))
        assert "75" in str(data.genre_config.get("show_tell_ratio", ""))
