"""Dispatcher executor: orchestrates gate checks + sub-agent dispatch.

PR-20 (P-1.E): Python translation of tests/dispatch-subagent.sh (203 lines).
Replaces shell script with typed, loggable Python.
"""

from __future__ import annotations
from typing import Any

import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = REPO_ROOT


def generate_agent_id(round_dir: Path, skill: str, test_type: str) -> str:
    """Generate unique agent ID for this dispatch."""
    return f"{round_dir.name}-{skill}-{test_type}-{uuid.uuid4().hex[:8]}"


def derive_file_type(skill: str) -> str:
    """Derive FILE_TYPE from skill name."""
    chapter_skills = {
        "shenbi-chapter-drafting",
        "shenbi-style-polishing",
        "shenbi-anti-detect",
        "shenbi-length-normalizing",
    }
    truth_skills = {
        "shenbi-state-settling",
        "shenbi-foreshadowing-track",
        "shenbi-foreshadowing-plant",
    }
    if skill in chapter_skills:
        return "chapter"
    if skill in truth_skills:
        return "truth"
    return "chapter"


def derive_input_files(skill: str) -> list[str]:
    """Parse SKILL.md to extract Reads."""
    skill_md = PROJECT_DIR / "skills" / skill / "SKILL.md"
    if not skill_md.exists():
        return []
    content = skill_md.read_text(encoding="utf-8")
    reads_match = re.findall(r"\*\*Reads:\*\*\s*(.*)", content)
    files = []
    for line in reads_match:
        files.extend(re.findall(r"`([^`]+)`", line))
    return files


def derive_output_files(skill: str) -> list[str]:
    """Parse SKILL.md to extract Writes + Updates."""
    skill_md = PROJECT_DIR / "skills" / skill / "SKILL.md"
    if not skill_md.exists():
        return []
    content = skill_md.read_text(encoding="utf-8")
    writes = re.findall(r"\*\*Writes:\*\*\s*(.*)", content)
    updates = re.findall(r"\*\*Updates:\*\*\s*(.*)", content)
    files = []
    for line in writes + updates:
        files.extend(re.findall(r"`([^`]+)`", line))
    return files


def run_g1(skill: str, inputs: list[str], round_dir: Path) -> dict[str, Any]:
    """Run G1 gate via shenbi-validate entry point."""
    inputs_json = json.dumps(inputs)
    result = subprocess.run(
        ["uv", "run", "shenbi-validate", "G1", skill, inputs_json, str(round_dir)],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def run_g2(outputs: list[str], file_type: str, round_dir: Path) -> dict[str, Any]:
    """Run G2 gate via shenbi-validate entry point."""
    output_files = ",".join(outputs)
    result = subprocess.run(
        [
            "uv",
            "run",
            "shenbi-validate",
            "G2",
            output_files,
            file_type,
            str(round_dir),
            str(PROJECT_DIR),
        ],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def detect_mode() -> str:
    """Detect dispatch mode (codex, codex-api, or internal)."""
    if shutil.which("codex"):
        return "codex"
    if os.environ.get("CODEX_API_KEY"):
        return "codex-api"
    return "internal"


def dispatch(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
    """Main dispatch entry point."""
    agent_id = generate_agent_id(round_dir, skill, test_type)
    log.info("dispatch_start", agent_id=agent_id, skill=skill, test_type=test_type)

    file_type = derive_file_type(skill)
    input_files = derive_input_files(skill)

    g1 = run_g1(skill, input_files, round_dir)
    if g1.get("status") != "PASS":
        log.error("g1_failed", gate="G1", result=g1)
        return 1
    log.info("gate_passed", gate="G1")

    output_files = derive_output_files(skill)
    if output_files:
        g2 = run_g2(output_files, file_type, round_dir)
        if g2.get("status") != "PASS":
            log.error("g2_failed", gate="G2", result=g2)
            return 1
        log.info("gate_passed", gate="G2")

    mode = detect_mode()
    log.info("dispatch_mode", mode=mode)

    if mode == "codex":
        from shenbi.dispatcher.modes.codex import dispatch_codex

        return dispatch_codex(skill, test_type, round_dir, prompt, agent_id)
    if mode == "codex-api":
        from shenbi.dispatcher.modes.codex_api import dispatch_codex_api

        return dispatch_codex_api(skill, test_type, round_dir, prompt, agent_id)
    from shenbi.dispatcher.modes.internal import dispatch_internal

    return dispatch_internal(skill, test_type, round_dir, prompt, agent_id)
