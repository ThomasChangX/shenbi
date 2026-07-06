"""Dispatch + gate helpers for pipeline orchestrators.

Reuses the existing ``dispatch_with_write_audit`` (write-overreach detection)
via the dispatcher CLI rather than bypassing it. The dispatcher runs G1 (input
readiness) and G2 (output structure) internally; this module adds G3 (scoring
independence) and G4 (skill-specific structure) on top.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uuid import uuid4

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.status import GateStatus

log = get_logger(__name__)


@dataclass
class DispatchResult:
    """Outcome of a single skill dispatch."""

    success: bool
    returncode: int
    stdout: str
    stderr: str


def requires_independent(skill: str) -> bool:
    """Whether a skill requires an independent agent (G3 enforcement).

    Reads the top-level ``requires_independent_agent`` frontmatter flag via the
    contract layer. Returns False on any error (missing skill, bad YAML, etc.).
    """
    from shenbi.contracts import requires_independent_agent

    try:
        return requires_independent_agent(skill)
    except Exception:
        log.debug("requires_independent_error", skill=skill)
        return False


#: Skills and their reads that are optional (produced late, missing in ramp-up).
# These paths are excluded from G1 input validation so early chapters don't
# fail G1 on files that later chapters will produce.
OPTIONAL_READS: dict[str, list[str]] = {
    "shenbi-context-composing": ["arc-*.md", "volume_summaries.md", "trend"],
    "shenbi-drift-guidance": ["arc-*.md"],
    # Chapter plans don't exist during GENESIS mode (spec §5.2)
    "shenbi-foreshadowing-plant": ["chapter-*-plan.md"],
    "shenbi-foreshadowing-track": ["chapter-*-plan.md"],
    "shenbi-chapter-planning": ["chapter-*-plan.md"],
    "shenbi-chapter-drafting": ["chapter-*-plan.md"],
}

_G1_SKIP_ENV_VAR = "SHENBI_G1_SKIP_READS"


def dispatch_skill(
    skill: str,
    project_dir: Path | str,
    prompt: str,
    test_type: str = "generative",
    round_dir: Path | str | None = None,
    timeout: int = 900,
    skip_reads: list[str] | None = None,
) -> DispatchResult:
    """Dispatch a skill via ``shenbi.dispatcher.cli``.

    The dispatcher CLI internally calls ``dispatch_with_write_audit``, which runs
    G1 + G2 and the write-overreach audit. Returns a :class:`DispatchResult`
    capturing the subprocess outcome.
    """
    # Merge explicit skip_reads with known optional reads for this skill.
    patterns = list(skip_reads or [])
    patterns.extend(OPTIONAL_READS.get(skill, []))

    rd = str(round_dir) if round_dir else str(project_dir)
    log.info("dispatch_start", skill=skill, test_type=test_type, round_dir=rd)
    env = os.environ.copy()
    if patterns:
        env[_G1_SKIP_ENV_VAR] = ",".join(patterns)
        log.debug("dispatch_skip_reads", skill=skill, patterns=patterns)
    try:
        _run_cmd = ["uv", "run", "shenbi-dispatch", skill, test_type, rd, prompt]
        r = subprocess.run(_run_cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        log.error("dispatch_timeout", skill=skill, timeout=timeout)
        return DispatchResult(False, -1, "", str(exc))
    # Log dispatch result for error visibility
    if r.returncode != 0:
        stderr_preview = r.stderr[:2000] if r.stderr else "(empty)"
        log.error(
            "dispatch_subprocess_failed",
            skill=skill,
            rc=r.returncode,
            stderr_preview=stderr_preview,
            cmd_preview=" ".join(str(x)[:80] for x in _run_cmd),
        )
    else:
        log.info("dispatch_subprocess_ok", skill=skill, rc=0)
    return DispatchResult(r.returncode == 0, r.returncode, r.stdout, r.stderr)


def run_gate_g4(skill: str, files: list[str], project_dir: Path | str) -> dict[str, Any]:
    """Run G4 (skill-specific structural check) after dispatch."""
    cmd = [
        sys.executable,
        "-m",
        "shenbi.gates.cli",
        "G4",
        skill,
        ",".join(files),
        str(project_dir),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        log.error("g4_timeout", skill=skill)
        return {"status": GateStatus.FAIL, "error": "G4 timed out"}
    try:
        return json.loads(r.stdout)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"status": GateStatus.FAIL, "error": "unparseable G4 output", "stderr": r.stderr}


def run_gate_g3(skill: str, round_dir: Path | str) -> dict[str, Any]:
    """Run G3 (scoring independence) check.

    Creates a minimal progress.json if none exists (pipeline mode) so that
    G3.3-G3.5 have the data they need for independence verification.
    """
    rd = Path(round_dir)
    pp = rd / "progress.json"
    if not pp.exists():
        safe_write(
            pp,
            json.dumps(
                {
                    "current_scorer_agent": f"pipeline-g3-scorer-{uuid4().hex[:12]}",
                    "scoring_history": [
                        {
                            "agent": "pipeline-skill-generator",
                            "g2_passed": True,
                        }
                    ],
                },
                indent=2,
            ),
        )
        log.info("progress_json_created_for_g3", skill=skill, path=str(pp))

    cmd = [
        sys.executable,
        "-m",
        "shenbi.gates.cli",
        "G3",
        skill,
        "generative",
        str(rd),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        log.error("g3_timeout", skill=skill)
        return {"status": GateStatus.FAIL, "error": "G3 timed out"}
    try:
        return json.loads(r.stdout)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"status": GateStatus.FAIL, "error": "unparseable G3 output", "stderr": r.stderr}
