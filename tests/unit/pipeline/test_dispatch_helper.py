"""Tests for dispatch helper (G3/G4 + write-audit integration).

Wave 3 Task 1: dispatch wrapper that reuses the existing dispatcher CLI
(which runs G1+G2 + write-overreach audit) and adds G3/G4 gate calls.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shenbi.pipeline.dispatch_helper import (
    DispatchResult,
    _validate_json_output,
    dispatch_skill,
    requires_independent,
    run_gate_g3,
    run_gate_g4,
)

PATCH = "shenbi.pipeline.dispatch_helper.subprocess.run"
IDE_CLI_PATCH = "shenbi.pipeline.dispatch_helper._find_ide_cli"


class TestDispatchSkill:
    @patch(PATCH)
    def test_calls_subprocess(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert isinstance(result, DispatchResult)

    @patch(PATCH)
    def test_failure_returns_error(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert result.success is False

    @patch(PATCH)
    def test_success_is_true(self, mock_run, tmp_path):
        # Valid JSON required since _validate_json_output runs on .json outputs
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt")
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == "{}"

    @patch(PATCH)
    def test_timeout_returns_error(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=1)
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt", timeout=1)
        assert result.success is False
        assert result.returncode == -1

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_round_dir_override(self, mock_run, _mock_ide, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        round_dir = tmp_path / "round-001"
        round_dir.mkdir()
        dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt", round_dir=round_dir)
        cmd = mock_run.call_args[0][0]
        assert str(round_dir) in cmd

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_passes_prompt_to_cli(self, mock_run, _mock_ide, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        dispatch_skill("shenbi-worldbuilding", tmp_path, "do the thing")
        cmd = mock_run.call_args[0][0]
        assert "do the thing" in cmd


class TestRequiresIndependent:
    def test_resonance_is_independent(self):
        assert requires_independent("shenbi-review-resonance") is True

    def test_worldbuilding_not_independent(self):
        assert requires_independent("shenbi-worldbuilding") is False

    def test_unknown_skill_returns_false(self):
        assert requires_independent("shenbi-does-not-exist-xyz") is False


class TestRunGateG4:
    @patch(PATCH)
    def test_parses_json_output(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"status": "PASS"}), stderr=""
        )
        result = run_gate_g4("shenbi-worldbuilding", ["world/story_bible.md"], tmp_path)
        assert result == {"status": "PASS"}

    @patch(PATCH)
    def test_invalid_json_returns_fail(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="e")
        result = run_gate_g4("shenbi-worldbuilding", ["world/story_bible.md"], tmp_path)
        assert result["status"] == "FAIL"

    @patch(PATCH)
    def test_builds_comma_separated_file_arg(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"status": "PASS"}), stderr=""
        )
        run_gate_g4(
            "shenbi-worldbuilding",
            ["world/story_bible.md", "world/rules.md"],
            tmp_path,
        )
        cmd = mock_run.call_args[0][0]
        assert "world/story_bible.md,world/rules.md" in cmd


class TestRunGateG3:
    @patch(PATCH)
    def test_parses_json_output(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"status": "PASS"}), stderr=""
        )
        result = run_gate_g3("shenbi-review-resonance", tmp_path)
        assert result == {"status": "PASS"}

    @patch(PATCH)
    def test_invalid_json_returns_fail(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="e")
        result = run_gate_g3("shenbi-review-resonance", tmp_path)
        assert result["status"] == "FAIL"

    @patch(PATCH)
    def test_timeout_returns_fail(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=1)
        result = run_gate_g3("shenbi-review-resonance", tmp_path)
        assert result["status"] == "FAIL"

    @patch(PATCH)
    def test_passes_generative_test_type(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"status": "PASS"}), stderr=""
        )
        run_gate_g3("shenbi-review-resonance", tmp_path)
        cmd = mock_run.call_args[0][0]
        assert "generative" in cmd


class TestOptionalReads:
    """Tests for the OPTIONAL_READS dict and env-var integration."""

    def test_optional_reads_has_context_composing(self):
        from shenbi.pipeline.dispatch_helper import OPTIONAL_READS

        assert "shenbi-context-composing" in OPTIONAL_READS

    def test_optional_reads_has_drift_guidance(self):
        from shenbi.pipeline.dispatch_helper import OPTIONAL_READS

        assert "shenbi-drift-guidance" in OPTIONAL_READS

    def test_optional_reads_globs(self):
        from shenbi.pipeline.dispatch_helper import OPTIONAL_READS

        patterns = OPTIONAL_READS["shenbi-context-composing"]
        assert "arc-*.md" in patterns  # glob pattern, not literal filename
        assert "volume_summaries.md" in patterns

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_dispatch_with_known_skill_sets_env(self, mock_run, _mock_ide, tmp_path):
        """Known skill with optional reads sets SHENBI_G1_SKIP_READS."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        dispatch_skill("shenbi-context-composing", tmp_path, "prompt")
        env = mock_run.call_args[1].get("env", {})
        skip = env.get("SHENBI_G1_SKIP_READS", "")
        assert "arc-*.md" in skip
        assert "volume_summaries.md" in skip

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_dispatch_with_unknown_skill_no_env(self, mock_run, _mock_ide, tmp_path):
        """Unknown skill without optional reads does not set the env var."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt")
        env = mock_run.call_args[1].get("env", {})
        assert "SHENBI_G1_SKIP_READS" not in env

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_skip_reads_merges_with_optional(self, mock_run, _mock_ide, tmp_path):
        """Explicit skip_reads merges with OPTIONAL_READS."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        dispatch_skill(
            "shenbi-context-composing",
            tmp_path,
            "prompt",
            skip_reads=["extra.md"],
        )
        env = mock_run.call_args[1].get("env", {})
        skip = env.get("SHENBI_G1_SKIP_READS", "")
        assert "extra.md" in skip
        assert "arc-*.md" in skip  # from OPTIONAL_READS

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_skip_reads_with_unknown_skill(self, mock_run, _mock_ide, tmp_path):
        """Explicit skip_reads work even without OPTIONAL_READS entry."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt", skip_reads=["temp.md"])
        env = mock_run.call_args[1].get("env", {})
        skip = env.get("SHENBI_G1_SKIP_READS", "")
        assert "temp.md" in skip

    @patch(IDE_CLI_PATCH, return_value=None)  # force legacy CLI path
    @patch(PATCH)
    def test_subprocess_uses_copied_env(self, mock_run, _mock_ide, tmp_path):
        """Subprocess gets a modified env copy, not os.environ directly."""
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        dispatch_skill("shenbi-context-composing", tmp_path, "prompt")
        env = mock_run.call_args[1].get("env", {})
        assert env is not None
        assert env.get("SHENBI_G1_SKIP_READS", "") != ""


class TestMultiFileOutputFormat:
    """M6: when contract has multiple writes, prompt reminds about schema."""

    def test_multi_file_prompt_includes_schema_reminder(self, tmp_path, monkeypatch):
        from shenbi.contracts import OutputKind
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        # Mock contract with 2 writes (chapter.md + decisions.json)
        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["chapters/chapter-1.md", "chapters/chapter-1-decisions.json"],
            "updates": [],
            "read_fields": {},
        }
        # load_contract is imported locally inside _build_skill_prompt from
        # shenbi.contracts.legacy, so patch it there.
        monkeypatch.setattr(
            "shenbi.contracts.legacy.load_contract",
            lambda s: mock_contract,
        )

        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
        )

        assert len(output_paths) == 2
        assert "shenbi-decisions-v1" in user_prompt
        assert "decisions-schema.md" in user_prompt

    def test_single_file_prompt_omits_schema_reminder(self, tmp_path, monkeypatch):
        """Single-write contracts should NOT include the schema reminder."""
        from shenbi.contracts import OutputKind
        from shenbi.pipeline.dispatch_helper import _build_skill_prompt

        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["chapters/chapter-1.md"],
            "updates": [],
            "read_fields": {},
        }
        monkeypatch.setattr(
            "shenbi.contracts.legacy.load_contract",
            lambda s: mock_contract,
        )

        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
        )

        assert len(output_paths) == 1
        assert "shenbi-decisions-v1" not in user_prompt


class TestTruthTemplates:
    """D21: truth templates derive H2 headings from consumer-declared fields."""

    def test_seeds_all_four_files(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        truth = tmp_path / "truth"
        for name in (
            "current_state.md",
            "character_matrix.md",
            "emotional_arcs.md",
            "chapter_summaries.md",
        ):
            assert (truth / name).exists()

    def test_current_state_has_declared_h2_stubs(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        body = (tmp_path / "truth" / "current_state.md").read_text(encoding="utf-8")
        # chapter-planning/review-continuity declare these 3 fields.
        assert "## 主角状态" in body
        assert "## 当前世界局势" in body
        assert "## 活跃线索" in body
        assert "# Current State" in body

    def test_character_matrix_template_created(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        body = (tmp_path / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        # The template is created with frontmatter and H1; no H2 stubs are
        # seeded since no consumer skill declares fields for this file
        # (character_matrix.md is a slug-based table, not section-based).
        assert "update_mode: replace" in body
        assert "# Character Matrix" in body

    def test_chapter_summaries_has_declared_h2(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        body = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        assert "## 已完成章节" in body

    def test_yaml_frontmatter_present(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        body = (tmp_path / "truth" / "current_state.md").read_text(encoding="utf-8")
        assert body.startswith("---\n")
        assert "update_mode: replace" in body

    def test_does_not_overwrite_existing_file(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        truth = tmp_path / "truth"
        truth.mkdir(parents=True)
        pre_existing = "PRESERVED CONTENT"
        (truth / "current_state.md").write_text(pre_existing, encoding="utf-8")
        _init_truth_templates(tmp_path)
        assert (truth / "current_state.md").read_text(encoding="utf-8") == pre_existing

    def test_template_satisfies_check_fields_exist(self, tmp_path):
        """D21 canary: a freshly-seeded template produces no G1 field WARNs."""
        from shenbi.gates.g1 import check_fields_exist
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        inputs = [str(tmp_path / "truth" / "current_state.md")]
        # Key must be str(fp) (absolute path), matching check_fields_exist's
        # lookup convention (g1.py:104); a relative key matches neither fp nor
        # Path(fp).name, making the canary vacuously pass.
        fields_map = {
            str(tmp_path / "truth" / "current_state.md"): [
                "主角状态",
                "当前世界局势",
                "活跃线索",
            ]
        }
        warnings = check_fields_exist("shenbi-chapter-planning", inputs, fields_map)
        assert warnings == []


# ---------------------------------------------------------------------------
# JSON validation + raw_decode() recovery tests (Plan 02 Task 1)
# ---------------------------------------------------------------------------


class TestValidateJsonOutput:
    """Tests for _validate_json_output (pre-write JSON validation with recovery).

    The dominant corruption pattern (verified by filesystem audit) is a valid
    JSON object followed by trailing markdown — NOT multi-JSON concatenation.
    """

    def test_validate_json_passes_clean_json(self):
        """Clean JSON passes validation unchanged."""
        content = json.dumps({"key": "value", "number": 42}, ensure_ascii=False)
        result = _validate_json_output(content, Path("test.json"))
        assert json.loads(result) == {"key": "value", "number": 42}

    def test_validate_json_truncates_trailing_markdown(self):
        """Dominant pattern: valid JSON + trailing markdown -> truncate to first object."""
        content = '{"key": "value"}\n\n---\n**G4 failure summary:**\n- Fixed X\n'
        result = _validate_json_output(content, Path("test.json"))
        parsed = json.loads(result)
        assert parsed == {"key": "value"}
        assert "G4 failure summary" not in result

    def test_validate_json_recovers_decisions_with_complete_schema(self):
        """A shenbi-decisions-v1 object + trailing markdown passes schema + recovers."""
        valid_decisions = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-drafting",
            "chapter": 5,
            "selections": [],
            "adjustments": [],
            "produced_at": "2026-07-19T00:00:00+00:00",
        }
        content = json.dumps(valid_decisions, ensure_ascii=False) + (
            "\n\n---\n\n**两项 G4 失败修复摘要：**\n1. 修正转折词。\n"
        )
        result = _validate_json_output(content, Path("chapter-5-decisions.json"))
        parsed = json.loads(result)
        assert parsed["$schema"] == "shenbi-decisions-v1"
        assert parsed["chapter"] == 5
        assert "G4 失败修复摘要" not in result

    def test_validate_json_recovers_revision_decisions_adjustments(self):
        """A revision decisions object with non-empty adjustments recovers."""
        valid_rev = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {
                    "issue_id": "resonance.sentiment",
                    "severity": "high",
                    "handling": "explicit_callout",
                    "rationale": "Dialogue lacked emotional grounding in scene.",
                }
            ],
            "produced_at": "2026-07-19T00:00:00+00:00",
        }
        content = json.dumps(valid_rev, ensure_ascii=False) + "\n\nSummary text."
        result = _validate_json_output(content, Path("chapter-5-revision-decisions.json"))
        parsed = json.loads(result)
        assert parsed["adjustments"][0]["issue_id"] == "resonance.sentiment"

    def test_validate_json_raises_when_recovered_object_missing_required_fields(self):
        """Recovery tightened: if the recovered object fails DecisionsDoc schema
        (missing required fields), raise rather than persisting an incomplete file.
        """
        # Object with trailing markdown but MISSING required fields (no skill/chapter/...)
        incomplete = {"$schema": "shenbi-decisions-v1", "note": "partial"}
        content = json.dumps(incomplete) + "\n\n---\ntail markdown"
        with pytest.raises(ValueError, match=r"schema|incomplete|unrecoverable"):
            _validate_json_output(content, Path("chapter-5-decisions.json"))

    def test_validate_json_handles_multiple_concatenated_json_defensively(self):
        """Defensive (not the dominant pattern): multiple concatenated JSON objects
        extracts only the first, then validates it against schema. If the first
        object is not a decisions doc, the non-decisions branch returns it as-is.
        """
        content = '{"a":1}\n{"b":2}\n{"c":3}'
        result = _validate_json_output(content, Path("test.json"))
        parsed = json.loads(result)
        assert parsed == {"a": 1}
        assert "b" not in result

    def test_validate_json_raises_on_unrecoverable(self):
        """Completely invalid JSON (no recoverable object) raises ValueError."""
        content = "not json at all"
        with pytest.raises(ValueError, match="unrecoverable"):
            _validate_json_output(content, Path("test.json"))

    def test_validate_json_skips_non_json_files(self):
        """Non-JSON files are returned unchanged."""
        content = "# Chapter 5\n\n## Section 1\nProse content here."
        result = _validate_json_output(content, Path("chapter-5.md"))
        assert result == content


# ---------------------------------------------------------------------------
# Control character sanitization tests (Plan 02 Task 2)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Wildcard path resolution tests (Plan 10 Task 5)
# ---------------------------------------------------------------------------


class TestResolveWildcardPath:
    """Tests for _resolve_wildcard_path wildcard-to-concrete matching."""

    def test_resolve_wildcard_creates_directory_for_concrete_path(self, tmp_path: Path):
        """When a contract declares characters/major/*.md and LLM outputs
        characters/major/chen-weimin.md, auto-create the major/ directory.
        """
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        contract_pattern = "characters/major/*.md"
        concrete_path = tmp_path / "characters" / "major" / "chen-weimin.md"
        assert not concrete_path.parent.exists()

        _resolve_wildcard_path(contract_pattern, str(concrete_path), base_dir=tmp_path)

        assert concrete_path.parent.exists()

    def test_resolve_wildcard_matches_pattern(self, tmp_path: Path):
        """Wildcard pattern should match concrete paths."""
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        assert (
            _resolve_wildcard_path(
                "characters/major/*.md",
                str(tmp_path / "characters" / "major" / "chen-weimin.md"),
                base_dir=tmp_path,
            )
            is True
        )

    def test_resolve_wildcard_rejects_non_matching_path(self, tmp_path: Path):
        """Concrete path must match the wildcard pattern."""
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        assert (
            _resolve_wildcard_path(
                "characters/major/*.md",
                str(tmp_path / "characters" / "protagonist.md"),
                base_dir=tmp_path,
            )
            is False
        )

    def test_resolve_wildcard_with_minor_characters(self, tmp_path: Path):
        """Test with minor character wildcard."""
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        contract_pattern = "characters/minor/*.md"
        concrete_path = tmp_path / "characters" / "minor" / "zhao-tiezhu.md"
        assert not concrete_path.parent.exists()

        _resolve_wildcard_path(contract_pattern, str(concrete_path), base_dir=tmp_path)
        assert concrete_path.parent.exists()

    def test_resolve_wildcard_creates_dir_for_truth_wildcard(self, tmp_path: Path):
        """truth/*.md wildcard should match truth/current_state.md."""
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        concrete_path = tmp_path / "truth" / "current_state.md"
        assert not concrete_path.parent.exists()

        result = _resolve_wildcard_path("truth/*.md", str(concrete_path), base_dir=tmp_path)
        assert result is True
        assert concrete_path.parent.exists()

    def test_resolve_wildcard_rejects_deeply_nested_path(self, tmp_path: Path):
        """Wildcard * should not match across directory boundaries."""
        from shenbi.pipeline.dispatch_helper import _resolve_wildcard_path

        assert (
            _resolve_wildcard_path(
                "characters/major/*.md",
                str(tmp_path / "characters" / "major" / "subdir" / "chen-weimin.md"),
                base_dir=tmp_path,
            )
            is False
        )


class TestWildcardToRegex:
    """Tests for _wildcard_to_regex pattern conversion."""

    def test_wildcard_pattern_to_regex(self):
        """Internal: pattern conversion."""
        from shenbi.pipeline.dispatch_helper import _wildcard_to_regex

        pattern = _wildcard_to_regex("characters/major/*.md")
        regex = re.compile(pattern)
        assert regex.match("characters/major/chen-weimin.md")
        assert not regex.match("characters/major/subdir/chen-weimin.md")
        assert not regex.match("characters/protagonist.md")

    def test_wildcard_to_regex_escapes_dots(self):
        """Dots in pattern should be escaped to match literal dots."""
        from shenbi.pipeline.dispatch_helper import _wildcard_to_regex

        pattern = _wildcard_to_regex("truth/*.md")
        regex = re.compile(pattern)
        assert regex.match("truth/current_state.md")
        assert not regex.match("truth/current_state_Xmd")  # dot must be literal

    def test_wildcard_to_regex_anchors_both_ends(self):
        """Pattern should be anchored at both start and end."""
        from shenbi.pipeline.dispatch_helper import _wildcard_to_regex

        pattern = _wildcard_to_regex("import/analysis/*.md")
        regex = re.compile(pattern)
        # Should match full path
        assert regex.match("import/analysis/01_plot.md")
        # Should NOT partial-match
        assert not regex.match("prefix_import/analysis/01_plot.md")
        assert not regex.match("import/analysis/01_plot.md_suffix")


class TestResolveAllWildcards:
    """Tests for _resolve_all_wildcards batch matching."""

    def test_resolve_all_matches_single_pattern(self, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import _resolve_all_wildcards

        contract_writes = ["characters/major/*.md", "characters/minor/*.md"]
        concrete = str(tmp_path / "characters" / "major" / "chen-weimin.md")

        matching = _resolve_all_wildcards(contract_writes, concrete, base_dir=tmp_path)
        assert matching == ["characters/major/*.md"]

    def test_resolve_all_creates_directories(self, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import _resolve_all_wildcards

        contract_writes = ["characters/major/*.md"]
        concrete = str(tmp_path / "characters" / "major" / "li-xiaoyao.md")

        assert not (tmp_path / "characters" / "major").exists()
        _resolve_all_wildcards(contract_writes, concrete, base_dir=tmp_path)
        assert (tmp_path / "characters" / "major").exists()

    def test_resolve_all_returns_empty_for_no_match(self, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import _resolve_all_wildcards

        contract_writes = ["characters/major/*.md"]
        concrete = str(tmp_path / "other" / "file.md")

        matching = _resolve_all_wildcards(contract_writes, concrete, base_dir=tmp_path)
        assert matching == []

    def test_resolve_all_handles_literal_fallback(self, tmp_path: Path):
        """Literal patterns (no wildcards) should also match via substring heuristic."""
        from shenbi.pipeline.dispatch_helper import _resolve_all_wildcards

        contract_writes = ["chapters/chapter-1.md"]
        concrete = str(tmp_path / "chapters" / "chapter-1.md")

        matching = _resolve_all_wildcards(contract_writes, concrete, base_dir=tmp_path)
        assert "chapters/chapter-1.md" in matching


class TestWriteParsedOutputsWithWildcards:
    """Integration tests for _write_parsed_outputs with wildcard contract patterns."""

    def test_writes_concrete_path_matching_wildcard(self, tmp_path: Path):
        """When LLM outputs characters/major/chen-weimin.md and contract has
        characters/major/*.md, the file should be written.
        """
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = "### FILE: characters/major/chen-weimin.md\n# 陈伟民\n\n主角的好友，性格沉稳。\n"
        output_paths = [
            "characters/protagonist.md",
            "characters/major/*.md",
            "characters/minor/*.md",
        ]
        _write_parsed_outputs(response, output_paths, tmp_path)

        written_file = tmp_path / "characters" / "major" / "chen-weimin.md"
        assert written_file.exists()
        content = written_file.read_text(encoding="utf-8")
        assert "陈伟民" in content

    def test_writes_multiple_wildcard_matches(self, tmp_path: Path):
        """Multiple wildcard-matching files should all be written."""
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = (
            "### FILE: characters/major/li-xiaoyao.md\n"
            "# 李逍遥\n\n主角。\n"
            "### FILE: characters/major/zhao-ling-er.md\n"
            "# 赵灵儿\n\n女主角。\n"
        )
        output_paths = ["characters/major/*.md"]
        _write_parsed_outputs(response, output_paths, tmp_path)

        assert (tmp_path / "characters" / "major" / "li-xiaoyao.md").exists()
        assert (tmp_path / "characters" / "major" / "zhao-ling-er.md").exists()

    def test_wildcard_and_literal_paths_together(self, tmp_path: Path):
        """Literal and wildcard writes should coexist."""
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = (
            "### FILE: characters/protagonist.md\n"
            "# 主角\n\n林烽。\n"
            "### FILE: characters/major/chen-weimin.md\n"
            "# 陈伟民\n\n好友。\n"
        )
        output_paths = [
            "characters/protagonist.md",
            "characters/major/*.md",
        ]
        _write_parsed_outputs(response, output_paths, tmp_path)

        assert (tmp_path / "characters" / "protagonist.md").exists()
        assert (tmp_path / "characters" / "major" / "chen-weimin.md").exists()

    def test_non_matching_parsed_output_is_skipped(self, tmp_path: Path):
        """A parsed output that matches neither literal nor wildcard should be skipped."""
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = "### FILE: unrelated/extra_file.md\n# Extra\n\nShould not be written.\n"
        output_paths = ["characters/major/*.md"]
        written = _write_parsed_outputs(response, output_paths, tmp_path)

        assert not (tmp_path / "unrelated" / "extra_file.md").exists()
        assert written == []


# ---------------------------------------------------------------------------
# Plan skeleton injection tests (Plan 10 Task 13)
# ---------------------------------------------------------------------------


class TestPlanSkeletonInjection:
    """Task 13: _build_skill_prompt injects plan skeleton for chapter planning."""

    def test_chapter_planning_prompt_includes_skeleton(self, tmp_path: Path, monkeypatch):
        """When dispatching shenbi-chapter-planning, the REAL _build_skill_prompt
        must include a plan skeleton when volume_map.md exists.

        This does NOT mock _build_skill_prompt (that would make the test a no-op).
        Instead it exercises the real function and asserts the skeleton-derived
        content appears in the returned prompt, proving the Task 13 wiring works.
        """
        from shenbi.contracts import OutputKind
        from shenbi.pipeline.dispatch_helper import (
            _build_skill_prompt,
        )

        # ---- Arrange: set up project structure ----
        outline_dir = tmp_path / "outline"
        outline_dir.mkdir()
        (outline_dir / "volume_map.md").write_text(
            """# Volume Map
## Volume 1 (Ch 1-15)
### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Test content |
""",
            encoding="utf-8",
        )

        # _build_skill_prompt reads SKILL.md from _PROJECT_ROOT / "skills" / skill.
        # Redirect _PROJECT_ROOT to tmp_path so it finds our test SKILL.md.
        skill_dir = tmp_path / "skills" / "shenbi-chapter-planning"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: shenbi-chapter-planning\n"
            "description: Use when planning\n"
            "contract: {kind: artifact}\n"
            "---\n# Chapter Planning Skill body\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "shenbi.pipeline.dispatch_helper._PROJECT_ROOT",
            tmp_path,
        )

        # Mock load_contract to return a minimal valid contract
        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["plans/chapter-1-plan.md"],
            "updates": [],
            "read_fields": {},
        }
        monkeypatch.setattr(
            "shenbi.contracts.legacy.load_contract",
            lambda s: mock_contract,
        )

        # ---- Act: call the REAL _build_skill_prompt ----
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill="shenbi-chapter-planning",
            project_dir=tmp_path,
            prompt="plan chapter 1",
            chapter=1,
        )

        # ---- Assert: skeleton-derived content proves Task 13 wiring ----
        assert "Plan Skeleton" in user_prompt or "plan skeleton" in user_prompt.lower()
        assert "Test content" in user_prompt
        assert "opening" in user_prompt.lower()


class TestSanitizeJsonContent:
    """Tests for sanitize_json_content (illegal control character removal)."""

    def test_sanitize_strips_illegal_control_characters(self):
        r"""Removes control characters except \\n, \\r, \\t."""
        from shenbi.pipeline.dispatch_helper import sanitize_json_content

        content = '{"key": "val\x00\x01\x02\x08\x0b\x0c\x0e\x1fue"}'
        result = sanitize_json_content(content)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x08" not in result
        assert "value" in result

    def test_sanitize_preserves_legal_control_characters(self):
        r"""Preserves \\n, \\r, \\t which are valid in JSON strings."""
        from shenbi.pipeline.dispatch_helper import sanitize_json_content

        content = '{"text": "line1\\nline2\\r\\n\\tindented"}'
        result = sanitize_json_content(content)
        assert "\\n" in result
        assert "\\r" in result
        assert "\\t" in result

    def test_sanitize_handles_clean_input(self):
        """Clean input is returned unchanged."""
        from shenbi.pipeline.dispatch_helper import sanitize_json_content

        content = '{"key": "value"}'
        result = sanitize_json_content(content)
        assert result == content

    def test_sanitize_handles_chinese_characters(self):
        """Chinese characters are preserved."""
        from shenbi.pipeline.dispatch_helper import sanitize_json_content

        content = '{"name": "林烽", "status": "在场"}'
        result = sanitize_json_content(content)
        assert "林烽" in result
        assert "在场" in result
