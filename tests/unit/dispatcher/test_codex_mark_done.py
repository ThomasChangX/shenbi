"""Verify dispatch_codex records completion via direct progress.json update,
not via the non-existent shenbi-progress CLI subprocess.

Regression for the shenbi-progress entry point that was never registered in
pyproject.toml (historical tests/update-progress.py was deleted).
"""

from __future__ import annotations

import json
from unittest.mock import patch

from shenbi.dispatcher.modes.codex import dispatch_codex


class TestCodexMarkDone:
    def test_writes_completion_to_progress_json(self, tmp_path):
        """After a successful codex dispatch+score, progress.json must contain
        the skill in completed_skill_names with its score — written directly,
        not via a shenbi-progress subprocess.
        """
        round_dir = tmp_path / "round-001"
        round_dir.mkdir()
        (round_dir / "t1-reports").mkdir()

        # Mock the two real subprocesses: codex exec + shenbi-score.
        # codex exec writes a raw scores file; shenbi-score outputs final JSON.
        def fake_run(cmd, **kwargs):
            class FakeResult:
                returncode = 0
                # shenbi-score outputs a JSON with final_score
                stdout = json.dumps({"final_score": 92, "status": "ok"})
                stderr = ""

            return FakeResult()

        # Pre-create the raw output file that codex exec would produce
        # (dispatch_codex reads it to extract scores JSON)
        raw_file = round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores-subagent.raw"
        raw_file.write_text('{"1": 90, "2": 95}', encoding="utf-8")

        with patch("shenbi.dispatcher.modes.codex.subprocess.run", side_effect=fake_run):
            rc = dispatch_codex(
                "shenbi-worldbuilding",
                "generative",
                round_dir,
                "test prompt",
                "agent-001",
            )

        assert rc == 0
        # progress.json must now exist and record completion
        progress_path = round_dir / "progress.json"
        assert progress_path.exists(), "progress.json was not written"
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        assert "shenbi-worldbuilding" in progress.get("completed_skill_names", []), (
            f"skill not in completed_skill_names: {progress}"
        )

    def test_does_not_call_shenbi_progress_subprocess(self, tmp_path):
        """No subprocess command may contain 'shenbi-progress'."""
        round_dir = tmp_path / "round-002"
        round_dir.mkdir()
        (round_dir / "t1-reports").mkdir()
        raw_file = round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores-subagent.raw"
        raw_file.write_text('{"1": 90}', encoding="utf-8")

        captured_cmds: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))

            class FakeResult:
                returncode = 0
                stdout = json.dumps({"final_score": 90})
                stderr = ""

            return FakeResult()

        with patch("shenbi.dispatcher.modes.codex.subprocess.run", side_effect=fake_run):
            dispatch_codex("shenbi-worldbuilding", "generative", round_dir, "p", "a")

        for cmd in captured_cmds:
            assert not any("shenbi-progress" in str(part) for part in cmd), (
                f"shenbi-progress subprocess still called: {cmd}"
            )
