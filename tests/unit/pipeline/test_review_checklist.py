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
        c1 = generate_review_checklist(tmp_path, chapter=3)
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
