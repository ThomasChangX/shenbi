"""Verify run_gate() targets the live shenbi.gates.cli module, not the deleted
tests/validate-gate.py file.

Regression guard for the PR-19 migration that extracted gate logic into
src/shenbi/gates/ but left phase_runner.py calling the old path.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from shenbi.phase_runner import run_gate


class TestRunGateTarget:
    @patch("shenbi.phase_runner.subprocess.run")
    def test_calls_gates_cli_module_not_validate_gate_py(self, mock_run, tmp_path):
        """run_gate must invoke `python -m shenbi.gates.cli`, never tests/validate-gate.py."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"status": "PASS"}', stderr=""
        )
        run_gate("G5", ["some-phase", str(tmp_path), str(tmp_path)])
        called_cmd = mock_run.call_args[0][0]
        # The command list must contain "-m" and "shenbi.gates.cli"
        assert "-m" in called_cmd, f"expected -m flag, got {called_cmd}"
        assert "shenbi.gates.cli" in called_cmd, (
            f"expected shenbi.gates.cli module, got {called_cmd}"
        )
        # Must NOT reference the deleted file
        assert not any("validate-gate.py" in str(part) for part in called_cmd), (
            f"run_gate still references deleted tests/validate-gate.py: {called_cmd}"
        )

    @patch("shenbi.phase_runner.subprocess.run")
    def test_returns_parsed_json_on_success(self, mock_run, tmp_path):
        """Non-regression: success path still returns parsed JSON."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"status": "PASS", "checks": []}', stderr=""
        )
        result = run_gate("G2", ["file.md", "chapter", str(tmp_path)])
        assert result["status"] == "PASS"

    @patch("shenbi.phase_runner.subprocess.run")
    def test_returns_fail_dict_on_oserror(self, mock_run, tmp_path):
        """If subprocess.run raises OSError (e.g. python binary missing), run_gate
        must return a FAIL dict, not propagate the exception.

        NOTE: FileNotFoundError subclasses OSError (NOT subprocess.SubprocessError).
        This test guards the except clause catches the right hierarchy.
        """
        mock_run.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'python3'")
        result = run_gate("G4", ["skill", "file.md", str(tmp_path)])
        assert result["status"] == "FAIL"
