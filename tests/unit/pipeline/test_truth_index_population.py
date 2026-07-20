"""Population tests for truth_index — verify the parser extracts entities from
the formats actually produced by the skills (Chinese-ordinal rules, P0-N hooks).

Spec: 2026-07-19 semantic-index-population-and-parser-coherence-design §3.1/§3.2.
These are ADDITIVE: the legacy H01 / R1 formats in test_truth_index.py must
still pass.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.truth_index import build_index


def _make_project(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    (p / "world").mkdir(parents=True)
    (p / "truth").mkdir(parents=True)
    return p


class TestChineseOrdinalRules:
    def test_extracts_chinese_ordinal_rules(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "# 世界铁律\n\n"
            "## 规则一：灵能总量守恒\n宇宙间灵能的总量是有限的。\n\n"
            "## 规则二：知识即力量上限\n一个个体能调用的灵能上限受限。\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.rules) == 2, (
            f"expected 2 Chinese-ordinal rules, got {len(idx.rules)} (keys={list(idx.rules)})"
        )
        # The ID captured is the ordinal (一 / 二).
        assert "一" in idx.rules
        assert "二" in idx.rules
        assert "守恒" in str(idx.rules["一"].extra["content"])

    def test_numeric_rules_still_work(self, tmp_path):
        """Legacy R1 / 1: format — must not regress (existing testTruthIndex)."""
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "## R1: Magic exists\n## R2: Dragons\n", encoding="utf-8"
        )
        idx = build_index(p)
        assert set(idx.rules) == {"R1", "R2"}

    def test_mixed_numeric_and_chinese_ordinals(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text("## 规则一：守恒\n## R2: Dragons\n", encoding="utf-8")
        idx = build_index(p)
        assert len(idx.rules) == 2


class TestDualSourceHooks:
    def test_body_only_hooks_indexed_when_frontmatter_absent(self, tmp_path):
        """Production state: frontmatter has no `hooks:` list, hooks live in
        the body as ``### P0-N ...`` headings.
        """
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\n"
            "title: 伏笔追踪\n"
            "project: 星火燃穹\n"
            "last_chapter: 56\n"
            "---\n"
            "# 伏笔追踪\n\n"
            "## 第56章伏笔呈现\n\n"
            "### P0-4 TRIGGER 证据\n安静在阈附近完整段落。\n\n"
            "### P0-9 偏移周日格式\n偏移段未从周日格式对照。\n\n"
            "回访 P0-14 与 P0-15 两条伏笔。\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.hooks) >= 4, (
            f"expected >=4 body hooks, got {len(idx.hooks)} (keys={sorted(idx.hooks)})"
        )
        assert "P0-4" in idx.hooks
        assert "P0-9" in idx.hooks
        assert "P0-14" in idx.hooks

    def test_frontmatter_hooks_remain_authoritative(self, tmp_path):
        """When the frontmatter `hooks:` list IS present, those entries keep
        their richer extra payload; body hooks only fill gaps.
        """
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\n"
            "hooks:\n"
            "  - id: H01\n"
            "    content: Magic sword\n"
            "    state: PLANTED\n"
            "    last_reinforced: 3\n"
            "    max_distance: 25\n"
            "---\n"
            "# Hooks\n\n"
            "### H01 the sword\n### H02 new from body\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        # H01 came from frontmatter — keeps its payload.
        assert idx.hooks["H01"].extra.get("state") == "PLANTED"
        # H02 came from body — minimal entry.
        assert "H02" in idx.hooks

    def test_no_duplicate_when_id_in_both_sources(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: P0-4\n    content: fm\n---\n### P0-4 body mention\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.hooks) == 1
        # Frontmatter content wins.
        assert idx.hooks["P0-4"].extra.get("content_keywords") == "fm"


class TestHookIdRegex:
    def test_p0_hook_ids_matched_in_plan(self, tmp_path):
        """extract_entities_from_plan must recognise P0-N production IDs."""
        from shenbi.pipeline.truth_index import extract_entities_from_plan

        p = _make_project(tmp_path)
        (p / "truth" / "pending_hooks.md").write_text(
            "---\nhooks:\n  - id: P0-4\n    content: quiet structure\n---\n# Hooks\n",
            encoding="utf-8",
        )
        idx = build_index(p)
        assert "P0-4" in idx.hooks
        plan = "本章回访 P0-4 与 P0-9 两条伏笔。"
        hits = extract_entities_from_plan(idx, plan)
        assert "P0-4" in hits["hooks"]


class TestPopulationAssertion:
    def test_warns_when_rules_file_has_content_but_index_empty(self, tmp_path):
        """A rules.md with Chinese-ordinal headings that the OLD regex would
        miss must NOT silently produce an empty index. After the Task 1 fix
        this file indexes fine; to test the WARNING path we feed a format no
        regex matches (``### not-a-rule``).
        """
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text(
            "# Rules\n\n### not-a-rule-heading\n" + "x" * 200,
            encoding="utf-8",
        )
        idx = build_index(p)
        assert len(idx.rules) == 0
        # Verify via the module-level logger directly: the warning must be
        # emitted when a source file has content but the index bucket is empty.
        # We patch log.warning instead of using capsys because
        # configure_logging() binds structlog to a specific file descriptor
        # at import time, and capsys cannot reliably capture the output
        # across test-ordering variations (see test_cli.py line 6-9).
        from unittest.mock import patch

        import shenbi.pipeline.truth_index as ti_mod

        with patch.object(ti_mod.log, "warning", wraps=ti_mod.log.warning) as mock_warn:
            build_index(p)
            assert mock_warn.called
            call_args = [c[0][0] if c[0] else "" for c in mock_warn.call_args_list]
            assert any("truth_index_empty_rules" in str(a) for a in call_args)

    def test_no_warning_when_index_populated(self, tmp_path):
        p = _make_project(tmp_path)
        (p / "world" / "rules.md").write_text("## 规则一：守恒\n" + "正文。" * 50, encoding="utf-8")
        idx = build_index(p)
        assert len(idx.rules) == 1
        # Patch log.warning to verify it is NOT called when the index is
        # successfully populated.
        from unittest.mock import patch

        import shenbi.pipeline.truth_index as ti_mod

        with patch.object(ti_mod.log, "warning", wraps=ti_mod.log.warning) as mock_warn:
            build_index(p)
            call_args = [c[0][0] if c[0] else "" for c in mock_warn.call_args_list]
            assert not any("truth_index_empty_rules" in str(a) for a in call_args)

    def test_no_warning_when_source_file_absent(self, tmp_path):
        """Early-stage project with no rules.md yet — must not warn."""
        p = _make_project(tmp_path)
        # Patch log.warning to verify it is NOT called when the source file
        # is absent.
        from unittest.mock import patch

        import shenbi.pipeline.truth_index as ti_mod

        with patch.object(ti_mod.log, "warning", wraps=ti_mod.log.warning) as mock_warn:
            build_index(p)
            call_args = [c[0][0] if c[0] else "" for c in mock_warn.call_args_list]
            assert not any("truth_index_empty_rules" in str(a) for a in call_args)
