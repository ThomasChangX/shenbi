"""Verify all Wave 4 skill modifications are consistent with the pipeline.

Each test class maps to a Wave 4 task that edited a ``SKILL.md`` (docs and/or
contract frontmatter). The tests pin two things:

1. **Contract integrity** -- the reads/writes/updates the pipeline orchestrator
   expects are present and the pre-existing contract paths were not regressed by
   the additive Wave 4 edits.
2. **Documentation** -- the behavioral section that implements the new mode is
   actually present in the skill body.

A final class, :class:`TestCrossSkillConsistency`, checks that the new contract
edges line up across skills and with the pipeline's materialization targets
(e.g. ``context/chapter-N-context.md`` is the pipeline-assembled package that
``shenbi-chapter-drafting`` reads and ``shenbi-context-composing`` curates).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[3]
SKILLS = PROJECT / "skills"


def _skill_text(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def _load_frontmatter(skill: str) -> dict[str, Any]:
    """Parse the YAML frontmatter block of a skill's ``SKILL.md``.

    ``yaml.safe_load`` strips inline ``#`` comments (e.g. the ``# for genesis
    mode`` annotations), so the returned contract paths are the bare values that
    ``shenbi-sync-contracts`` renders into the auto-generated 数据契约 block.
    """
    text = _skill_text(skill)
    parts = text.split("---", 2)
    assert len(parts) >= 3, f"{skill}/SKILL.md has no frontmatter block"
    return yaml.safe_load(parts[1]) or {}


def _contract(skill: str) -> dict[str, Any]:
    return _load_frontmatter(skill)["contract"]


class TestCharacterDesignExpand:
    """W4T1: ``--mode expand`` for volume-boundary character introduction."""

    def test_contract_unchanged(self) -> None:
        # expand mode reuses existing I/O paths; the genesis writes must remain.
        writes = _contract("shenbi-character-design")["writes"]
        assert "characters/protagonist.md" in writes
        assert "characters/relationships.md" in writes

    def test_expand_mode_section_present(self) -> None:
        text = _skill_text("shenbi-character-design")
        assert "## 扩展模式" in text
        assert "expand" in text.lower()

    def test_expand_mode_is_append_only(self) -> None:
        # the two distinguishing expand-mode rules must be documented
        text = _skill_text("shenbi-character-design")
        assert "character_design_expand" in text
        assert "追加" in text


class TestForeshadowingPlantGenesis:
    """W4T2: ``--mode genesis`` reads outline files for cross-volume hooks."""

    def test_genesis_reads_in_contract(self) -> None:
        reads = _contract("shenbi-foreshadowing-plant")["reads"]
        assert "outline/story_frame.md" in reads
        assert "outline/volume_map.md" in reads

    def test_per_chapter_reads_unchanged(self) -> None:
        reads = _contract("shenbi-foreshadowing-plant")["reads"]
        updates = _contract("shenbi-foreshadowing-plant")["updates"]
        # default per-chapter mode contract must survive the additive edit
        assert "plans/chapter-N-plan.md" in reads
        assert "truth/pending_hooks.md" in updates

    def test_genesis_mode_section_present(self) -> None:
        text = _skill_text("shenbi-foreshadowing-plant")
        assert "## 创世模式" in text
        assert "genesis" in text.lower()


class TestSnapshotManageFullProject:
    """W4T3: full-project snapshot kind with globbed truth + project files."""

    def test_full_project_reads_in_contract(self) -> None:
        reads = _contract("shenbi-snapshot-manage")["reads"]
        assert "truth/*.md" in reads
        assert "world/*.md" in reads
        assert "outline/*.md" in reads
        assert "chapters/chapter-N.md" in reads

    def test_snapshot_kind_documented(self) -> None:
        text = _skill_text("shenbi-snapshot-manage")
        assert "snapshot_kind" in text

    def test_manifest_has_checksums(self) -> None:
        text = _skill_text("shenbi-snapshot-manage")
        assert "checksums" in text.lower()


class TestChapterDraftingContextRead:
    """W4T4: chapter-drafting reads the pipeline-assembled context package."""

    def test_context_in_reads(self) -> None:
        reads = _contract("shenbi-chapter-drafting")["reads"]
        assert any("context/chapter-N-context.md" in r for r in reads)

    def test_pipeline_integration_note_present(self) -> None:
        text = _skill_text("shenbi-chapter-drafting")
        assert "context/chapter-N-context.md" in text
        assert "pipeline-context-assemble" in text


class TestDriftGuidanceWindow:
    """W4T5: bounded 12-chapter rolling window for ``audit_drift.md``."""

    def test_rolling_window_documented(self) -> None:
        text = _skill_text("shenbi-drift-guidance")
        assert "滚动窗口" in text
        assert "12" in text

    def test_archive_path_documented(self) -> None:
        # entries beyond the window roll into the archive, keeping Route C bounded
        text = _skill_text("shenbi-drift-guidance")
        assert "audit_drift_archive.md" in text


class TestStyleLearningBootstrap:
    """W4T6: seed-fingerprint bootstrap mode when no chapter corpus exists."""

    def test_bootstrap_reads_in_contract(self) -> None:
        reads = _contract("shenbi-style-learning")["reads"]
        assert "novel.json" in reads
        assert "genre-config.json" in reads

    def test_normal_mode_reads_unchanged(self) -> None:
        reads = _contract("shenbi-style-learning")["reads"]
        writes = _contract("shenbi-style-learning")["writes"]
        assert "chapters/*.md" in reads
        assert "import/source/*.txt" in reads
        assert "style/style_profile.md" in writes

    def test_bootstrap_mode_documented(self) -> None:
        text = _skill_text("shenbi-style-learning")
        assert "bootstrap" in text.lower()
        # the profile carries an explicit bootstrap flag, not just the word
        assert "bootstrap: true" in text.lower()


class TestContextComposingPipelineMode:
    """W4T6b: pipeline-mode curation of the pre-assembled context package."""

    def test_pipeline_integration_section_present(self) -> None:
        text = _skill_text("shenbi-context-composing")
        assert "## Pipeline 集成模式" in text

    def test_reads_pre_assembled_package(self) -> None:
        text = _skill_text("shenbi-context-composing")
        assert "context/chapter-N-context.md" in text
        assert "pipeline-context-assemble" in text

    def test_contract_is_artifact_with_decisions_write(self) -> None:
        # Task 8: context-composing migrated from ephemeral to artifact kind.
        # It now writes a durable decisions sidecar (context/chapter-N-context-decisions.json)
        # so downstream skills can read the composed decisions.
        contract = _contract("shenbi-context-composing")
        assert contract["kind"] == "artifact"
        assert "context/chapter-N-context-decisions.json" in contract["writes"]


class TestMemoryDistillDensityTrigger:
    """W4T6c: density-driven early-trigger thresholds for arc distillation."""

    def test_density_trigger_section_present(self) -> None:
        text = _skill_text("shenbi-memory-distill")
        assert "密度驱动触发" in text

    @pytest.mark.parametrize(
        ("needle", "label"),
        [
            ("> 60", "state-settling changes"),
            ("> 15", "pending_hooks additions"),
            ("> 20", "character_matrix changes"),
        ],
    )
    def test_density_thresholds_documented(self, needle: str, label: str) -> None:
        text = _skill_text("shenbi-memory-distill")
        assert needle in text, f"missing {label} threshold ({needle!r})"


class TestCrossSkillConsistency:
    """The Wave 4 contract edges must line up across skills and with the
    pipeline's own materialization targets.
    """

    CONTEXT_PACKAGE = "context/chapter-N-context.md"

    def test_context_package_consumers_agree(self) -> None:
        # the pipeline materializes context/chapter-N-context.md (chapter_loop
        # output_path); chapter-drafting reads it, context-composing curates it.
        drafting = _contract("shenbi-chapter-drafting")["reads"]
        composing_text = _skill_text("shenbi-context-composing")
        assert any(self.CONTEXT_PACKAGE in r for r in drafting)
        assert self.CONTEXT_PACKAGE in composing_text

    def test_foreshadowing_genesis_reads_are_outline_outputs(self) -> None:
        # the genesis-mode reads must be real outline outputs with producers
        index = _truth_index()
        for path in ("outline/story_frame.md", "outline/volume_map.md"):
            entry = index.get(path)
            assert entry is not None, f"{path} missing from truth-files index"
            producers = entry.get("writes", []) + entry.get("updates", [])
            assert "shenbi-foreshadowing-plant" in entry.get("reads", [])
            assert producers, f"{path} has no producer declared"

    def test_style_bootstrap_reads_are_pipeline_configs(self) -> None:
        # novel.json + genre-config.json must exist in the truth index and list
        # style-learning as a reader
        index = _truth_index()
        for path in ("novel.json", "genre-config.json"):
            entry = index.get(path)
            assert entry is not None, f"{path} missing from truth-files index"
            assert "shenbi-style-learning" in entry.get("reads", [])


def _truth_index() -> dict[str, Any]:
    import json

    path = PROJECT / "docs" / "framework" / "truth-files.index.json"
    return json.loads(path.read_text(encoding="utf-8"))
