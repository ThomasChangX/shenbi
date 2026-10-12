"""Tests for seed file parsing."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import PROJECT
from shenbi.pipeline.seed_parser import _split_key_value, parse_seed

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
        assert (
            data.novel_json["target_word_count"] == 200000
        )  # F919: 20万 adjudicated (goal-prompt/concepts 2:1)
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


class TestSplitKeyValue:
    """Unit tests for the _split_key_value helper."""

    def test_no_colon_returns_none(self):
        assert _split_key_value("just a label") is None

    def test_ascii_colon(self):
        assert _split_key_value("Genre: fantasy") == ("Genre", "fantasy")

    def test_fullwidth_colon(self):
        assert _split_key_value("类型：奇幻") == ("类型", "奇幻")

    def test_chinese_key_value_with_ascii_colon_in_value(self):
        """Regression: a fullwidth-colon key whose value contains an ASCII
        colon must split on the earliest (fullwidth) separator, not on the
        colon embedded inside the value.
        """
        item = '核心概念：主角说"你好:世界"'
        assert _split_key_value(item) == ("核心概念", '主角说"你好:世界"')

    def test_english_key_with_fullwidth_colon_in_value(self):
        """Symmetric case: ASCII-colon key whose value contains a fullwidth
        colon must split on the earliest (ASCII) separator.
        """
        item = 'Core concept: she says"你好：世界"'
        assert _split_key_value(item) == ("Core concept", 'she says"你好：世界"')


class TestTitleExtraction:
    """probe10/11 (2026-10-02): init never wrote novel.json's title — the
    seed parser has no H1 handling — so G4.novel.missing_title had only ever
    passed because worldbuilding's LLM output was allowed to (accidentally)
    overwrite the framework file with an invented title (probe9 shipped the
    model-invented 星火燎原; the seed says 星火燃穹). The framework must own
    its invariant: the title comes from the seed H1.
    """

    def test_h1_title_lands_in_novel_json(self, tmp_path):

        from shenbi.pipeline.seed_parser import parse_seed

        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 星火燃穹：位面解放战争史\n\n## 基本信息\n- 类型：架空历史\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert data.novel_json.get("title") == "星火燃穹"

    def test_h1_without_colon_uses_full_line(self, tmp_path):

        from shenbi.pipeline.seed_parser import parse_seed

        seed = tmp_path / "seed.md"
        seed.write_text("# 一本没有副标题的书\n\n## 基本信息\n", encoding="utf-8")
        data = parse_seed(seed)
        assert data.novel_json.get("title") == "一本没有副标题的书"


class TestTargetTotalChapters:
    """T3: seed「目标章节数」→ novel.json.target_total_chapters（权威覆盖）。"""

    def test_zh_key_parsed(self, tmp_path):
        from shenbi.pipeline.seed_parser import parse_seed

        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型：测试\n- 目标章节数：450\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert data.novel_json.get("target_total_chapters") == 450

    def test_zh_alt_and_inline_unit_parsed(self, tmp_path):
        from shenbi.pipeline.seed_parser import parse_seed

        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 目标总章数: 约 500 章\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert data.novel_json.get("target_total_chapters") == 500

    def test_absent_means_no_override(self, tmp_path):
        from shenbi.pipeline.seed_parser import parse_seed

        seed = tmp_path / "seed.md"
        seed.write_text("# 书\n\n## 基本信息\n- 类型：测试\n", encoding="utf-8")
        data = parse_seed(seed)
        assert "target_total_chapters" not in data.novel_json


class TestValidateSeed:
    """T2: AI-tool-edit 防错——结构校验一次性报全量问题。"""

    @pytest.fixture()
    def valid_seed_text(self) -> str:
        return (
            "# 测试书\n\n"
            "## 基本信息\n- 类型：测试\n- 目标章节数：450\n\n"
            "## 主角设定\n内容\n\n## 世界观设定\n内容\n\n"
            "## 势力/组织\n内容\n\n"
            "## 核心冲突\n- 表层冲突：A\n- 个人冲突：B\n- 深层冲突：C\n\n"
            "## 情节线\n内容\n\n## 章节大纲\n内容\n\n"
            "## 三幕结构\n内容\n\n## 叙事技巧\n- 主题：测试\n"
        )

    def test_valid_seed_passes(self, tmp_path, valid_seed_text):
        from shenbi.pipeline.seed_parser import validate_seed

        seed = tmp_path / "seed.md"
        seed.write_text(valid_seed_text, encoding="utf-8")
        assert validate_seed(seed) == []

    def test_missing_sections_all_reported(self, tmp_path, valid_seed_text):
        from shenbi.pipeline.seed_parser import validate_seed

        broken = valid_seed_text.replace("## 三幕结构\n内容\n\n", "").replace(
            "## 叙事技巧\n- 主题：测试\n", ""
        )
        seed = tmp_path / "seed.md"
        seed.write_text(broken, encoding="utf-8")
        errors = validate_seed(seed)
        assert any("三幕" in e for e in errors)
        assert any("叙事技巧" in e for e in errors)

    def test_missing_h1_reported(self, tmp_path, valid_seed_text):
        from shenbi.pipeline.seed_parser import validate_seed

        broken = valid_seed_text.replace("# 测试书\n\n", "", 1)
        seed = tmp_path / "seed.md"
        seed.write_text(broken, encoding="utf-8")
        errors = validate_seed(seed)
        assert any("一级标题" in e for e in errors)

    def test_english_headings_accepted(self, tmp_path):
        from shenbi.pipeline.seed_parser import validate_seed

        seed = tmp_path / "seed.md"
        seed.write_text(
            "# Book\n\n## Basic Info\n- Genre: test\n\n## Protagonist\nx\n\n"
            "## World Rules\nx\n\n## Forces\nx\n\n"
            "## Core Conflict\n- surface: a\n- personal: b\n- deep: c\n\n"
            "## Plot Lines\nx\n\n## Chapter Outline\nx\n\n"
            "## Three-Act Structure\nx\n\n## Narrative Techniques\n- theme: x\n",
            encoding="utf-8",
        )
        assert validate_seed(seed) == []
