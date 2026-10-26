"""Tests for seed file parsing."""

from __future__ import annotations

from typing import ClassVar

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
        assert "近世" in str(data.novel_json["era"])
        assert "穿越" in str(data.novel_json["core_concept"])
        assert (
            data.novel_json["target_word_count"] == 1980000
        )  # 2026-10-27 re-scoped: #72 平台章长带（2800-4000/default 3200）重预算 660 章/198 万字（卷均 16.5 万贴已验证卷密度）；supersedes 2026-10-15 千万字/1400 章
        assert data.novel_json["target_total_chapters"] == 660  # authoritative chapter override
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
        assert "80" in str(
            data.genre_config.get("show_tell_ratio", "")
        )  # 体感优先：75→80 (2026-10-15)


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


class TestSupportingSection:
    """spec #69 T2: 配角设定 optional section."""

    def test_supporting_section_parsed(self, tmp_path):
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n"
            "## 配角设定\n- 阿萱：女主挚友，药庐传人\n\n## 主角设定\n- 名字: 测试\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert "阿萱" in data.genesis_context["supporting"]

    def test_supporting_section_absent_defaults_empty(self, tmp_path):
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n## 主角设定\n- 名字: 测试\n",
            encoding="utf-8",
        )
        data = parse_seed(seed)
        assert data.genesis_context["supporting"] == ""


class TestRichSeedSoftBounds:
    """spec §3.4: 丰富软约束锚点——各节 < 32K、十节合计 < ~100K（测试内字面量，
    G0.9 先例 conftest.sample_seed_content；不落 tests/fixtures/）。
    """

    RICH_SECTIONS: ClassVar[dict[str, str]] = {
        "基本信息": "- 类型: 玄幻\n- 目标字数: 2000000\n- 目标章节数: 600\n",
        "主角设定": "- 测试主角 " * 200 + "\n",
        "配角设定": "- 测试配角 " * 100 + "\n",
        "世界观设定": "- 测试规则 " * 400 + "\n",
        "势力/组织": "- 测试势力 " * 200 + "\n",
        "核心冲突": "- 表层冲突: 测试\n- 个人冲突: 测试\n- 深层冲突: 测试\n",
        "情节线": "- 测试情节线 " * 200 + "\n",
        "章节大纲": "- 第1章 测试 " * 200 + "\n",
        "三幕结构": "- 第一幕 测试 " * 100 + "\n",
        "叙事技巧": "- 展示讲述比: 0.6\n",
    }

    def test_rich_seed_within_soft_bounds(self, tmp_path):
        body = "\n".join(f"## {h}\n{c}" for h, c in self.RICH_SECTIONS.items())
        seed = tmp_path / "seed.md"
        seed.write_text(f"# 丰富测试书\n\n{body}\n", encoding="utf-8")
        data = parse_seed(seed)
        fragments = {k: v for k, v in data.genesis_context.items() if v}
        assert len(fragments) == 10  # 十节全产出（含 supporting）
        for name, text in fragments.items():
            assert len(text) < 32000, name
        assert sum(len(t) for t in fragments.values()) < 100000


class TestDroppedKeyWarning:
    """Spec #69 T3: non-whitelist keys surface once via seed_key_dropped.

    structlog binds stderr (PrintLoggerFactory(sys.stderr)) -- caplog CANNOT
    capture it; capsys must (precedent:
    tests/unit/pipeline/test_dispatch_skill_write_audit.py:281-292).
    """

    @staticmethod
    def _configure() -> None:
        from shenbi.logging import configure_logging

        configure_logging()

    def test_basic_info_unknown_key_warns(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n- 灵感来源: 某剧\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        err = capsys.readouterr().err
        assert err.count("seed_key_dropped") == 1  # 一次汇总, 不逐键刷屏
        assert "灵感来源" in err

    def test_narrative_unknown_key_warns(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n"
            "## 叙事技巧\n- 展示讲述比: 0.6\n- 叙事人称: 第一人称\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        err = capsys.readouterr().err
        assert err.count("seed_key_dropped") == 1
        assert "叙事人称" in err

    def test_all_whitelisted_no_warning(self, tmp_path, capsys):
        self._configure()
        seed = tmp_path / "seed.md"
        seed.write_text(
            "# 书\n\n## 基本信息\n- 类型: 玄幻\n- 目标字数: 1000000\n\n## 叙事技巧\n- 展示讲述比: 0.6\n",
            encoding="utf-8",
        )
        parse_seed(seed)
        assert "seed_key_dropped" not in capsys.readouterr().err
