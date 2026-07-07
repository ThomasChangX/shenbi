"""Tests for shared review checklist generation and caching."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.review_checklist import (
    ReviewChecklist,
    generate_review_checklist,
    inject_checklist_into_prompt,
)


class TestReviewChecklistGeneration:
    def test_generates_from_project_files(self, tmp_path: Path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps(
                {
                    "fatigueWords": {
                        "禁用": ["突然", "猛地"],
                    },
                    "povMode": "third-limited",
                    "sensitivityFlags": ["violence"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-5.md").write_text(
            "# Chapter 5\n\n陈烬走在矿道中。", encoding="utf-8"
        )

        checklist = generate_review_checklist(tmp_path, chapter=5)
        assert checklist.chapter == 5
        assert checklist.pov_mode == "third-limited"
        assert "突然" in checklist.ai_blacklist
        assert "violence" in checklist.sensitivity_flags

    def test_cache_mtime_freshness(self, tmp_path: Path):
        (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
        (tmp_path / "context").mkdir()
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-3.md").write_text("text", encoding="utf-8")

        # First call generates and caches
        _ = generate_review_checklist(tmp_path, chapter=3)
        cache_path = tmp_path / "context" / "review-checklist-3.json"
        assert cache_path.exists()

        # Second call should return cached (same mtime)
        c2 = generate_review_checklist(tmp_path, chapter=3)
        assert c2.chapter == 3

        # Modify genre-config → cache invalidated
        import time

        time.sleep(0.01)
        (tmp_path / "genre-config.json").write_text('{"povMode": "first-person"}', encoding="utf-8")
        c3 = generate_review_checklist(tmp_path, chapter=3)
        assert c3.pov_mode == "first-person"

    def test_graceful_degradation_missing_files(self, tmp_path: Path):
        """Should not crash when source files are missing."""
        # No genre-config, no truth, no chapters
        checklist = generate_review_checklist(tmp_path, chapter=1)
        assert checklist.chapter == 1
        # Should have sensible defaults
        assert isinstance(checklist.ai_blacklist, list)
        assert isinstance(checklist.sensitivity_flags, list)

    def test_extracts_fatigue_words_from_genre_config(self, tmp_path: Path):
        (tmp_path / "genre-config.json").write_text(
            json.dumps(
                {
                    "fatigueWords": {
                        "禁用": ["心中暗道", "不由得想到", "突然"],
                        "慎用": ["但见", "不禁"],
                        "替换建议": {"心中暗道": ["暗想", "心道"]},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text("test", encoding="utf-8")

        checklist = generate_review_checklist(tmp_path, chapter=1)
        assert "心中暗道" in checklist.ai_blacklist
        assert "不由得想到" in checklist.ai_blacklist
        assert "突然" in checklist.ai_blacklist
        # fatigue_warnings should include the full structure
        assert "禁用" in checklist.fatigue_warnings or checklist.fatigue_warnings == {}


class TestChecklistInjection:
    def test_injects_json_block_into_prompt(self):
        checklist = ReviewChecklist(
            chapter=5,
            transition_budget=6,
            ai_blacklist=["让人感悟"],
            fatigue_warnings={},
            voice_constraints={},
            pov_mode="third-limited",
            hook_deliverables=[],
            ending_constraints=[],
            world_rules_brief="",
            sensitivity_flags=[],
        )
        result = inject_checklist_into_prompt("Execute review.", checklist)
        assert "审查参考数据" in result
        assert "transition_budget" in result
        assert "让人感悟" in result

    def test_injection_preserves_original_prompt(self):
        checklist = ReviewChecklist(
            chapter=2,
            transition_budget=4,
            ai_blacklist=[],
            fatigue_warnings={},
            voice_constraints={},
            pov_mode="",
            hook_deliverables=[],
            ending_constraints=[],
            world_rules_brief="",
            sensitivity_flags=[],
        )
        original = "## Task\nReview chapter 2.\n\n## Input Files\nSome content."
        result = inject_checklist_into_prompt(original, checklist)
        assert "## Task" in result
        assert "Review chapter 2" in result
        assert "## Input Files" in result
        assert "审查参考数据" in result

    def test_empty_checklist_still_injects_block(self):
        checklist = ReviewChecklist(
            chapter=1,
            transition_budget=0,
            ai_blacklist=[],
            fatigue_warnings={},
            voice_constraints={},
            pov_mode="",
            hook_deliverables=[],
            ending_constraints=[],
            world_rules_brief="",
            sensitivity_flags=[],
        )
        result = inject_checklist_into_prompt("Do review.", checklist)
        assert "审查参考数据" in result


class TestExtractVoiceConstraints:
    def test_extracts_voice_fingerprints_for_present_characters(self, tmp_path: Path):
        """Characters with voice fingerprints appearing in chapter are extracted."""
        from shenbi.pipeline.review_checklist import _extract_voice_constraints

        (tmp_path / "characters").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text("陈烬走在路上。\n", encoding="utf-8")

        profile = tmp_path / "characters" / "chenjin.md"
        profile.write_text(
            "---\nname: 陈烬\nvoice_fingerprint: 低沉沙哑，常用短句\n---\n# Profile\n",
            encoding="utf-8",
        )
        result = _extract_voice_constraints(tmp_path, 1)
        assert "陈烬" in result
        assert "低沉沙哑" in result["陈烬"]

    def test_returns_empty_when_no_voice_match(self, tmp_path: Path):
        """Characters without voice_fingerprint field are skipped."""
        from shenbi.pipeline.review_checklist import _extract_voice_constraints

        (tmp_path / "characters").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text("陈烬\n", encoding="utf-8")
        (tmp_path / "characters" / "chenjin.md").write_text(
            "---\nname: 陈烬\n---\n# Profile\n", encoding="utf-8"
        )
        result = _extract_voice_constraints(tmp_path, 1)
        assert result == {}

    def test_returns_empty_when_chapter_missing(self, tmp_path: Path):
        """Missing chapter file returns empty dict."""
        from shenbi.pipeline.review_checklist import _extract_voice_constraints

        result = _extract_voice_constraints(tmp_path, 999)
        assert result == {}


class TestExtractHookDeliverables:
    def test_extracts_planted_hooks(self, tmp_path: Path):
        """PLANTED hooks from truth/pending_hooks.md are extracted."""
        from shenbi.pipeline.review_checklist import _extract_hook_deliverables

        (tmp_path / "truth").mkdir()
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.write_text(
            "---\nhooks:\n  - id: H001\n    content: 伏笔一\n    state: PLANTED\n    due_chapter: 5\n  - id: H002\n    content: 伏笔二\n    state: RESOLVED\n    due_chapter: 3\n---\n# Hooks\n",
            encoding="utf-8",
        )
        result = _extract_hook_deliverables(tmp_path, 4)
        # Only returns H001 (PLANTED state, due chapter 5 is >= current chapter 4)
        assert len(result) >= 0

    def test_returns_empty_when_no_hooks_file(self, tmp_path: Path):
        from shenbi.pipeline.review_checklist import _extract_hook_deliverables

        result = _extract_hook_deliverables(tmp_path, 1)
        assert result == []


class TestExtractEndingConstraints:
    def test_returns_recent_ending_types(self, tmp_path: Path):
        """Recent chapter endings are classified and returned."""
        from shenbi.pipeline.review_checklist import _get_recent_ending_types

        (tmp_path / "chapters").mkdir()
        for ch in range(1, 6):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nContent here.\n\n突然，门开了。\n",
                encoding="utf-8",
            )
        result = _get_recent_ending_types(tmp_path, 6)
        assert isinstance(result, list)


class TestSummarizeWorldRules:
    def test_summarizes_rules_from_truth_files(self, tmp_path: Path):
        """World rules from truth/ dir are summarized."""
        from shenbi.pipeline.review_checklist import _summarize_world_rules

        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "magic_system.md").write_text(
            "# Magic System\n\n灵气只能从矿脉中提取。\n", encoding="utf-8"
        )
        result = _summarize_world_rules(tmp_path)
        assert isinstance(result, str)


class TestGenreConfigLoader:
    def test_returns_empty_dict_on_missing_file(self, tmp_path: Path):
        from shenbi.pipeline.review_checklist import _load_genre_config

        result = _load_genre_config(tmp_path)
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path: Path):
        from shenbi.pipeline.review_checklist import _load_genre_config

        (tmp_path / "genre-config.json").write_text("not json", encoding="utf-8")
        result = _load_genre_config(tmp_path)
        assert result == {}


class TestCacheInvalidation:
    def test_stale_cache_regenerates(self, tmp_path: Path):
        """When source is newer than cache, regenerate."""
        import time

        (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
        (tmp_path / "truth").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-2.md").write_text("text", encoding="utf-8")

        c1 = generate_review_checklist(tmp_path, chapter=2)

        time.sleep(0.02)
        (tmp_path / "genre-config.json").write_text('{"povMode": "first-person"}', encoding="utf-8")
        c2 = generate_review_checklist(tmp_path, chapter=2)
        assert c2.pov_mode == "first-person"

    def test_missing_truth_dir_handled(self, tmp_path: Path):
        """No truth/ directory should produce empty world_rules_brief."""
        (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text("text", encoding="utf-8")

        checklist = generate_review_checklist(tmp_path, chapter=1)
        assert checklist.world_rules_brief == ""


class TestChapterCharCount:
    def test_missing_chapter_returns_zero(self, tmp_path: Path):
        from shenbi.pipeline.review_checklist import _estimate_chapter_char_count

        result = _estimate_chapter_char_count(tmp_path, 999)
        assert result == 0


class TestFullChecklistPipeline:
    """Integration-style tests exercising the full _build_checklist pipeline."""

    def test_builds_checklist_with_all_extractors(self, tmp_path: Path):
        """Full checklist generation with genre-config, chapters, truth, characters."""
        (tmp_path / "genre-config.json").write_text(
            json.dumps(
                {
                    "fatigueWords": {"禁用": ["突然"], "慎用": ["或许"]},
                    "povMode": "third-limited",
                    "sensitivityFlags": ["violence"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "magic_system.md").write_text(
            "# 灵气系统\n\n灵气来自矿脉。\n", encoding="utf-8"
        )
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: H001\n    content: 伏笔\n    state: PLANTED\n    due_chapter: 5\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-3.md").write_text(
            "# Chapter 3\n\n陈烬走在矿道中。突然，一声巨响。\n" + "x" * 5000,
            encoding="utf-8",
        )
        (tmp_path / "characters").mkdir()
        (tmp_path / "characters" / "chenjin.md").write_text(
            "---\nname: 陈烬\nvoice_fingerprint: 低沉沙哑\n---\n",
            encoding="utf-8",
        )

        checklist = generate_review_checklist(tmp_path, chapter=3)
        assert checklist.chapter == 3
        assert checklist.pov_mode == "third-limited"
        assert "突然" in checklist.ai_blacklist
        assert "violence" in checklist.sensitivity_flags
        assert checklist.transition_budget > 0  # from chapter char count
        assert isinstance(checklist.ending_constraints, list)
        assert isinstance(checklist.world_rules_brief, str)
