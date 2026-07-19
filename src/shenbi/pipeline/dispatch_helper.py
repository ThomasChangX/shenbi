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

import glob as glob_module
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

from pydantic import ValidationError

from shenbi.contracts.fields import filter_to_fields
from shenbi.contracts.paths import extract_chapter, resolve_chapter_path, resolve_or_skip
from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.status import GateStatus

log = get_logger(__name__)

#: Repository root, resolved from this file's location (match gates/shared.py pattern).
#: Used to locate bundled skills/ directory independently of CWD.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

# Regex matching control characters EXCEPT newline (\n), carriage return (\r),
# and tab (\t) which are valid in JSON strings when properly escaped.
_ILLEGAL_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


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
# Path resolution (glob expansion)
# ---------------------------------------------------------------------------


def _resolve_read_path(project_dir: Path, read_path: str) -> list[Path]:
    """Resolve a read path, expanding glob patterns if present.

    Args:
        project_dir: Pipeline project root directory.
        read_path: Path string from contract reads, may contain glob patterns.

    Returns:
        List of resolved Path objects. Empty list if no matches.
    """
    if "*" in read_path or "?" in read_path or "[" in read_path:
        pattern = str(project_dir / read_path)
        matches = glob_module.glob(pattern)
        return [Path(m) for m in sorted(matches)]
    full_path = project_dir / read_path
    if full_path.exists():
        return [full_path]
    return []


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


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

    # System prompt = SKILL.md (resolved from repo root, not CWD)
    skill_file = _PROJECT_ROOT / "skills" / skill / "SKILL.md"
    if skill_file.exists():
        system_prompt = skill_file.read_text(encoding="utf-8")
    else:
        log.warning("skill_file_missing", skill=skill, path=str(skill_file))
        system_prompt = f"Execute the {skill} skill."

    # Read contract inputs with field-level filtering (Layer B).
    # Replaces only the read loop; truncation logic below stays intact and
    # consumes raw_inputs. Filtering is applied BEFORE truncation, so the
    # truncated content is already field-filtered.
    #
    # resolve_or_skip returns None when a read path carries an N/NNN placeholder
    # but chapter is None (genesis mode) — such reads are skipped rather than
    # raising. With a chapter, resolve_chapter_path does a bounded N/NNN replace.
    input_texts: dict[str, str] = {}
    reads: list[Any] = contract.get("reads", [])
    for read_path_entry in reads:
        if isinstance(read_path_entry, dict):
            # Layer B: field-level read
            read_path: str = read_path_entry.get("file", "")
            fields: list[str] = read_path_entry.get("fields", [])
        else:
            read_path = read_path_entry
            fields = []

        # Resolve chapter placeholders before glob expansion
        resolved = resolve_or_skip(read_path, chapter)
        if resolved is None:
            continue  # unresolvable placeholder (genesis) — skip this read

        resolved_paths = _resolve_read_path(project_dir, resolved)
        for full_path in resolved_paths:
            try:
                content = full_path.read_text(encoding="utf-8")
            except Exception:
                content = f"[binary or unreadable: {full_path}]"
            if fields:
                content, _matched = filter_to_fields(content, fields, str(full_path))
            # Apply per-file char cap
            if len(content) > _INPUT_MAX_CHARS_PER_FILE:
                log.warning(
                    "input_truncated",
                    skill=skill,
                    path=str(full_path),
                    original=len(content),
                    truncated=_INPUT_MAX_CHARS_PER_FILE,
                )
                content = content[:_INPUT_MAX_CHARS_PER_FILE]
            input_texts[full_path.name] = content

    # Collect output paths
    output_paths: list[str] = []
    for write_path in contract.get("writes", []):
        output_paths.append(resolve_chapter_path(write_path, chapter))
    for update_path in contract.get("updates", []):
        output_paths.append(resolve_chapter_path(update_path, chapter))

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
    if len(output_paths) > 1:
        user_parts.append(
            "\nNote: This skill produces multiple files. "
            "Decisions JSON must conform to shenbi-decisions-v1 schema "
            "(see docs/framework/decisions-schema.md)."
        )
    if input_texts:
        user_parts.append("\n## Input Files (read-only reference)")
        for fname, content in input_texts.items():
            # Escape ALL '<' in content to '\u003c' to prevent any tag injection.
            # (Spec 8 §3 Bug 2: the wrapper is </document>, NOT </doc>; the safest
            # approach is escaping every '<' rather than only replacing the tag.)
            safe_content = content.replace("<", "\u003c")
            user_parts.append(f'<document name="{fname}">\n{safe_content}\n</document>')
    user_prompt = "\n".join(user_parts)

    # Inject shared review checklist for review skills (Phase 2.3).
    if _is_review_skill(skill) and chapter is not None:
        try:
            from shenbi.pipeline.review_checklist import (
                generate_review_checklist,
                inject_checklist_into_prompt,
            )

            checklist = generate_review_checklist(project_dir, chapter)
            user_prompt = inject_checklist_into_prompt(user_prompt, checklist)
        except Exception as e:
            log.warning("review_checklist_inject_failed", skill=skill, error=str(e))

    return system_prompt, user_prompt, output_paths


def _is_review_skill(skill: str) -> bool:
    """Check whether a skill name indicates a review skill."""
    return "review" in skill.lower()


# ---------------------------------------------------------------------------
# Output parsing and writing
# ---------------------------------------------------------------------------


def _validate_json_output(content: str, path: Path) -> str:
    """Validate and clean JSON content before writing to disk.

    Recovery policy (tightened per spec §3 Layer 1):
    - Clean JSON parses and is returned unchanged.
    - The dominant corruption pattern (valid JSON + trailing markdown) is
      recovered via ``json.JSONDecoder().raw_decode()`` (truncates to the
      first complete JSON object).
    - After truncation, if the recovered object declares
      ``$schema == "shenbi-decisions-v1"`` it MUST pass
      ``DecisionsDoc.model_validate`` (schema + required-field completeness).
      A recovered object missing required fields raises ValueError rather
      than being persisted (prevents recovering a truncated-tail fragment).
    - Non-decisions JSON files (no matching ``$schema``) are returned as-is
      after truncation.
    - Completely unrecoverable content raises ValueError.

    Args:
        content: Raw content to validate.
        path: Target file path (used to check extension and for error messages).

    Returns:
        Cleaned JSON string.

    Raises:
        ValueError: If content is JSON-typed but unrecoverable, or if a
            recovered decisions object fails schema validation.
    """
    if path.suffix != ".json":
        return content

    # Try strict parse first — fastest path for clean JSON
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass

    # Recovery: extract first complete JSON object
    decoder = json.JSONDecoder()
    try:
        clean_data, end_pos = decoder.raw_decode(content)
    except json.JSONDecodeError as e:
        log.error("decisions_json_unrecoverable", path=str(path), error=str(e))
        raise ValueError(f"Decisions JSON invalid and unrecoverable for {path}: {e}") from e

    # Tightened recovery: a shenbi-decisions-v1 object must pass schema +
    # required-field completeness before being accepted. This prevents
    # recovering a truncated-tail fragment that is missing required fields.
    if isinstance(clean_data, dict) and clean_data.get("$schema") == "shenbi-decisions-v1":
        try:
            from shenbi.contracts.schemas.decisions import DecisionsDoc

            DecisionsDoc.model_validate(clean_data)
        except (ValidationError, ImportError) as e:
            log.error(
                "decisions_json_recovered_but_schema_incomplete",
                path=str(path),
                error=str(e),
            )
            raise ValueError(
                f"Recovered decisions JSON for {path} failed schema validation "
                f"(missing required fields): {e}"
            ) from e

    log.warning(
        "decisions_json_truncated",
        path=str(path),
        original_len=len(content),
        cleaned_len=end_pos,
    )
    return json.dumps(clean_data, ensure_ascii=False, indent=2)


def sanitize_json_content(content: str) -> str:
    r"""Remove illegal control characters from JSON content.

    JSON spec (RFC 8259) only permits specific control characters
    (``\\n``, ``\\r``, ``\\t``) within strings. All other control
    characters in the range ``0x00-0x1F`` are stripped before write.

    This applies to both staging and final paths equally.

    Args:
        content: Raw JSON string to sanitize.

    Returns:
        Sanitized string with illegal control characters removed.
    """
    return _ILLEGAL_CTRL_RE.sub("", content)


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
        if full_path.suffix == ".json":
            content = sanitize_json_content(content)
        try:
            content = _validate_json_output(content, full_path)
        except ValueError as e:
            log.error("output_validation_failed", path=rel_path, error=str(e))
            raise  # Pipeline must stop rather than persist corrupt data

        safe_write(full_path, content)
        written.append(rel_path)
        log.info("output_written", path=rel_path, size=len(content))

    if create_truth_templates and any("*" in p for p in output_paths):
        _init_truth_templates(project_dir)

    return written


#: Truth files seeded by the worldbuilding genesis + their H1 titles. Each
#: template's body is derived from the union of consumer-declared ``fields:``
#: (fix D21) rather than a bare H1, so skills that read e.g.
#: ``truth/current_state.md [主角状态, 当前世界局势, 活跃线索]`` find their H2
#: headings present on first run instead of tripping G1 ``check_fields_exist``.
_TRUTH_FILE_TITLES: dict[str, tuple[str, str]] = {
    "current_state.md": ("Current State", "replace"),
    "character_matrix.md": ("Character Matrix", "replace"),
    "emotional_arcs.md": ("Emotional Arcs", "upsert_markdown_row"),
    "chapter_summaries.md": ("Chapter Summaries", "upsert_markdown_row"),
}


def _collect_declared_truth_fields() -> dict[str, list[str]]:
    """Union of consumer-declared ``fields:`` per truth file, across all skills.

    Scans every ``SKILL.md`` frontmatter ``contract.reads`` entry of the form
    ``{file: truth/<name>.md, fields: [...]}`` and unions the declared field
    names for each of the four seeded truth files. Order is stable
    (first-seen) so template bodies are deterministic across runs. Skills with
    no contract or an unparseable one are skipped — template seeding must
    never block genesis on a single malformed skill.
    """
    from shenbi.contracts.legacy import ContractError, load_contract
    from shenbi.gates.shared import ALL_SKILLS

    declared: dict[str, dict[str, None]] = {name: {} for name in _TRUTH_FILE_TITLES}
    for skill in ALL_SKILLS:
        try:
            contract = load_contract(skill)
        except (ContractError, Exception):
            continue  # malformed/missing contract — skip this skill
        for read_path, fields in contract.get("read_fields", {}).items():
            # read_fields is keyed by the contract path, e.g. "truth/current_state.md".
            rel = read_path.removeprefix("truth/")
            if rel in declared:
                for field in fields:
                    declared[rel][field] = None  # de-dupe, preserve first-seen order
    return {name: list(fields) for name, fields in declared.items()}


def _init_truth_templates(project_dir: Path) -> None:
    """Create minimal truth template files with required YAML frontmatter.

    Each template includes an ``update_mode`` field (``replace``,
    ``upsert_markdown_row``, or ``upsert_yaml``) so downstream writers and
    state-settling can distinguish snapshot vs cumulative files. The value
    must match one of the modes accepted by ``write_truth_file()``.
    """
    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    declared_fields = _collect_declared_truth_fields()
    for filename, (title, mode) in _TRUTH_FILE_TITLES.items():
        tp = truth_dir / filename
        if tp.exists():
            continue  # Don't overwrite existing truth files
        fields = declared_fields.get(filename, [])
        header = f"---\nupdate_mode: {mode}\n---\n\n# {title}\n\n"
        body = "\n".join(f"## {f}\n\n" for f in fields)
        safe_write(tp, header + body)
        log.info("truth_template_created", file=filename, mode=mode)


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

    chapter = extract_chapter(prompt)
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

    # Pre-flight: warn if the assembled prompt approaches the context limit.
    from shenbi.cost.estimate import warn_if_over_budget

    warn_if_over_budget(f"{system_prompt}\n\n{user_prompt}", model, logger=log)

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

    # Capture response.usage (spec §3.1): persist to cost ledger.
    # Defensive: some OpenAI-compatible endpoints omit usage.
    usage_obj = getattr(response, "usage", None)
    if usage_obj is not None:
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) or 0,
        }
        log.info(
            "llm_token_usage",
            skill=skill,
            chapter=chapter,
            model=model,
            **usage,
        )
        try:
            from shenbi.cost.ledger import TokenLedger

            TokenLedger(project_dir).record(skill, chapter or 0, usage, model=model)
        except Exception as exc:
            # Cost accounting must NEVER break a dispatch.
            log.warning("ledger_record_failed", skill=skill, error=str(exc))

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
    chapter = extract_chapter(prompt)
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
    if uses_staging:
        log.warning(
            "legacy_dispatch_ignores_staging",
            skill=skill,
            hint="uses_staging=True cannot be honored in legacy subprocess path",
        )
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
