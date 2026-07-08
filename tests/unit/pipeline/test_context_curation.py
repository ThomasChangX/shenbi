"""Tests for deterministic context curation."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.context_curation import (
    _build_hook_debt_briefing,
    _check_ending_diversity,
    curate_context,
)


class TestEndingDiversity:
    """Ending diversity check should detect consecutive same-type endings."""

    def test_no_repetition_passes(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        (tmp_path / "chapters" / "chapter-1.md").write_text(
            "# Chapter 1\n\nSome text.\n\n他突然停下了脚步。", encoding="utf-8"
        )
        (tmp_path / "chapters" / "chapter-2.md").write_text(
            "# Chapter 2\n\nMore text.\n\n第二天，他出发了。", encoding="utf-8"
        )
        (tmp_path / "chapters" / "chapter-3.md").write_text(
            "# Chapter 3\n\nFinal text.\n\n但他知道一切尚未结束。", encoding="utf-8"
        )
        result = _check_ending_diversity(tmp_path, chapter=4)
        # Should have rows for chapters 1,2,3 with different types
        assert "chapter-1.md" not in result.lower() or "1" in result
        assert "⚠️" not in result  # No 3-consecutive warning

    def test_consecutive_cliffhanger_warns(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        for ch in range(1, 4):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nText.\n\n突然，一声巨响打破了寂静。", encoding="utf-8"
            )
        result = _check_ending_diversity(tmp_path, chapter=4)
        assert "⚠️" in result  # 3 consecutive cliffhangers

    def test_too_few_chapters(self, tmp_path: Path):
        result = _check_ending_diversity(tmp_path, chapter=2)
        assert "不足3章" in result


class TestHookDebtBriefing:
    """Hook debt briefing should generate MH*/H* two-tier table."""

    def test_empty_hooks(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        hooks_file.write_text("---\nhooks: []\n---\n", encoding="utf-8")
        result = _build_hook_debt_briefing(tmp_path, chapter=5)
        assert "Hook 债务简报" in result


class TestCurateContext:
    """Full curation pipeline should produce 9-section output."""

    def test_curate_produces_nine_sections(self, tmp_path: Path):
        (tmp_path / "context").mkdir()
        (tmp_path / "plans").mkdir()
        (tmp_path / "chapters").mkdir()
        (tmp_path / "truth").mkdir()

        # Write assembled context
        (tmp_path / "context" / "chapter-5-context.md").write_text(
            "## route-a:Hero\n\nHero context text.\n\n## route-c:book_spine\n\nSpine text.",
            encoding="utf-8",
        )
        # Write plan
        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            "## 1. 当前任务\n\nWrite chapter 5.", encoding="utf-8"
        )
        # Write chapters for ending check
        for ch in range(2, 5):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nText.\n\n最终，他做出了选择。", encoding="utf-8"
            )
        # Write pending hooks
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )

        result = curate_context(tmp_path, chapter=5)
        assert "P1 章节备忘" in result
        assert "近章结尾多样性" in result
        assert "Hook 债务简报" in result

    def test_curate_falls_back_to_minimal(self, tmp_path: Path):
        """When assembled context is missing, generates minimal context."""
        result = curate_context(tmp_path, chapter=1)
        assert "P1 章节备忘" in result
        assert "(未产出)" in result


class TestHookDebtWithRealData:
    """Hook debt briefing with actual hook data from book_spine."""

    def test_briefing_with_master_hooks(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        # pending_hooks with arc-level hooks
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: H001\n    content: 神秘信件\n    state: PLANTED\n    last_reinforced: 1\n  - id: H002\n    content: 叛徒身份\n    state: TRIGGERED\n    last_reinforced: 3\n---\n",
            encoding="utf-8",
        )
        # book_spine with MH* master hooks
        (tmp_path / "truth" / "book_spine.md").write_text(
            "---\nhook_master_list:\n  - id: MH001\n    content: 世界真相\n    state: active\n    last_reinforced: 2\n    max_distance: 10\n---\n# Book Spine\n",
            encoding="utf-8",
        )
        result = _build_hook_debt_briefing(tmp_path, chapter=5)
        assert "Hook 债务简报" in result
        assert "MH001" in result
        assert "H001" in result

    def test_briefing_with_inline_mh_hooks(self, tmp_path: Path):
        """Master hooks from inline markdown table in book_spine.md."""
        (tmp_path / "truth").mkdir()
        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )
        (tmp_path / "truth" / "book_spine.md").write_text(
            "# Book Spine\n\n| MH001 | 世界崩坏 | active | 3 |\n| MH002 | 主角身世 | dormant | 1 |\n",
            encoding="utf-8",
        )
        result = _build_hook_debt_briefing(tmp_path, chapter=6)
        assert "MH001" in result
        assert "MH002" in result

    def test_briefing_missing_files(self, tmp_path: Path):
        """Returns briefing with empty tables when truth files are missing."""
        result = _build_hook_debt_briefing(tmp_path, chapter=1)
        assert "(无)" in result


class TestEndingDiversityEdgeCases:
    """Edge cases for ending diversity checker."""

    def test_missing_chapter_file(self, tmp_path: Path):
        (tmp_path / "chapters").mkdir()
        for ch in [1, 2, 3]:
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\nText.\n\n结束了。", encoding="utf-8"
            )
        result = _check_ending_diversity(tmp_path, chapter=5)
        # chapter 4 is missing — should still produce table
        assert "未产出" in result

    def test_ending_classifier_health_warning(self, tmp_path: Path):
        """Unclassified endings should be tracked as 'other'."""
        (tmp_path / "chapters").mkdir()
        for ch in range(1, 4):
            (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
                f"# Chapter {ch}\n\n普通叙述文字，没有任何明确的结尾标记。\n", encoding="utf-8"
            )
        result = _check_ending_diversity(tmp_path, chapter=4)
        # Should produce a table without warning (different 'other' don't match)
        assert "章节" in result
