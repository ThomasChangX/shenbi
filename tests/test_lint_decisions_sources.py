"""T106/F439 (spec #30 T4): the decisions producer set is reconciled across
three sources (SKILL writes, truth-files.yaml, schema doc Per-Skill table)
by tools/lint_decisions_sources.py, and every producer documents the required
sidecar fields.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent

PRODUCERS = [
    "shenbi-chapter-drafting",
    "shenbi-chapter-revision",
    "shenbi-chapter-planning",
    "shenbi-context-composing",
    "shenbi-genre-config",
    "shenbi-market-radar",
    "shenbi-short-drafting",
    "shenbi-state-settling",
]


def test_lint_passes_on_current_tree():
    r = subprocess.run(
        [sys.executable, "tools/lint_decisions_sources.py"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_producer_documents_required_fields():
    for skill in PRODUCERS:
        text = (REPO / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "decisions sidecar 必填字段" in text, skill
        for field in ("$schema", "skill", "chapter", "produced_at"):
            assert field in text, f"{skill} missing {field}"


def test_state_settling_sidecar_declared_in_writes():
    """T2 follow-up: state-settling's sidecar now in contract writes."""
    text = (REPO / "skills" / "shenbi-state-settling" / "SKILL.md").read_text(encoding="utf-8")
    assert "truth/state-settling-decisions.json" in text.split("---")[1]
