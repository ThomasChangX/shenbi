"""Tests for the skill-description audit tool (spec §3.4)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[3] / "tools" / "audit-skill-descriptions.py"


class TestAuditTool:
    def test_tool_exists(self):
        assert _TOOLS.exists(), f"audit tool missing at {_TOOLS}"

    def test_tool_runs_against_synthetic_dir(self, tmp_path: Path):
        """The tool emits a report and exits non-zero on a violation."""
        skill = tmp_path / "shenbi-bad"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: shenbi-bad\n"
            "description: |\n  This skill generates a huge plot. " + ("x" * 600) + "\n"
            "contract: {kind: ephemeral}\n---\n# body\n",
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(_TOOLS), "--skills-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode != 0, "tool must exit non-zero when violations exist"
        assert "shenbi-bad" in r.stdout

    def test_clean_dir_exits_zero(self, tmp_path: Path):
        skill = tmp_path / "shenbi-good"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            '---\nname: shenbi-good\ndescription: "Use when a chapter fails the audit"\n'
            "contract: {kind: ephemeral}\n---\n# body\n",
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(_TOOLS), "--skills-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"clean dir must pass: {r.stdout}\n{r.stderr}"
