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
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from shenbi.contracts.fields import filter_to_fields
from shenbi.contracts.paths import extract_chapter, resolve_chapter_path, resolve_or_skip
from shenbi.logging import get_logger
from shenbi.exceptions import DispatchWriteFailureError
from shenbi.pipeline.llm_output_integrity import (
    RETRY_WRITE_CONFIRMATION,
    check_audit_completeness,
    check_audit_line_refs,
    check_markdown_fence_balance,
    check_prose_leakage,
    detect_write_failure,
)
from shenbi.safe_write import safe_write
from shenbi.status import GateStatus

# write_truth_file is imported so tests can verify it is NOT routed through
# the generic dispatch write path. Truth-file append/upsert is the CALLER's
# responsibility (the state-settling skill calls write_truth_file directly).
# Imported but never called in this module.
from shenbi.pipeline.truth_io import write_truth_file  # noqa: F401  # pyright: ignore[reportUnusedImport]

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
#: Externalised per-skill temperature/max_tokens configuration.
#: Loaded from executor_config.toml at project root (Spec 6 §5.4).

_executor_config_cache: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Dynamic timeout (Task 14 — all 3 dispatch paths)
# ---------------------------------------------------------------------------


def _compute_dispatch_timeout(
    skill_name: str,
    chapter_path: Path | None = None,
) -> int:
    """Compute adaptive dispatch timeout based on chapter size.

    base = 300s (5 min)
    extra = 30s per KB of chapter size
    cap = 1800s (30 min)
    state-settling gets 2x multiplier.

    Applied to ALL THREE dispatch paths (CLI subprocess, API, IDE-CLI).
    """
    base = 300
    extra = 0

    if chapter_path and chapter_path.exists():
        chapter_size_kb = chapter_path.stat().st_size / 1024
        extra = int(chapter_size_kb * 30)

    timeout = min(base + extra, 1800)

    # state-settling is the heaviest step -- double timeout
    if skill_name == "shenbi-state-settling":
        timeout = min(int(timeout * 2.0), 1800)

    return timeout


def _handle_timeout_gracefully(skill_name: str, chapter: int | None) -> None:
    """Graceful degradation on timeout.

    Save partial LLM output, log WARN (not HARD failure).
    """
    log.warning(
        "dispatch_timeout", skill=skill_name, chapter=chapter, resolution="saving_partial_output"
    )
    # Reuse previous truth file versions for incomplete updates
    # This is logged for observability; actual handling depends on skill


def _load_executor_config() -> dict[str, Any]:
    """Load executor_config.toml, caching in memory."""
    if _executor_config_cache:
        return _executor_config_cache[0]
    config_path = _PROJECT_ROOT / "executor_config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            _executor_config_cache.append(tomllib.load(f))
    else:
        _executor_config_cache.append({})
    return _executor_config_cache[0]


# ---------------------------------------------------------------------------
# 10a: META block stripping for non-drafting LLM calls
# ---------------------------------------------------------------------------

_META_PATTERN = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)


def _strip_meta_for_non_drafting(skill_name: str, text: str) -> str:
    """Strip META blocks from chapter text for non-drafting LLM calls.

    Only drafting and revision skills need META blocks.
    All other skills (auditors, state-settling, etc.) receive stripped text.
    Saves 16-31% input per non-drafting call.
    """
    if skill_name in ("shenbi-chapter-drafting", "shenbi-chapter-revision"):
        return text
    return _META_PATTERN.sub("", text)


# ---------------------------------------------------------------------------
# 10b: Genre-config per-chapter cache
# ---------------------------------------------------------------------------

_genre_config_cache: dict[int, dict[str, Any]] = {}


def _load_genre_config_cached(project_dir: Path, chapter: int) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """Load genre-config.json with per-chapter cache. ~7 disk I/O -> 1."""
    if chapter in _genre_config_cache:
        return _genre_config_cache[chapter]
    config_path = project_dir / "config" / "genre-config.json"
    config: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    _genre_config_cache[chapter] = config
    return config


def _get_skill_temperature(skill_name: str) -> float:
    """Get temperature for a skill from executor_config.toml."""
    config = _load_executor_config()
    overrides = config.get("overrides", {})
    if skill_name in overrides:
        return float(
            overrides[skill_name].get(
                "temperature", config.get("default", {}).get("temperature", 0.7)
            )
        )
    return float(config.get("default", {}).get("temperature", 0.7))


def _get_skill_max_tokens(skill_name: str) -> int:
    """Get max_tokens for a skill from executor_config.toml."""
    config = _load_executor_config()
    overrides = config.get("overrides", {})
    if skill_name in overrides:
        return int(
            overrides[skill_name].get(
                "max_tokens", config.get("default", {}).get("max_tokens", 16384)
            )
        )
    return int(config.get("default", {}).get("max_tokens", 16384))


_INPUT_MAX_CHARS_PER_FILE = 32000  # hard cap per input file (~8K tokens)
_INPUT_MAX_CHARS_TOTAL = 128000  # total input budget (~32K tokens)

# ---------------------------------------------------------------------------
# Priority-driven context budget allocation
# ---------------------------------------------------------------------------


class _Priority:
    """Priority weight constants for budgeted truncation."""

    HIGH: float = 1.0
    MEDIUM: float = 0.5
    LOW: float = 0.2


_FILE_PRIORITY_WEIGHTS: dict[str, float] = {
    # HIGH priority (1.0) — essential for task completion
    "chapter": 1.0,
    "chapter-current": 1.0,
    "chapter-plan": 1.0,
    # MEDIUM-HIGH (0.8) — strongly influences output quality
    "volume_map": 0.8,
    "character_matrix": 0.8,
    "world_rules": 0.8,
    "current_state": 0.8,
    # MEDIUM (0.5) — provides important context
    "style_profile": 0.5,
    "pending_hooks": 0.5,
    "review_checklist": 0.5,
    "current_focus": 0.5,
    # LOW (0.2) — supplementary, can be heavily truncated
    "archive": 0.2,
    "snapshot": 0.2,
    "default": 0.5,
}


def _get_priority(filename: str) -> float:
    """Get priority weight for a filename based on keyword matching.

    Checks explicit path prefixes first to avoid substring misclassification
    (e.g., ``audits/chapter-1-anti-ai.md`` must not match the ``audit`` key
    and return LOW when it contains ``chapter`` in its name).
    """
    # Explicit path-prefix checks (avoid substring false matches)
    if filename.startswith("audits/"):
        return _Priority.LOW
    if "chapter" in filename.lower():
        return _Priority.HIGH
    # Fall back to keyword matching for remaining entries
    for key, weight in _FILE_PRIORITY_WEIGHTS.items():
        if key in filename.lower():
            return weight
    return _FILE_PRIORITY_WEIGHTS["default"]


def _budgeted_truncate(input_texts: dict[str, str], budget: int) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
    """Truncate input texts to fit within budget, preserving high-priority content.

    Uses weighted allocation: high-priority files get proportionally more budget.
    """
    if not input_texts:
        return {}

    # Calculate total weight
    weights = {name: _get_priority(name) for name in input_texts}
    total_weight = sum(weights.values())

    # Allocate budget proportionally by weight
    result: dict[str, str] = {}
    for name, content in input_texts.items():
        allocation = int(budget * weights[name] / total_weight)
        if len(content) <= allocation:
            result[name] = content
        else:
            result[name] = content[:allocation] + f"\n\n[... truncated from {len(content)} chars]"
        # Enforce per-file character ceiling
        result[name] = result[name][:_INPUT_MAX_CHARS_PER_FILE]

    return result


# Regex matching control characters EXCEPT newline (\n), carriage return (\r),
# and tab (\t) which are valid in JSON strings when properly escaped.
_ILLEGAL_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class FileOutput(BaseModel):
    """A single file output from a structured LLM response."""

    path: str
    content: str


class SkillOutput(BaseModel):
    """Structured output from a skill execution (JSON mode primary format)."""

    files: list[FileOutput] = []
    decisions: dict[str, Any] | None = None


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


def build_retry_feedback(exc: BaseException) -> str:
    """Build the retry-prompt feedback for a failed dispatch.

    For :class:`DispatchWriteFailureError` the feedback is the write-capability
    confirmation quoting the matched signature, so the model stops emitting
    sandbox diagnostics. For any other exception, a generic message is used.
    """
    if isinstance(exc, DispatchWriteFailureError):
        return RETRY_WRITE_CONFIRMATION.format(signature=exc.signature)
    return f"Previous attempt failed: {exc}. Retry, producing the complete output."


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


def _wildcard_to_regex(pattern: str) -> str:
    r"""Convert a glob-style pattern to a regex pattern string.

    'characters/major/*.md' -> '^characters/major/[^/]*\\.md$'
    """
    escaped = re.escape(pattern)
    # Replace escaped \* with a non-slash wildcard
    return "^" + escaped.replace(r"\*", r"[^/]*") + "$"


def _resolve_wildcard_path(
    contract_pattern: str,
    concrete_path: str,
    base_dir: Path | None = None,
) -> bool:
    """Check if concrete_path matches contract_pattern and ensure parent dirs exist.

    Returns True if the path matches and directories were handled.
    Returns False if the path does not match the pattern.

    contract_pattern examples:
        'characters/major/*.md'
        'characters/minor/*.md'

    When a match is found, all intermediate directories are created so the
    caller can safely write the file.
    """
    regex = re.compile(_wildcard_to_regex(contract_pattern))

    p = Path(concrete_path)
    if base_dir is not None and not p.is_absolute():
        p = base_dir / p

    # Compute the relative path for pattern matching.
    # If base_dir is provided, match against the path relative to base_dir.
    if base_dir is not None:
        try:
            match_path = str(p.relative_to(base_dir))
        except ValueError:
            # concrete_path is not under base_dir — cannot match
            return False
    else:
        match_path = concrete_path

    # Normalize path separator
    normalized = match_path.replace("\\", "/")

    if not regex.match(normalized):
        return False

    p.parent.mkdir(parents=True, exist_ok=True)
    return True


def _resolve_all_wildcards(
    contract_writes: list[str],
    concrete_path: str,
    base_dir: Path | None = None,
) -> list[str]:
    """Return the list of contract patterns that match concrete_path.

    For each matching pattern, ensure directories exist.
    """
    matching: list[str] = []
    for pattern in contract_writes:
        if "*" in pattern or "?" in pattern:
            if _resolve_wildcard_path(pattern, concrete_path, base_dir):
                matching.append(pattern)
        else:
            # Literal match: compare against the relative path if base_dir set
            if base_dir is not None:
                p = Path(concrete_path)
                if not p.is_absolute():
                    p = base_dir / p
                try:
                    rel = str(p.relative_to(base_dir))
                except ValueError:
                    continue
            else:
                rel = concrete_path
            if pattern in rel or rel.endswith(pattern):
                matching.append(pattern)
    return matching


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
    uses_staging: bool = False,
    shared_context: Any = None,
    json_mode: bool = False,
) -> tuple[str, str, list[str]]:
    """Build a complete execution prompt for a skill.

    Returns (system_prompt, user_prompt, output_paths) where:
    - system_prompt: SKILL.md content
    - user_prompt: task description + input file contents + output format
    - output_paths: resolved contract writable paths (prefixed with staging/
      when uses_staging=True)

    Args:
        skill: The skill name (e.g. 'shenbi-review-anti-ai').
        project_dir: Pipeline project root directory.
        prompt: The task prompt describing what to do.
        chapter: Chapter number, or None for genesis mode.
        uses_staging: If True, prefix output paths with staging/.
        shared_context: Optional SharedAuditContext with pre-extracted fields
            (world_rules, character_list, style_profile, pending_hooks). When
            provided, cached fields are injected into input_texts so auditors
            skip re-reading those files from disk.
        json_mode: If True, output format instructions request JSON
            (SkillOutput schema) instead of ### FILE: markers. Used by the
            API dispatch path with ``response_format={"type": "json_object"}``.
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
    # Filtering is applied BEFORE truncation, so the truncated content is
    # already field-filtered.
    #
    # resolve_or_skip returns None when a read path carries an N/NNN placeholder
    # but chapter is None (genesis mode) — such reads are skipped rather than
    # raising. With a chapter, resolve_chapter_path does a bounded N/NNN replace.
    raw_inputs: dict[str, str] = {}
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
            # 10a: Strip META blocks for non-drafting skills (save 16-31% input)
            content = _strip_meta_for_non_drafting(skill, content)
            raw_inputs[full_path.name] = content

    # Inject cached fields from shared_context so auditors skip re-reading
    # those files from disk (Task 6 Step 2 wiring).
    if shared_context is not None:
        _INJECT_FROM_CACHE: dict[str, str] = {}
        if getattr(shared_context, "world_rules", ""):
            _INJECT_FROM_CACHE["world_rules.md"] = shared_context.world_rules
        if getattr(shared_context, "character_list", ""):
            _INJECT_FROM_CACHE["character_matrix.md"] = shared_context.character_list
        if getattr(shared_context, "style_profile", ""):
            _INJECT_FROM_CACHE["style_profile.md"] = shared_context.style_profile
        if getattr(shared_context, "pending_hooks", ""):
            _INJECT_FROM_CACHE["pending_hooks.md"] = shared_context.pending_hooks
        for fname, cached in _INJECT_FROM_CACHE.items():
            if cached:
                raw_inputs[fname] = cached

    # Priority-weighted budgeted truncation (Task 4/6 wiring).
    # Replaces the old equal-weight proportional budget with priority-driven
    # allocation via _budgeted_truncate.
    input_texts: dict[str, str] = {}
    if not raw_inputs:
        input_texts = {}
    else:
        total_raw = sum(len(v) for v in raw_inputs.values())
        if total_raw > _INPUT_MAX_CHARS_TOTAL:
            log.warning(
                "input_over_budget_applying_priority_truncation",
                skill=skill,
                total_chars=total_raw,
                budget=_INPUT_MAX_CHARS_TOTAL,
            )
            input_texts = _budgeted_truncate(raw_inputs, _INPUT_MAX_CHARS_TOTAL)
            # _budgeted_truncate respects _INPUT_MAX_CHARS_PER_FILE per file via
            # the weights; if a stricter per-file ceiling is still required, cap
            # each result here AFTER budgeted truncation.
        else:
            # Under budget: still enforce the per-file cap.
            input_texts = {
                fname: (
                    text[:_INPUT_MAX_CHARS_PER_FILE]
                    if len(text) > _INPUT_MAX_CHARS_PER_FILE
                    else text
                )
                for fname, text in raw_inputs.items()
            }

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
    ]

    if json_mode:
        user_parts.extend(
            [
                "## Output Format (CRITICAL — output valid JSON only)",
                "Respond with a single JSON object conforming to this schema:",
                "```json",
                "{",
                '  "files": [',
                '    {"path": "path/to/file1.md", "content": "complete file content here"},',
                '    {"path": "path/to/file2.json", "content": "complete file content here"}',
                "  ],",
                '  "decisions": null',
                "}",
                "```",
                "Rules:",
                "- Output ONLY the JSON object — no markdown wrappers, no extra text",
                "- Each file's content must be the COMPLETE file content",
                "- Use the exact file paths listed below",
                "- The response must be parseable by `json.loads()`",
                "",
            ]
        )
    else:
        user_parts.extend(
            [
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
            ]
        )

    user_parts.append("Files to create:")
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

    # Task 13: Inject plan skeleton for shenbi-chapter-planning when volume_map exists.
    if skill == "shenbi-chapter-planning" and chapter is not None:
        vm_path = project_dir / "outline" / "volume_map.md"
        if vm_path.exists():
            try:
                from shenbi.pipeline.plan_skeleton import generate_plan_skeleton

                skeleton = generate_plan_skeleton(project_dir, chapter)
                skeleton_header = "## Plan Skeleton (auto-generated from volume_map.md)\n\n"
                skeleton_footer = (
                    "\n\n---\n\n"
                    "Complete the [LLM]-marked sections above. Pre-filled sections "
                    "are derived from the blueprint and are EDITABLE CONTEXT -- you "
                    "may modify, override, or deviate from them as the story requires. "
                    "Section 5 (Key Decisions) is entirely yours to create.\n\n"
                    "---"
                )
                user_prompt = skeleton_header + skeleton + skeleton_footer + "\n\n" + user_prompt
            except Exception as e:
                log.warning("plan_skeleton_inject_failed", skill=skill, error=str(e))

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


def _inject_instruction_hierarchy(prompt: str) -> str:  # pyright: ignore[reportUnusedFunction]
    """Add 3-tier instruction hierarchy to prompt (Anthropic Context Engineering pattern)."""
    header = """## Instruction Hierarchy

<HARD_CONSTRAINTS>
- These rules CANNOT be violated under any circumstances
- Violation = automatic rejection
</HARD_CONSTRAINTS>

<GUIDELINES>
- Follow these unless there is a compelling creative reason not to
- Deviations must be justified in the decisions JSON
</GUIDELINES>

<REFERENCE>
- This section provides context and examples
- Use for inspiration, not as strict rules
</REFERENCE>

---
"""
    return header + prompt


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


def _parse_structured_output(raw_content: str) -> SkillOutput:
    """Parse LLM response via JSON mode (Pydantic).

    Falls back to ### FILE: regex parsing for CLI backend.
    """
    try:
        return SkillOutput.model_validate_json(raw_content)
    except (ValidationError, json.JSONDecodeError):
        # Fallback: regex parse ### FILE: markers
        return _parse_file_markers(raw_content)


def _parse_file_markers(raw_content: str) -> SkillOutput:
    """Legacy ### FILE: regex fallback parser."""
    files = []
    pattern = re.compile(r"###\s*FILE:\s*(.+?)\n(.*?)(?=###\s*FILE:|\Z)", re.DOTALL)
    for match in pattern.finditer(raw_content):
        files.append(
            FileOutput(
                path=match.group(1).strip(),
                content=match.group(2).strip(),
            )
        )
    return SkillOutput(files=files)


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


# Minimum ratio of new content to original before overwrite is allowed.
# Below this, the write is refused (WARN + skip) to prevent revision metadata
# summaries from overwriting actual chapter prose. This is a DEFENSE-IN-DEPTH
# secondary safety net — the primary fix is the revision write-contract change
# (Spec 2) + the pre-revision backup (Task 1).
_CONTENT_SIZE_MIN_RATIO = 0.20


def _check_content_size_guard(
    project_dir: Path,
    rel_path: str,
    new_content: str,
) -> tuple[bool, str]:
    """Check if new content is too small compared to existing file.

    Only applies to ``chapters/chapter-N.md`` files (not metadata, audits,
    truth files, or ``-pre-rev.md`` backups). Path matching uses
    ``parent.name``/``name.startswith()`` — NOT ``PurePath.match``, which
    does not handle multi-segment patterns reliably.

    Args:
        project_dir: Root directory of the novel project.
        rel_path: Relative path within the project directory.
        new_content: The new content about to be written.

    Returns:
        A tuple of ``(should_block, reason)``. ``should_block`` is True
        when the write should be refused. ``reason`` is a human-readable
        explanation (empty string if not blocking).
    """
    # Only guard chapter body files: parent dir must be "chapters", name must
    # start with "chapter-" and end with ".md", and must NOT be a -pre-rev
    # backup. Use parent.name/name.startswith() per spec §3.2 (PurePath.match
    # does not handle multi-segment patterns reliably).
    path = Path(rel_path)
    if path.parent.name != "chapters":
        return False, ""
    if not path.name.startswith("chapter-"):
        return False, ""
    if not path.name.endswith(".md"):
        return False, ""
    if path.name.endswith("-pre-rev.md"):
        return False, ""

    full_path = project_dir / rel_path
    if not full_path.exists():
        return False, ""

    original_size = full_path.stat().st_size
    if original_size == 0:
        return False, ""

    new_size = len(new_content)
    ratio = new_size / original_size

    if ratio < _CONTENT_SIZE_MIN_RATIO:
        reason = (
            f"content_too_small: {new_size}B is {ratio:.1%} of "
            f"original {original_size}B (threshold: {_CONTENT_SIZE_MIN_RATIO:.0%})"
        )
        return True, reason

    return False, ""


#: Regex for the chapter-number in an audit filename like
#: ``chapter-32-foreshadowing.md`` or a prose file ``chapter-32.md``.
_CHAPTER_NUM_RE = re.compile(r"chapter-(\d+)")


def _is_audit_file(name: str) -> bool:
    """True iff *name* looks like an audit report (``chapter-NN-<dim>.md``).

    Matches the production layout: audit reports are ``chapter-NN-<dimension>.md``
    (e.g. ``chapter-8-foreshadowing.md``, ``chapter-51-anti-ai.md``). A bare
    ``chapter-NN.md`` (the prose file) is NOT an audit.
    """
    stem = Path(name).stem
    m = _CHAPTER_NUM_RE.match(stem)
    if not m:
        return False
    # stem must have a suffix after the number to be an audit.
    return len(stem) > len(m.group(0))


def _resolve_chapter_for_audit(full_path: Path, project_dir: Path) -> Path:
    """Return the prose chapter file paired with an audit at *full_path*.

    ``audits/chapter-NN-<dim>.md`` -> ``chapters/chapter-NN.md``. Falls back to
    a sibling ``chapter-NN.md`` if the canonical chapters/ dir is absent.
    """
    m = _CHAPTER_NUM_RE.search(full_path.stem)
    if not m:
        return full_path  # caller treats missing file as a no-op
    num = m.group(1)
    canonical = project_dir / "chapters" / f"chapter-{num}.md"
    if canonical.exists():
        return canonical
    return full_path.parent / f"chapter-{num}.md"


def _append_integrity_findings(project_dir: Path, file_path: Path, issues: list[str]) -> None:
    """Persist post-write integrity findings for the G4 checker to read."""
    m = _CHAPTER_NUM_RE.search(file_path.stem)
    num = m.group(1) if m else "unknown"
    out = project_dir / "audits" / f".integrity-findings-{num}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = out.read_text(encoding="utf-8") if out.exists() else ""
    for issue in issues:
        existing += (
            json.dumps(
                {"file": str(file_path.relative_to(project_dir)), "finding": issue},
                ensure_ascii=False,
            )
            + "\n"
        )
    safe_write(out, existing)


def _write_parsed_outputs(
    response: str,
    output_paths: list[str],
    project_dir: Path,
    create_truth_templates: bool = False,
    *,
    skill: str | None = None,
    skip_paths: set[str] | None = None,
    parsed: dict[str, str] | None = None,
) -> list[str]:
    """Parse agent response and write per-file content, honoring no_op_behavior.

    This generic dispatch path writes WHOLE FILES (one ``### FILE: <path>`` block
    per output). It honors only ``no_op_behavior: skip_write`` (paths in
    *skip_paths* are not written). For all declared modes — including
    ``append_dedup`` — it writes the whole file via ``safe_write``.

    Truth-file append/upsert (``mode: append_dedup``) is NOT routed here. That
    mode is declared in the contract so G0.16 can verify it, but the upsert
    itself is the CALLER's responsibility: the state-settling skill calls
    ``write_truth_file`` directly with a real semantic key field (``chapter``,
    ``hook_id``, ...). Fabricating a key from raw prose in this generic path
    would be wrong — the key is semantic and only the calling skill knows it.
    ``merge_prose`` content-preservation is likewise enforced by G4 / the caller;
    the dispatch write itself replaces the file.

    Returns list of successfully written paths.
    """
    if parsed is None:
        parsed = _parse_file_outputs(response)
    written: list[str] = []
    skip = skip_paths or set()

    semantics: dict[str, dict[str, Any]] = {}
    if skill is not None:
        try:
            from shenbi.contracts import load_contract

            semantics = load_contract(skill).get("write_semantics", {})
        except Exception:
            semantics = {}  # contract issues surface in G0; never block dispatch here

    # Split output_paths into literal and wildcard
    literal_paths = [p for p in output_paths if "*" not in p and "?" not in p]
    wildcard_patterns = [p for p in output_paths if "*" in p or "?" in p]

    def _write_one(rel_path: str, content: str) -> None:
        """Write a single output file with validation, write-failure detection,
        and size guard. After writing, runs post-write integrity checks
        (prose leakage, fence balance, audit completeness, line-ref skew)
        and logs findings without blocking the write.
        """
        full_path = project_dir / rel_path

        # 1. WRITE-FAILURE DETECTION (pre-write, blocks the write).
        is_failure, signature = detect_write_failure(content)
        if is_failure:
            log.error(
                "dispatch_write_failure_detected",
                path=str(full_path),
                signature=signature,
            )
            raise DispatchWriteFailureError(
                f"LLM reported write failure for {full_path}: '{signature}'. "
                f"The output is a diagnostic message, not file content. Retry "
                f"with explicit write-capability confirmation.",
                signature=signature or "",
            )

        if full_path.suffix == ".json":
            content = sanitize_json_content(content)
        try:
            content = _validate_json_output(content, full_path)
        except ValueError as e:
            log.error("output_validation_failed", path=rel_path, error=str(e))
            raise  # Pipeline must stop rather than persist corrupt data

        should_block, reason = _check_content_size_guard(project_dir, rel_path, content)
        if should_block:
            log.warning("write_blocked_content_size_guard", path=rel_path, reason=reason)
            return  # Skip this file, preserve original

        # 2. WRITE.
        safe_write(full_path, content)
        written.append(rel_path)
        mode = semantics.get(rel_path, {}).get("mode")
        log.info("output_written", path=rel_path, size=len(content), mode=mode)

        # 3-6. POST-WRITE INTEGRITY (fixed order; collect all issues).
        issues: list[str] = []
        name = full_path.name
        is_chapter = _CHAPTER_NUM_RE.match(Path(name).stem) is not None and not _is_audit_file(name)
        is_audit = _is_audit_file(name)

        if is_chapter:
            issues += check_prose_leakage(full_path)
            issues += check_markdown_fence_balance(full_path)

        if is_audit:
            issues += check_audit_completeness(full_path)
            chapter_path = _resolve_chapter_for_audit(full_path, project_dir)
            issues += check_audit_line_refs(full_path, chapter_path)

        for issue in issues:
            log.warning("llm_output_integrity_issue", path=str(full_path), finding=issue)
        if issues:
            _append_integrity_findings(project_dir, full_path, issues)

    # Process literal contract paths
    for rel_path in literal_paths:
        if "*" in rel_path:
            continue
        if rel_path in skip:
            log.info("write_skipped_noop", path=rel_path, skill=skill)
            continue
        content = parsed.get(rel_path, parsed.get("__stdout__", ""))
        if not content.strip():
            log.warning("output_empty", path=rel_path)
            continue
        full_path = project_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # NOTE: append_dedup is intentionally NOT branched here. The dispatch
        # path writes whole files; truth-file upsert is the caller's job
        # (state-settling skill calls write_truth_file with a real key).
        _write_one(rel_path, content)

    # Process wildcard paths: check parsed outputs against wildcard patterns
    for rel_path, content in parsed.items():
        if rel_path == "__stdout__":
            continue
        if rel_path in literal_paths:
            continue  # Already handled above
        if rel_path in skip:
            log.info("write_skipped_noop", path=rel_path, skill=skill)
            continue
        matching = _resolve_all_wildcards(wildcard_patterns, rel_path, base_dir=project_dir)
        if matching:
            if not content.strip():
                log.warning("output_empty", path=rel_path)
                continue
            _write_one(rel_path, content)
            log.debug(
                "wildcard_output_matched",
                path=rel_path,
                patterns=matching,
            )

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
# Retry with exponential backoff for LLM API calls
# ---------------------------------------------------------------------------

_RETRYABLE_STATUSES: set[int] = {429, 500, 502, 503, 504}


def _is_retryable(exception: BaseException) -> bool:
    """Determine if an HTTP error is retryable."""
    if isinstance(exception, httpx.TimeoutException):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in _RETRYABLE_STATUSES
    return False


def _call_llm_streaming(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    early_stop_patterns: list[str] | None = None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """Stream LLM response with optional early-stop patterns.

    Returns (collected_text, stop_reason) where stop_reason is None for
    normal completion or a description string for early termination.
    """
    collected: list[str] = []
    stop_reason: str | None = None
    stream = client.chat.completions.create(model=model, messages=messages, stream=True, **kwargs)
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            delta = chunk.choices[0].delta.content
            collected.append(delta)
            if early_stop_patterns:
                text_so_far = "".join(collected)
                for pat in early_stop_patterns:
                    if pat in text_so_far:
                        stop_reason = f"early_stop: matched '{pat[:30]}'"
                        break
                if stop_reason:
                    break
    result = "".join(collected)
    if stop_reason:
        log.info("streaming_early_stop", reason=stop_reason)
    return result, stop_reason


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=30),
    retry=retry_if_exception(_is_retryable),
    before_sleep=lambda retry_state: log.warning(
        "llm_retry",
        attempt=retry_state.attempt_number,
        exception=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
    ),
)
def _call_llm_streaming_with_retry(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    early_stop_patterns: list[str] | None = None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """Stream LLM response with retry on transient failures.

    Retries: 429 (rate limit), 5xx (server errors), timeouts.
    Does NOT retry: 400, 401, 403 (client errors).
    """
    return _call_llm_streaming(
        client,
        model,
        messages,
        early_stop_patterns=early_stop_patterns,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Dispatch paths
# ---------------------------------------------------------------------------


def _dispatch_via_api(
    skill: str,
    project_dir: Path,
    prompt: str,
    uses_staging: bool = False,
    shared_context: Any = None,
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
            skill,
            project_dir,
            prompt,
            chapter,
            uses_staging=uses_staging,
            shared_context=shared_context,
            json_mode=True,
        )
    except Exception as exc:
        return DispatchResult(False, -1, "", f"Prompt build failed: {exc}")

    client = OpenAI(
        api_key=os.environ[_ENV_LLM_API_KEY],
        base_url=os.environ.get(_ENV_LLM_BASE_URL, _DEFAULT_BASE_URL),
    )
    model = os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)

    chapter_path = (
        project_dir / "chapters" / f"chapter-{chapter}.md" if chapter is not None else None
    )
    api_timeout = _compute_dispatch_timeout(skill, chapter_path)

    log.info("api_dispatch_start", skill=skill, model=model, chapter=chapter)

    # Pre-flight: warn if the assembled prompt approaches the context limit.
    from shenbi.cost.estimate import warn_if_over_budget

    warn_if_over_budget(f"{system_prompt}\n\n{user_prompt}", model, logger=log)

    try:
        output_text, stop_reason = _call_llm_streaming_with_retry(
            client,
            model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=_get_skill_temperature(skill),
            max_tokens=_get_skill_max_tokens(skill),
            timeout=api_timeout,
        )
    except Exception as exc:
        _handle_timeout_gracefully(skill, chapter)
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")

    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)
    if stop_reason:
        log.info("api_dispatch_early_stop", skill=skill, stop_reason=stop_reason)

    # Token usage is not available via streaming; cost estimation uses
    # the pre-flight heuristic (warn_if_over_budget above) instead.

    try:
        output = _parse_structured_output(output_text)
        parsed_dict = {f.path: f.content for f in output.files}
        written = _write_parsed_outputs(
            output_text,
            output_paths,
            project_dir,
            create_truth_templates=True,
            skill=skill,
            parsed=parsed_dict,
        )
    except DispatchWriteFailureError as exc:
        log.error(
            "api_write_failure_detected",
            skill=skill,
            signature=exc.signature,
        )
        return DispatchResult(False, -1, "", build_retry_feedback(exc))
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
    shared_context: Any = None,
) -> DispatchResult:
    """Execute a skill via an IDE agent CLI (codex / zcode).

    Builds a complete prompt, spawns the IDE agent, parses the multi-file
    response, and writes per-file output to the project directory.
    """
    chapter = extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill,
            project_dir,
            prompt,
            chapter,
            uses_staging=uses_staging,
            shared_context=shared_context,
        )
    except Exception as exc:
        return DispatchResult(False, -1, "", f"Prompt build failed: {exc}")

    cli_parts = _find_ide_cli()
    if not cli_parts:
        return DispatchResult(False, -1, "", "No IDE CLI found on PATH")

    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    cmd = [p.replace("{dir}", str(project_dir)) for p in cli_parts]

    chapter_path = (
        project_dir / "chapters" / f"chapter-{chapter}.md" if chapter is not None else None
    )
    ide_timeout = _compute_dispatch_timeout(skill, chapter_path)

    log.info("ide_dispatch_start", skill=skill, cmd=cmd[0], chapter=chapter)
    try:
        r = subprocess.run(
            cmd, input=full_prompt, capture_output=True, text=True, timeout=ide_timeout
        )
    except subprocess.TimeoutExpired:
        _handle_timeout_gracefully(skill, chapter)
        log.error("ide_timeout", skill=skill)
        return DispatchResult(False, -1, "", f"IDE agent timed out after {ide_timeout}s")
    except FileNotFoundError:
        log.error("ide_cli_not_found", cmd=cmd[0])
        return DispatchResult(False, -1, "", f"CLI not found: {cmd[0]}")

    if r.returncode != 0:
        log.error("ide_failed", skill=skill, rc=r.returncode, stderr=r.stderr[:500])
        return DispatchResult(False, r.returncode, r.stdout, r.stderr)

    log.info("ide_dispatch_complete", skill=skill)

    try:
        written = _write_parsed_outputs(
            r.stdout,
            output_paths,
            project_dir,
            create_truth_templates=True,
            skill=skill,
        )
    except DispatchWriteFailureError as exc:
        log.error(
            "ide_write_failure_detected",
            skill=skill,
            signature=exc.signature,
        )
        return DispatchResult(False, -1, "", build_retry_feedback(exc))
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
    shared_context: Any = None,
) -> DispatchResult:
    """Dispatch a skill for execution.

    Routing (tried in order):
    1. ``SHENBI_LLM_API_KEY`` set → OpenAI-compatible API
    2. IDE CLI available (codex / zcode) → spawn agent subprocess
    3. Fallback → ``shenbi-dispatch`` CLI subprocess

    Args:
        skill: The skill name to dispatch (e.g. 'shenbi-chapter-drafting').
        project_dir: Pipeline project root directory.
        prompt: The task prompt describing what to generate/audit.
        test_type: Test mode identifier (default 'generative').
        round_dir: Optional round-specific directory for output isolation.
        timeout: Subprocess timeout in seconds (default 900).
        skip_reads: Optional list of read patterns to skip.
        uses_staging: If True, dispatch writes to staging/ first.
        shared_context: Optional SharedAuditContext with pre-extracted fields.
            Passed through to _build_skill_prompt so auditors skip re-reading
            common files from disk.
    """
    pd = Path(project_dir)

    # API path
    if os.environ.get(_ENV_LLM_API_KEY):
        return _dispatch_via_api(
            skill, pd, prompt, uses_staging=uses_staging, shared_context=shared_context
        )

    # IDE CLI path
    if _find_ide_cli():
        return _dispatch_via_ide(
            skill, pd, prompt, uses_staging=uses_staging, shared_context=shared_context
        )

    # Legacy CLI subprocess path
    if uses_staging:
        log.warning(
            "legacy_dispatch_ignores_staging",
            skill=skill,
            hint="uses_staging=True cannot be honored in legacy subprocess path",
        )
    patterns = list(skip_reads or [])
    patterns.extend(OPTIONAL_READS.get(skill, []))

    chapter = extract_chapter(prompt)
    chapter_path = pd / "chapters" / f"chapter-{chapter}.md" if chapter is not None else None
    cli_timeout = _compute_dispatch_timeout(skill, chapter_path)

    rd = str(round_dir) if round_dir else str(project_dir)
    log.info("dispatch_start", skill=skill, test_type=test_type, round_dir=rd)
    env = os.environ.copy()
    if patterns:
        env[_G1_SKIP_ENV_VAR] = ",".join(patterns)
        log.debug("dispatch_skip_reads", skill=skill, patterns=patterns)
    try:
        _run_cmd = ["uv", "run", "shenbi-dispatch", skill, test_type, rd, prompt]
        r = subprocess.run(_run_cmd, capture_output=True, text=True, timeout=cli_timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        _handle_timeout_gracefully(skill, chapter)
        log.error("dispatch_timeout", skill=skill, timeout=cli_timeout)
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


def run_gate_g4(
    skill: str,
    files: list[str],
    project_dir: Path | str,
    chapter: int | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    """Run G4 (skill-specific structural check) after dispatch.

    When *chapter* and *phase* are provided, the result is recorded into the
    pipeline gate manifest via :func:`~shenbi.gates.gate_manifest.record_gate_result`.
    """
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
        result: dict[str, Any] = {"status": GateStatus.FAIL, "error": "G4 timed out"}
        if chapter is not None and phase is not None:
            _record_gate_manifest(Path(project_dir), phase, chapter, skill, "G4", result)
        return result
    try:
        result = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        result = {"status": GateStatus.FAIL, "error": "unparseable G4 output", "stderr": r.stderr}
    if chapter is not None and phase is not None:
        _record_gate_manifest(Path(project_dir), phase, chapter, skill, "G4", result)
    return result


def run_gate_g3(
    skill: str,
    round_dir: Path | str,
    chapter: int | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    """Run G3 (scoring independence) check.

    When *chapter* and *phase* are provided, the result is recorded into the
    pipeline gate manifest via :func:`~shenbi.gates.gate_manifest.record_gate_result`.
    """
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
        result: dict[str, Any] = {"status": GateStatus.FAIL, "error": "G3 timed out"}
        if chapter is not None and phase is not None:
            _record_gate_manifest(rd, phase, chapter, skill, "G3", result)
        return result
    try:
        result = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        result = {"status": GateStatus.FAIL, "error": "unparseable G3 output", "stderr": r.stderr}
    if chapter is not None and phase is not None:
        _record_gate_manifest(rd, phase, chapter, skill, "G3", result)
    return result


def _record_gate_manifest(
    project_dir: Path,
    phase: str,
    chapter: int,
    skill: str,
    gate: str,
    result: dict[str, Any],
) -> None:
    """Record a gate result into the pipeline manifest (best-effort, never raises)."""
    try:
        from shenbi.gates.gate_manifest import record_gate_result

        record_gate_result(
            gate_manifest_dir=project_dir,
            phase=phase,
            chapter=chapter,
            skill=skill,
            gate=gate,
            result=result,
        )
    except Exception:
        log.warning("gate_manifest_record_failed", gate=gate, skill=skill, exc_info=True)
