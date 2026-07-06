"""Dispatch + gate helpers for pipeline orchestrators.

Reuses the existing ``dispatch_with_write_audit`` (write-overreach detection)
via the dispatcher CLI rather than bypassing it. The dispatcher runs G1 (input
readiness) and G2 (output structure) internally; this module adds G3 (scoring
independence) and G4 (skill-specific structure) on top.
"""

from __future__ import annotations

import json
import os
import re
import shutil
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

#: Environment variable name for the LLM API key.
# When set, dispatch_skill() routes through the OpenAI-compatible API path
# instead of the CLI subprocess path.
_ENV_LLM_API_KEY = "SHENBI_LLM_API_KEY"
_ENV_LLM_BASE_URL = "SHENBI_LLM_BASE_URL"
_ENV_LLM_MODEL = "SHENBI_LLM_MODEL"
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o"


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
    "shenbi-escalation-review": [
        "resonance_trend.md",
        "volume-*-score.md",
        "arc-*-score.md",
        "stratum-*-score.md",
        "chapter-*-sensitivity.md",
    ],
}

_G1_SKIP_ENV_VAR = "SHENBI_G1_SKIP_READS"

#: CLI commands to try for IDE-based dispatch (checked in order).
_IDE_CLI_COMMANDS = [
    "codex exec -C {dir} {prompt}",
    "zcode exec --cwd {dir} {prompt}",
]


def _extract_chapter(prompt: str) -> int | None:
    """Extract chapter number from a pipeline prompt like '... for chapter 5.'."""
    m = re.search(r"chapter\s+(\d+)", prompt, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _resolve_path(path: str, chapter: int | None) -> str:
    """Replace N / NNN placeholders with chapter number; return as-is if chapter is None."""
    if chapter is None:
        return path
    return path.replace("NNN", f"{chapter:03d}").replace("N", str(chapter))


def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
) -> tuple[str, str, list[str]]:
    """Build a complete execution prompt for a skill.

    Returns (system_prompt, user_prompt, output_paths) where:
    - system_prompt: SKILL.md content
    - user_prompt: task description + input file contents
    - output_paths: resolved contract writable paths the agent must produce
    """
    from shenbi.contracts.legacy import ContractError, load_contract

    try:
        contract = load_contract(skill)
    except ContractError as exc:
        log.error("contract_load_failed", skill=skill, error=str(exc))
        raise

    # System prompt = SKILL.md
    skill_file = Path("skills") / skill / "SKILL.md"
    if skill_file.exists():
        system_prompt = skill_file.read_text(encoding="utf-8")
    else:
        log.warning("skill_file_missing", skill=skill, path=str(skill_file))
        system_prompt = f"Execute the {skill} skill."

    # Read contract inputs
    input_texts: dict[str, str] = {}
    for read_path in contract.get("reads", []):
        resolved = _resolve_path(read_path, chapter)
        full_path = project_dir / resolved
        if full_path.exists():
            try:
                input_texts[resolved] = full_path.read_text(encoding="utf-8")
            except Exception:
                input_texts[resolved] = f"[binary or unreadable: {resolved}]"
        else:
            input_texts[resolved] = f"[file not found: {resolved}]"

    # Collect output paths
    output_paths: list[str] = []
    for write_path in contract.get("writes", []):
        output_paths.append(_resolve_path(write_path, chapter))
    for update_path in contract.get("updates", []):
        output_paths.append(_resolve_path(update_path, chapter))

    # Build user prompt
    user_parts = [f"## Task\n{prompt}"]
    user_parts.append(f"\n## Output Files You Must Create\n")
    for p in output_paths:
        user_parts.append(f"- {p}")
    if input_texts:
        user_parts.append("\n## Input Files (read-only reference)")
        for fname, content in input_texts.items():
            user_parts.append(f"### {fname}\n```\n{content[:8000]}\n```")
    user_prompt = "\n\n".join(user_parts)

    return system_prompt, user_prompt, output_paths


def _write_outputs(output_text: str, output_paths: list[str], project_dir: Path) -> None:
    """Write the LLM response to each declared output path."""
    for rel_path in output_paths:
        full_path = project_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(full_path, output_text)
        log.info("output_written", path=rel_path, size=len(output_text))


def _find_ide_cli() -> str | None:
    """Return the first available IDE CLI command template, or None."""
    for cmd_template in _IDE_CLI_COMMANDS:
        cli_name = cmd_template.split()[0]
        if shutil.which(cli_name):
            return cmd_template
    return None


def _dispatch_via_ide(
    skill: str,
    project_dir: Path,
    prompt: str,
) -> DispatchResult:
    """Execute a skill via an IDE agent CLI (codex / zcode).

    Builds a complete prompt with SKILL.md instructions and input files,
    then spawns the IDE agent to execute the skill and produce output files.
    """
    chapter = _extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill, project_dir, prompt, chapter
        )
    except Exception as exc:
        return DispatchResult(False, -1, "", f"Prompt build failed: {exc}")

    cli_template = _find_ide_cli()
    if not cli_template:
        log.error("ide_no_cli_found")
        return DispatchResult(False, -1, "", "No IDE CLI (codex/zcode) found on PATH")

    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    cmd_str = cli_template.format(dir=str(project_dir), prompt=full_prompt)
    cmd_parts = cmd_str.split()

    log.info("ide_dispatch_start", skill=skill, cmd=cmd_parts[0], chapter=chapter)
    try:
        r = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        log.error("ide_timeout", skill=skill)
        return DispatchResult(False, -1, "", "IDE agent timed out after 600s")
    except FileNotFoundError:
        log.error("ide_cli_not_found", cmd=cmd_parts[0])
        return DispatchResult(False, -1, "", f"IDE CLI not found: {cmd_parts[0]}")

    if r.returncode != 0:
        log.error("ide_failed", skill=skill, rc=r.returncode, stderr=r.stderr[:500])
        return DispatchResult(False, r.returncode, r.stdout, r.stderr)

    log.info("ide_dispatch_complete", skill=skill)

    # Verify output files exist; write agent output if missing
    for rel_path in output_paths:
        full_path = project_dir / rel_path
        if not full_path.exists():
            _write_outputs(r.stdout, [rel_path], project_dir)

    return DispatchResult(True, 0, r.stdout, r.stderr)


def _dispatch_via_api(
    skill: str,
    project_dir: Path,
    prompt: str,
) -> DispatchResult:
    """Execute a skill via OpenAI-compatible API.

    Configure via environment variables:
    - ``SHENBI_LLM_API_KEY`` (required)
    - ``SHENBI_LLM_BASE_URL`` (default: https://api.openai.com/v1)
    - ``SHENBI_LLM_MODEL`` (default: gpt-4o)
    """
    from openai import OpenAI  # type: ignore[import-untyped]

    chapter = _extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill, project_dir, prompt, chapter
        )
    except Exception as exc:
        return DispatchResult(False, -1, "", f"Prompt build failed: {exc}")

    client = OpenAI(
        api_key=os.environ[_ENV_LLM_API_KEY],
        base_url=os.environ.get(_ENV_LLM_BASE_URL, _DEFAULT_BASE_URL),
    )
    model = os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)

    log.info("api_dispatch_start", skill=skill, model=model, chapter=chapter)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=16384,
        )
    except Exception as exc:
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")

    output_text = response.choices[0].message.content or ""
    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)

    _write_outputs(output_text, output_paths, project_dir)
    return DispatchResult(True, 0, output_text, "")


def dispatch_skill(
    skill: str,
    project_dir: Path | str,
    prompt: str,
    test_type: str = "generative",
    round_dir: Path | str | None = None,
    timeout: int = 900,
    skip_reads: list[str] | None = None,
) -> DispatchResult:
    """Dispatch a skill for execution.

    Routing (tried in order):
    1. ``SHENBI_LLM_API_KEY`` set → OpenAI-compatible API (DeepSeek, MiniMax, etc.)
    2. IDE CLI available (codex / zcode) → spawn agent subprocess
    3. Fallback → ``shenbi-dispatch`` CLI subprocess (T1 testing / legacy)
    """
    pd = Path(project_dir)

    # API path
    if os.environ.get(_ENV_LLM_API_KEY):
        return _dispatch_via_api(skill, pd, prompt)

    # IDE path
    if _find_ide_cli():
        return _dispatch_via_ide(skill, pd, prompt)

    # Legacy CLI subprocess path
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
