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

    @patch(PATCH)
    def test_round_dir_override(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        round_dir = tmp_path / "round-001"
        round_dir.mkdir()
        dispatch_skill("shenbi-worldbuilding", tmp_path, "prompt", round_dir=round_dir)
        cmd = mock_run.call_args[0][0]
        assert str(round_dir) in cmd

    @patch(PATCH)
    def test_passes_prompt_to_cli(self, mock_run, tmp_path):
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
