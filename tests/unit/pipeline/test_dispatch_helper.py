"""Tests for dispatch helper (G3/G4 + write-audit integration).

Wave 3 Task 1: dispatch wrapper that reuses the existing dispatcher CLI
(which runs G1+G2 + write-overreach audit) and adds G3/G4 gate calls.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from shenbi.pipeline.dispatch_helper import (
    DispatchResult,
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
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt")
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == "ok"

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

    def test_character_matrix_has_declared_h2_stubs(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(tmp_path)
        body = (tmp_path / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        # context-composing declares these 4 fields.
        assert "## 主角" in body
        assert "## 主要配角" in body
        assert "## 反派" in body
        assert "## 角色关系图谱" in body

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
        assert "type: current_state" in body
        assert "category: truth" in body
        assert "status: initialized" in body

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
        fields_map = {"truth/current_state.md": ["主角状态", "当前世界局势", "活跃线索"]}
        warnings = check_fields_exist("shenbi-chapter-planning", inputs, fields_map)
        assert warnings == []
