"""Tests for context assembly with Route A/B/C + dedup + CLI (wave2 task3).

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md §7.1-7.4.
Integrates Route A (entity index), Route B (embedding search), Route C
(fixed rule routing) with deterministic reranking and content-hash dedup.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.context_assemble import (
    BUDGET_BY_ROLE,
    DEFAULT_BUDGET,
    TOKEN_FACTOR,
    ContextPackage,
    ContextSection,
    assemble_context,
    rerank_results,
    write_context_file,
)


@pytest.fixture
def project_with_plan(tmp_path: Path) -> Path:
    """A minimal project with a chapter plan, truth files, and a character."""
    p = tmp_path / "project"
    (p / "plans").mkdir(parents=True)
    (p / "plans" / "chapter-1-plan.md").write_text(
        "## 1. 当前任务\nchapter_role: 推进/转折\nHero finds sword.\n",
        encoding="utf-8",
    )
    (p / "truth").mkdir()
    (p / "truth" / "book_spine.md").write_text("# Spine\nCore.", encoding="utf-8")
    (p / "truth" / "audit_drift.md").write_text(
        "---\ndrift_items: []\n---\n# Drift", encoding="utf-8"
    )
    (p / "style").mkdir()
    (p / "style" / "style_profile.md").write_text("# Style\nVoice.", encoding="utf-8")
    (p / "characters").mkdir()
    (p / "characters" / "protagonist.md").write_text(
        "---\nname: Hero\n---\n# Hero\nBrave.", encoding="utf-8"
    )
    return p


class TestConstants:
    def test_budget_by_role_values(self):
        assert BUDGET_BY_ROLE["高潮/兑现"] == 18000
        assert BUDGET_BY_ROLE["推进/转折"] == 12000
        assert BUDGET_BY_ROLE["过渡/铺垫"] == 8000

    def test_default_budget_is_progression(self):
        assert DEFAULT_BUDGET == 12000

    def test_token_factor_is_1_5(self):
        assert TOKEN_FACTOR == 1.5


class TestRerank:
    def test_sorts_by_weight_descending(self):
        entries = [
            {"source": "route-c:spine", "weight": 0.6, "text": "c content", "id": "c1"},
            {"source": "route-a:hero", "weight": 1.0, "text": "a content", "id": "a1"},
        ]
        ranked = rerank_results(entries)
        assert ranked[0]["weight"] == 1.0
        assert ranked[1]["weight"] == 0.6

    def test_content_hash_dedup(self):
        """Same text from different routes should dedup by content hash."""
        entries = [
            {"source": "route-a:hero", "weight": 1.0, "text": "same content", "id": "a1"},
            {"source": "route-c:hero", "weight": 0.6, "text": "same content", "id": "c1"},
        ]
        ranked = rerank_results(entries)
        assert len(ranked) == 1
        assert ranked[0]["weight"] == 1.0

    def test_different_text_not_deduped(self):
        entries = [
            {"source": "route-a:hero", "weight": 1.0, "text": "content A", "id": "a1"},
            {"source": "route-b:b1", "weight": 0.8, "text": "content B", "id": "b1"},
        ]
        ranked = rerank_results(entries)
        assert len(ranked) == 2

    def test_empty_entries_returns_empty(self):
        assert rerank_results([]) == []

    def test_stable_sort_keeps_insertion_order_for_equal_weights(self):
        entries = [
            {"source": "route-c:a", "weight": 0.6, "text": "a", "id": "a"},
            {"source": "route-c:b", "weight": 0.6, "text": "b", "id": "b"},
        ]
        ranked = rerank_results(entries)
        assert ranked[0]["id"] == "a"
        assert ranked[1]["id"] == "b"


class TestAssembleContext:
    def test_produces_package(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        assert pkg.chapter_role == "推进/转折"
        assert len(pkg.sections) > 0

    def test_route_a_finds_character(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        sources = [s.source for s in pkg.sections]
        assert any("route-a" in s for s in sources)

    def test_route_c_loads_fixed_context(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        sources = [s.source for s in pkg.sections]
        assert any("route-c" in s for s in sources)

    def test_token_estimate_uses_1_5x(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        for s in pkg.sections:
            assert s.estimated_tokens == int(len(s.text) * 1.5)

    def test_total_tokens_within_budget(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        assert pkg.total_tokens <= 12000

    def test_high_climax_budget(self, tmp_path: Path):
        p = tmp_path / "project"
        (p / "plans").mkdir(parents=True)
        (p / "plans" / "chapter-1-plan.md").write_text(
            "chapter_role: 高潮/兑现\nHero fights dragon.\n", encoding="utf-8"
        )
        (p / "characters").mkdir()
        (p / "characters" / "protagonist.md").write_text(
            "---\nname: Hero\n---\n# Hero\nBrave.", encoding="utf-8"
        )
        pkg = assemble_context(p, "plans/chapter-1-plan.md")
        assert pkg.chapter_role == "高潮/兑现"
        assert pkg.total_tokens <= 18000

    def test_unknown_role_uses_default_budget(self, tmp_path: Path):
        p = tmp_path / "project"
        (p / "plans").mkdir(parents=True)
        (p / "plans" / "chapter-1-plan.md").write_text(
            "chapter_role: 未知角色\nSome text.\n", encoding="utf-8"
        )
        pkg = assemble_context(p, "plans/chapter-1-plan.md")
        assert pkg.chapter_role == "未知角色"
        assert pkg.total_tokens <= DEFAULT_BUDGET

    def test_missing_role_uses_default_budget(self, tmp_path: Path):
        p = tmp_path / "project"
        (p / "plans").mkdir(parents=True)
        (p / "plans" / "chapter-1-plan.md").write_text(
            "Just a plan with no role.\n", encoding="utf-8"
        )
        pkg = assemble_context(p, "plans/chapter-1-plan.md")
        assert pkg.chapter_role is None
        assert pkg.total_tokens <= DEFAULT_BUDGET

    def test_route_b_degraded_flag_when_model_unavailable(self, project_with_plan):
        from shenbi.pipeline.truth_embed import is_embed_available

        if is_embed_available():
            pytest.skip("sentence_transformers installed; degradation path not testable")
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        assert pkg.route_b_degraded is True


class TestWriteContextFile:
    def test_write_creates_file(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        out = write_context_file(project_with_plan, 1, pkg)
        assert out.exists()

    def test_write_correct_path(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        out = write_context_file(project_with_plan, 1, pkg)
        assert out == project_with_plan / "context" / "chapter-1-context.md"

    def test_write_contains_content(self, project_with_plan):
        pkg = assemble_context(project_with_plan, "plans/chapter-1-plan.md")
        out = write_context_file(project_with_plan, 1, pkg)
        content = out.read_text(encoding="utf-8")
        assert "route" in content or "Spine" in content


class TestContextPackageMarkdown:
    def test_to_markdown_has_sections(self):
        pkg = ContextPackage(
            chapter_role="推进/转折",
            sections=[
                ContextSection(source="route-c:spine", priority=0.6, text="# Spine\nCore."),
            ],
        )
        md = pkg.to_markdown()
        assert "route-c:spine" in md
        assert "# Spine\nCore." in md

    def test_empty_package_markdown(self):
        pkg = ContextPackage()
        assert pkg.to_markdown() == ""


class TestRouteBIntegration:
    def test_route_b_search_works_with_stored_embeddings(self, tmp_path: Path):
        """Route B should search against stored embeddings without error.

        Stores a known embedding, then verifies assemble_context runs cleanly.
        Whether Route B activates depends on model availability; routes A+C
        must work regardless.
        """
        import struct

        p = tmp_path / "project"
        (p / "plans").mkdir(parents=True)
        (p / "plans" / "chapter-1-plan.md").write_text(
            "chapter_role: 推进/转折\nHero finds sword.\n", encoding="utf-8"
        )
        (p / "characters").mkdir()
        (p / "characters" / "protagonist.md").write_text(
            "---\nname: Hero\n---\n# Hero\nBrave.", encoding="utf-8"
        )

        from shenbi.pipeline.truth_embed import EmbeddingStore

        store = EmbeddingStore(p / "truth-embeddings.db")
        vec = struct.pack("3f", 1.0, 0.0, 0.0)
        store.upsert(
            "chunk-sword",
            "truth/chapter_summaries.md",
            "chapter_summary",
            1,
            '["Hero"]',
            "Hero finds a magic sword in the cave.",
            vec,
        )
        store.close()

        pkg = assemble_context(p, "plans/chapter-1-plan.md")
        assert len(pkg.sections) > 0
