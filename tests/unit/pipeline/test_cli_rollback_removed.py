"""Verify the rollback subcommand is removed from CLI registration.

cmd_rollback still exists (for direct callers) but returns a non-zero exit
code. The subparser is removed so 'pipeline --help' doesn't advertise an
unimplemented command.
"""

from __future__ import annotations

import argparse

import pytest

from shenbi.pipeline.cli import cmd_rollback, main


class TestRollbackRemoved:
    def test_help_does_not_list_rollback(self, capsys):
        """'pipeline --help' output must not contain 'rollback'."""
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "rollback" not in captured.out.lower(), (
            f"--help still advertises rollback: {captured.out}"
        )

    def test_cmd_rollback_returns_nonzero(self, tmp_path):
        """Direct cmd_rollback call must return exit code >= 1 (not 0)."""
        args = argparse.Namespace(project_dir=str(tmp_path), chapter=5)
        rc = cmd_rollback(args)
        assert rc != 0, f"cmd_rollback returned {rc}, expected non-zero (not faking success)"
