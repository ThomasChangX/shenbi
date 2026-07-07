"""Dispatch + gate helpers for pipeline orchestrators.

Reuses the existing ``dispatch_with_write_audit`` (write-overreach detection)
via the dispatcher CLI rather than bypassing it. The dispatcher runs G1 (input
readiness) and G2 (output structure) internally; this module adds G3 (scoring
independence) and G4 (skill-specific structure) on top.

Dispatch routing (tried in order):
1. ``SHENBI_LLM_API_KEY`` set → OpenAI-compatible API (DeepSeek, MiniMax, etc.)
2. IDE CLI available (codex / zcode) → spawn agent subprocess via stdin
3. Fallback → ``shenbi-dispatch`` CLI subprocess (T1 testing / legacy)
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

#: Environment variable names
_ENV_LLM_API_KEY = "SHENBI_LLM_API_KEY"
_ENV_LLM_BASE_URL = "SHENBI_LLM_BASE_URL"
_ENV_LLM_MODEL = "SHENBI_LLM_MODEL"

#: Dispatch configuration constants
_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
_DEFAULT_MODEL = "deepseek-v4-pro"  # fallback when SHENBI_LLM_MODEL not set
_IDE_AGENT_TIMEOUT = 900  # seconds for IDE agent subprocess (increased for large prompts)
_API_MAX_TOKENS = 16384  # max tokens per API call
_API_TEMPERATURE = 0.7  # default temperature for API calls
_INPUT_MAX_CHARS_PER_FILE = 32000  # hard cap per input file (~8K tokens)
_INPUT_MAX_CHARS_TOTAL = 128000  # total input budget (~32K tokens)
_AUDIT_HARD_CAP = 100  # safety cap for audit revision loop


@dataclass
class DispatchResult:
    """Outcome of a single skill dispatch."""

    success: bool
    returncode: int
    stdout: str
    stderr: str


def requires_independent(skill: str) -> bool:
    """Whether a skill requires an independent agent (G3 enforcement)."""
    from shenbi.contracts import requires_independent_agent

    try:
        return requires_independent_agent(skill)
    except Exception:
        log.debug("requires_independent_error", skill=skill)
        return False


#: Skills and their reads that are optional (produced late, missing in ramp-up).
OPTIONAL_READS: dict[str, list[str]] = {
    "shenbi-context-composing": ["arc-*.md", "volume_summaries.md", "trend"],
    "shenbi-drift-guidance": ["arc-*.md"],
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


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _extract_chapter(prompt: str) -> int | None:
    """Extract chapter number from a pipeline prompt like '... for chapter 5.'"""
    m = re.search(r"chapter\s+(\d+)", prompt, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _resolve_path(path: str, chapter: int | None) -> str:
    """Replace N / NNN placeholders with chapter number.

    Uses bounded replacement: ``NNN`` → zero-padded chapter, then ``-N``
    (preceded by hyphen/slash) → chapter number. Paths without chapter
    context are returned as-is.
    """
    if chapter is None:
        return path
    result = path.replace("NNN", f"{chapter:03d}")
    return re.sub(r"(?<=[-/])N(?=[-./]|$)", str(chapter), result)


def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
    uses_staging: bool = False,
) -> tuple[str, str, list[str]]:
    """Build a complete execution prompt for a skill.

    Returns (system_prompt, user_prompt, output_paths) where:
    - system_prompt: SKILL.md content
    - user_prompt: task description + input file contents + output format
    - output_paths: resolved contract writable paths (prefixed with staging/
      when uses_staging=True)
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

    # Read contract inputs with proportional budget
    input_texts: dict[str, str] = {}
    raw_inputs: dict[str, str] = {}
    for read_path in contract.get("reads", []):
        resolved = _resolve_path(read_path, chapter)
        full_path = project_dir / resolved
        if full_path.exists():
            try:
                raw_inputs[resolved] = full_path.read_text(encoding="utf-8")
            except Exception:
                raw_inputs[resolved] = f"[binary or unreadable: {resolved}]"
        else:
            raw_inputs[resolved] = f"[file not found: {resolved}]"

    # Apply per-file cap and proportional total budget
    total_raw = sum(len(v) for v in raw_inputs.values())
    if total_raw > _INPUT_MAX_CHARS_TOTAL and len(raw_inputs) > 1:
        budget_per_file = _INPUT_MAX_CHARS_TOTAL // len(raw_inputs)
        for fname, text in raw_inputs.items():
            limit = min(_INPUT_MAX_CHARS_PER_FILE, budget_per_file)
            if len(text) > limit:
                log.warning(
                    "input_truncated",
                    skill=skill,
                    path=fname,
                    original=len(text),
                    truncated=limit,
                )
                input_texts[fname] = text[:limit]
            else:
                input_texts[fname] = text
    else:
        for fname, text in raw_inputs.items():
            if len(text) > _INPUT_MAX_CHARS_PER_FILE:
                log.warning(
                    "input_truncated",
                    skill=skill,
                    path=fname,
                    original=len(text),
                    truncated=_INPUT_MAX_CHARS_PER_FILE,
                )
                input_texts[fname] = text[:_INPUT_MAX_CHARS_PER_FILE]
            else:
                input_texts[fname] = text

    # Collect output paths
    output_paths: list[str] = []
    for write_path in contract.get("writes", []):
        output_paths.append(_resolve_path(write_path, chapter))
    for update_path in contract.get("updates", []):
        output_paths.append(_resolve_path(update_path, chapter))

    # When uses_staging is True, prefix all output paths with staging/
    if uses_staging:
        output_paths = [f"staging/{p}" for p in output_paths]

    # Build user prompt
    user_parts = [
        "## PIPELINE MODE — AUTONOMOUS EXECUTION",
        "You are running inside an automated pipeline. Do NOT ask questions.",
        "Generate all content directly using the input files provided below.",
        "Do not wait for human confirmation. Produce complete output immediately.",
        "",
        f"## Task\n{prompt}",
        "",
        "## Output Format (CRITICAL — follow exactly)",
        "Output each file using this EXACT format with NO extra text:",
        "```",
        "### FILE: path/to/file1.md",
        "[complete file content — no markdown wrappers]",
        "### FILE: path/to/file2.json",
        "[complete file content — no markdown wrappers]",
        "```",
        "Rules:",
        "- Use ### FILE: markers EXACTLY as shown above",
        "- File content starts on the line AFTER the marker",
        "- Do NOT wrap content in ``` fences",
        "- Do NOT add text before the first ### FILE: marker",
        "- Do NOT add text after the last file's content",
        "",
        "Files to create:",
    ]
    for p in output_paths:
        if "*" not in p:
            user_parts.append(f"- {p}")
    if input_texts:
        user_parts.append("\n## Input Files (read-only reference)")
        for fname, content in input_texts.items():
            user_parts.append(f"### {fname}\n```\n{content}\n```")
    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt, output_paths


# ---------------------------------------------------------------------------
# Output parsing and writing
# ---------------------------------------------------------------------------


def _parse_file_outputs(response: str) -> dict[str, str]:
    """Parse a multi-file response into {filepath: content} dict.

    Expects markers like ``### FILE: path/to/file.md`` followed by content.
    Strips leading/trailing ``` fences from content if present.
    Falls back to returning the full response under ``__stdout__``.
    """
    pattern = r"###\s*FILE:\s*(\S+)\s*\n(.*?)(?=###\s*FILE:|\Z)"
    matches = re.findall(pattern, response, re.DOTALL)

    if matches:
        result: dict[str, str] = {}
        for path, content in matches:
            content = content.strip()
            content = re.sub(r"^```[\w]*\s*\n", "", content)
            content = re.sub(r"\n```\s*$", "", content)
            result[path.strip()] = content.strip()
        return result

    return {"__stdout__": response}


def _write_parsed_outputs(
    response: str,
    output_paths: list[str],
    project_dir: Path,
    create_truth_templates: bool = False,
) -> list[str]:
    """Parse agent response and write per-file content.

    Returns list of successfully written paths.
    """
    parsed = _parse_file_outputs(response)
    written: list[str] = []

    for rel_path in output_paths:
        if "*" in rel_path:
            continue
        content = parsed.get(rel_path, parsed.get("__stdout__", ""))
        if not content.strip():
            log.warning("output_empty", path=rel_path)
            continue
        full_path = project_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(full_path, content)
        written.append(rel_path)
        log.info("output_written", path=rel_path, size=len(content))

    if create_truth_templates and any("*" in p for p in output_paths):
        _init_truth_templates(project_dir)

    return written


def _init_truth_templates(project_dir: Path) -> None:
    """Create minimal truth template files with required YAML frontmatter."""
    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    templates = {
        "current_state.md": (
            "type: current_state\ncategory: truth\nstatus: initialized\n---\n# Current State\n"
        ),
        "character_matrix.md": (
            "type: character_matrix\ncategory: truth\nstatus: initialized\n"
            "---\n# Character Matrix\n"
        ),
        "emotional_arcs.md": (
            "type: emotional_arcs\ncategory: truth\nstatus: initialized\n---\n# Emotional Arcs\n"
        ),
        "chapter_summaries.md": (
            "type: chapter_summaries\ncategory: truth\nstatus: initialized\n"
            "---\n# Chapter Summaries\n"
        ),
    }
    for filename, content in templates.items():
        tp = truth_dir / filename
        if not tp.exists():
            safe_write(tp, f"---\n{content}")
            log.info("truth_template_created", path=str(tp))


# ---------------------------------------------------------------------------
# Dispatch paths
# ---------------------------------------------------------------------------


def _dispatch_via_api(
    skill: str,
    project_dir: Path,
    prompt: str,
    uses_staging: bool = False,
) -> DispatchResult:
    """Execute a skill via OpenAI-compatible API.

    Configure via environment variables:
    - ``SHENBI_LLM_API_KEY`` (required)
    - ``SHENBI_LLM_BASE_URL`` (default: https://api.openai.com/v1)
    - ``SHENBI_LLM_MODEL`` (default: gpt-4o)
    """
    from openai import OpenAI

    chapter = _extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill, project_dir, prompt, chapter, uses_staging=uses_staging
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
            temperature=_API_TEMPERATURE,
            max_tokens=_API_MAX_TOKENS,
        )
    except Exception as exc:
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")

    output_text = response.choices[0].message.content or ""
    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)

    written = _write_parsed_outputs(
        output_text, output_paths, project_dir, create_truth_templates=True
    )
    if not written:
        return DispatchResult(False, -1, "", "No output files written")

    missing = [p for p in output_paths if "*" not in p and not (project_dir / p).exists()]
    if missing:
        log.error("api_missing_outputs", skill=skill, missing=missing)

    return DispatchResult(True, 0, output_text, "")


def _find_ide_cli() -> list[str] | None:
    """Return command parts for available IDE CLI, or None.

    Prompt is fed via stdin (``-`` as the prompt argument).
    Note: flags are codex-specific. zcode support requires separate testing.
    """
    for cli_name in ("codex", "zcode"):
        if shutil.which(cli_name):
            return [
                cli_name,
                "exec",
                "--skip-git-repo-check",
                "-c",
                "sandbox_permissions=workspace-write",
                "-C",
                "{dir}",
                "-",
            ]
    return None


def _dispatch_via_ide(
    skill: str,
    project_dir: Path,
    prompt: str,
    uses_staging: bool = False,
) -> DispatchResult:
    """Execute a skill via an IDE agent CLI (codex / zcode).

    Builds a complete prompt, spawns the IDE agent, parses the multi-file
    response, and writes per-file output to the project directory.
    """
    chapter = _extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill, project_dir, prompt, chapter, uses_staging=uses_staging
        )
    except Exception as exc:
        return DispatchResult(False, -1, "", f"Prompt build failed: {exc}")

    cli_parts = _find_ide_cli()
    if not cli_parts:
        return DispatchResult(False, -1, "", "No IDE CLI found on PATH")

    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    cmd = [p.replace("{dir}", str(project_dir)) for p in cli_parts]

    log.info("ide_dispatch_start", skill=skill, cmd=cmd[0], chapter=chapter)
    try:
        r = subprocess.run(
            cmd, input=full_prompt, capture_output=True, text=True, timeout=_IDE_AGENT_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        log.error("ide_timeout", skill=skill)
        return DispatchResult(False, -1, "", f"IDE agent timed out after {_IDE_AGENT_TIMEOUT}s")
    except FileNotFoundError:
        log.error("ide_cli_not_found", cmd=cmd[0])
        return DispatchResult(False, -1, "", f"CLI not found: {cmd[0]}")

    if r.returncode != 0:
        log.error("ide_failed", skill=skill, rc=r.returncode, stderr=r.stderr[:500])
        return DispatchResult(False, r.returncode, r.stdout, r.stderr)

    log.info("ide_dispatch_complete", skill=skill)

    written = _write_parsed_outputs(
        r.stdout, output_paths, project_dir, create_truth_templates=True
    )
    if not written:
        return DispatchResult(False, -1, "", "No output files written")

    missing = [p for p in output_paths if "*" not in p and not (project_dir / p).exists()]
    if missing:
        log.error("ide_missing_outputs", skill=skill, missing=missing)

    return DispatchResult(True, 0, r.stdout, r.stderr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def dispatch_skill(
    skill: str,
    project_dir: Path | str,
    prompt: str,
    test_type: str = "generative",
    round_dir: Path | str | None = None,
    timeout: int = 900,
    skip_reads: list[str] | None = None,
    uses_staging: bool = False,
) -> DispatchResult:
    """Dispatch a skill for execution.

    Routing (tried in order):
    1. ``SHENBI_LLM_API_KEY`` set → OpenAI-compatible API
    2. IDE CLI available (codex / zcode) → spawn agent subprocess
    3. Fallback → ``shenbi-dispatch`` CLI subprocess
    """
    pd = Path(project_dir)

    # API path
    if os.environ.get(_ENV_LLM_API_KEY):
        return _dispatch_via_api(skill, pd, prompt, uses_staging=uses_staging)

    # IDE CLI path
    if _find_ide_cli():
        return _dispatch_via_ide(skill, pd, prompt, uses_staging=uses_staging)

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
    if r.returncode != 0:
        log.error(
            "dispatch_subprocess_failed",
            skill=skill,
            rc=r.returncode,
            stderr_preview=r.stderr[:2000] if r.stderr else "(empty)",
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
    """Run G3 (scoring independence) check."""
    rd = Path(round_dir)
    pp = rd / "progress.json"
    if not pp.exists():
        safe_write(
            pp,
            json.dumps(
                {
                    "current_scorer_agent": f"pipeline-g3-scorer-{uuid4().hex[:12]}",
                    "scoring_history": [{"agent": "pipeline-skill-generator", "g2_passed": True}],
                },
                indent=2,
            ),
        )
        log.info("progress_json_created_for_g3", skill=skill, path=str(pp))

    cmd = [sys.executable, "-m", "shenbi.gates.cli", "G3", skill, "generative", str(rd)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        log.error("g3_timeout", skill=skill)
        return {"status": GateStatus.FAIL, "error": "G3 timed out"}
    try:
        return json.loads(r.stdout)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"status": GateStatus.FAIL, "error": "unparseable G3 output", "stderr": r.stderr}
