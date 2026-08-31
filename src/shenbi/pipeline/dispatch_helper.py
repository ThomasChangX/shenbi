"""Dispatch + gate helpers for pipeline orchestrators.

Tier B write audit (C32 R3 / F518): ALL THREE dispatch routes below are
audited — routes 1 (API) and 2 (IDE CLI) wrap every dispatch with
``_with_write_audit`` (pre/post FS snapshot + ``audit_writes`` + ledger
record, same finally-hook topology as ``dispatch_with_write_audit``); route
3 (legacy CLI subprocess) is audited inside the subprocess by that same
``dispatch_with_write_audit``. The dispatcher runs G1 (input readiness) and
G2 (output structure) on the legacy route; this module adds G3 (scoring
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
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from shenbi.contracts.fields import filter_to_fields
from shenbi.contracts.paths import (
    PathContext,
    format_path_context,
    extract_chapter,
    parse_path_context,
    resolve_contract_path,
    resolve_or_skip_ctx,
)
from shenbi.cost.ledger import TokenLedger
from shenbi.logging import get_logger
from shenbi.exceptions import DispatchWriteFailureError, TruthFileParseError
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
_DEFAULT_MODEL = "deepseek-v4-flash"  # fallback when SHENBI_LLM_MODEL not set
#: Hard ceiling for max_tokens cap-raise (spec §5.1 C1, §7 iron rule #2).
#: The cap-raise on finish_reason=length will not exceed this × 0.9
#: (spec mandates 0.9 safety factor below the ceiling).
#: Must be > drafting's configured max_tokens (32768 after T3) so that
#: int(65536 * 0.9) = 58982 > 32768 and the cap-raise has headroom to fire.
#: If the model's actual output limit is lower, the API will 400 and the
#: error surfaces via the existing except block.
_MODEL_OUTPUT_CEILING = 65536
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
    base = 900
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
    """Log WARN on timeout (not a HARD failure).

    Note: no partial output is saved here — the streaming callback persists
    chunks as they arrive, so a timeout keeps whatever already landed (F395).
    """
    log.warning(
        "dispatch_timeout",
        skill=skill_name,
        chapter=chapter,
        resolution="partial_output_already_persisted_by_streaming",
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


def load_executor_config() -> dict[str, Any]:
    """Public accessor (spec #33 T1a): helper_injection reads the cached config."""
    return _load_executor_config()


# ---------------------------------------------------------------------------
# 10a: META block stripping for non-drafting LLM calls
# ---------------------------------------------------------------------------

from shenbi.gates.shared import META_BLOCK_RE as _META_PATTERN  # 单源别名（z11 F1301）


def _strip_meta_for_non_drafting(skill_name: str, text: str) -> str:
    """Strip META blocks from chapter text for non-drafting LLM calls.

    Only drafting and revision skills need META blocks.
    All other skills (auditors, state-settling, etc.) receive stripped text.
    Saves 16-31% input per non-drafting call.
    """
    if skill_name in ("shenbi-chapter-drafting", "shenbi-chapter-revision"):
        return text
    return _META_PATTERN.sub("", text)


# Sentinels for the auto-generated body blocks (spec §3.8). These are kept in
# the SKILL.md for codegen traceability + CI idempotency, but they are 100%
# redundant with the frontmatter contract (which the dispatcher already parses
# separately) and should never reach the LLM.
_AUTOGEN_DATA_RE = re.compile(
    r"<!-- AUTO-GENERATED.*?-->\n.*?<!-- END AUTO-GENERATED -->\n?",
    re.DOTALL,
)
_AUTOGEN_CHECK_RE = re.compile(
    r"<!-- AUTO-CHECK-START.*?-->\n.*?<!-- AUTO-CHECK-END -->\n?",
    re.DOTALL,
)


def _strip_autogen_blocks(text: str) -> str:
    """Remove the auto-generated 数据契约 + AUTO-CHECK blocks from a SKILL.md body.

    Spec §3.8: both blocks duplicate frontmatter info (数据契约) or are empty
    placeholders (AUTO-CHECK). Stripping them before the system prompt is sent
    saves ~150-320 chars (data-contract) + ~80 chars (auto-check) per skill per
    dispatch. The blocks remain in SKILL.md for codegen/CI — only the LLM view
    changes.
    """
    text = _AUTOGEN_DATA_RE.sub("", text)
    return _AUTOGEN_CHECK_RE.sub("", text)


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
    # F10 (spec #4 §5.1a): the framework-written audit aggregate may be
    # absent on legacy project dirs — G1 must drop the missing read instead
    # of hard-failing before the reads-loop fallback can substitute the raw
    # glob (executor drops optional non-existent reads pre-G1). Note: this
    # env-gated drop only runs on the legacy subprocess route; the API/IDE
    # routes get the raw-glob substitution via _resolve_read_with_fallback.
    "shenbi-chapter-revision": ["chapter-*.aggregate.md"],
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


#: F10 (spec #4 §5.1a): declared reads produced by the framework aggregate
#: layer. When the aggregate is missing (legacy project dirs), the read
#: fails open to the raw audit glob.
_AGGREGATE_READ_FALLBACK_RE = re.compile(r"^audits/chapter-(\d+)\.aggregate\.md$")


def _resolve_read_with_fallback(project_dir: Path, read_path: str) -> list[Path]:
    """Resolve a read path, failing aggregate reads open to the raw glob."""
    resolved = _resolve_read_path(project_dir, read_path)
    if resolved:
        return resolved
    m = _AGGREGATE_READ_FALLBACK_RE.match(read_path)
    if m:
        log.warning(
            "audit_aggregate_missing_fallback_raw_glob",
            read_path=read_path,
        )
        return _resolve_read_path(project_dir, f"audits/chapter-{m.group(1)}-*.md")
    return []


#: T12-01 (spec #22 R1b): wrapper-breaking characters in wildcard-written
#: filenames are rejected before any mkdir/write happens.
FORBIDDEN_FILENAME_RE = re.compile(r'["<>[\x00-\x1f\\]')


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


def _input_key(full_path: Path, project_dir: Path) -> str:
    """Return the canonical raw_inputs key for a file (spec §3.4).

    Uses the project-relative path (not basename) so two same-named files in
    different directories don't silently overwrite each other. Shared by the
    disk-read loop and the SharedAuditContext injection block so the two never
    produce mismatched keys (spec §6.1 C1 regression guard).
    """
    try:
        return str(full_path.relative_to(project_dir))
    except ValueError:
        # full_path is not under project_dir (defensive); fall back to full str.
        return str(full_path)


def _escape_attr(value: str) -> str:
    """T12-01 (spec #22 R1a): escape a filename for use inside a double-quoted
    XML-ish attribute value. '&' first so entity output is not double-escaped.
    """
    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _build_skill_prompt(
    skill: str,
    project_dir: Path,
    prompt: str,
    chapter: int | None,
    uses_staging: bool = False,
    shared_context: Any = None,
    json_mode: bool = False,
    path_context: PathContext | None = None,
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
        path_context: Optional per-family placeholder context (spec #6 R4).
            When provided, reads/writes resolve arc/stratum/volume/chapter
            families from it instead of the bare chapter number.
    """
    from shenbi.contracts.legacy import ContractError, load_contract, validate_skill_name

    try:
        contract = load_contract(skill)
    except ContractError as exc:
        log.error("contract_load_failed", skill=skill, error=str(exc))
        raise

    # System prompt = SKILL.md (resolved from repo root, not CWD)
    # (load_contract above already routes through _skill_path's validator;
    # this explicit call is belt-and-braces for the local join below.)
    validate_skill_name(skill)
    skill_file = _PROJECT_ROOT / "skills" / skill / "SKILL.md"
    if skill_file.exists():
        system_prompt = _strip_autogen_blocks(skill_file.read_text(encoding="utf-8"))
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

        # Resolve placeholders before glob expansion (ctx-aware, spec #6
        # R4b): resolve_or_skip_ctx routes arc/stratum/volume families via
        # path_context and filters unresolvable placeholders.
        resolved = resolve_or_skip_ctx(read_path, chapter, path_context)
        if resolved is None:
            continue  # unresolvable placeholder (genesis) — skip this read

        resolved_paths = _resolve_read_with_fallback(project_dir, resolved)
        for full_path in resolved_paths:
            try:
                content = full_path.read_text(encoding="utf-8")
            except Exception:
                content = f"[binary or unreadable: {full_path}]"
            if fields:
                content, _matched = filter_to_fields(content, fields, str(full_path))
            # 10a: Strip META blocks for non-drafting skills (save 16-31% input)
            content = _strip_meta_for_non_drafting(skill, content)
            raw_inputs[_input_key(full_path, project_dir)] = content

    # Inject cached fields from shared_context so auditors skip re-reading
    # those files from disk (Task 6 Step 2 wiring). Keys must match the
    # disk-read path's _input_key form (spec §6.1 C1) — basename before was
    # coincidentally consistent; now both use relative paths explicitly.
    if shared_context is not None:
        _INJECT_FROM_CACHE: dict[str, str] = {}
        if getattr(shared_context, "world_rules", ""):
            _INJECT_FROM_CACHE[
                _input_key(project_dir / "truth" / "world_rules.md", project_dir)
            ] = shared_context.world_rules
        if getattr(shared_context, "character_list", ""):
            _INJECT_FROM_CACHE[
                _input_key(project_dir / "truth" / "character_matrix.md", project_dir)
            ] = shared_context.character_list
        if getattr(shared_context, "style_profile", ""):
            _INJECT_FROM_CACHE[
                _input_key(project_dir / "truth" / "style_profile.md", project_dir)
            ] = shared_context.style_profile
        if getattr(shared_context, "pending_hooks", ""):
            _INJECT_FROM_CACHE[
                _input_key(project_dir / "truth" / "pending_hooks.md", project_dir)
            ] = shared_context.pending_hooks
        for fname, cached in _INJECT_FROM_CACHE.items():
            if cached and fname not in raw_inputs:
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
        output_paths.append(resolve_contract_path(write_path, chapter, path_context))
    for update_path in contract.get("updates", []):
        output_paths.append(resolve_contract_path(update_path, chapter, path_context))

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
            user_parts.append(
                f'<document name="{_escape_attr(fname)}">\n{safe_content}\n</document>'
            )
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

    # Inject deterministic helper precompute blocks (spec #33 T1a).
    try:
        from shenbi.pipeline.helper_injection import inject_helper_precompute

        user_prompt = inject_helper_precompute(skill, project_dir, user_prompt)
    except Exception as e:
        log.warning("helper_inject_failed", skill=skill, error=str(e))

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
from shenbi.gates.shared import CHAPTER_NUM_RE as _CHAPTER_NUM_RE  # 单源（z11 F1301）
from shenbi.gates.shared import CHAPTER_HEADER_RE


def ensure_chapter_header(content: str, chapter_num: int) -> str:
    """Insert the contract ``# Chapter N:`` header if missing. Idempotent.

    z11 SDD #20 R1a (F1301): the chapter-file header is a machine-insertable
    contract line; it is normalized on the write path (pre snapshot) and
    enforced gate-side by G2.13 — both share ``CHAPTER_HEADER_RE``.
    """
    first_line = content.lstrip().split("\n", 1)[0]
    if CHAPTER_HEADER_RE.match(first_line):
        return content
    return f"# Chapter {chapter_num}:\n\n" + content


def _is_audit_file(name: str) -> bool:
    """True iff *name* looks like an audit report (``chapter-NN-<dim>.md``).

    Matches the production layout: audit reports are ``chapter-NN-<dimension>.md``
    (e.g. ``chapter-8-foreshadowing.md``, ``chapter-51-anti-ai.md``). A bare
    ``chapter-NN.md`` (the prose file) is NOT an audit.
    """
    stem = Path(name).stem
    # The framework-written aggregate (chapter-N.aggregate.md) is NOT an
    # LLM audit report (spec #4 F10).
    if stem.endswith(".aggregate"):
        return False
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


_TRUTH_DIR_PREFIX = "truth/"
_STAGING_TRUTH_PREFIX = "staging/truth/"


def _increment_units(content: str) -> list[str]:
    """Split a dispatched append_dedup increment into upsert units.

    Each markdown TABLE row line is its own unit, so a multi-row increment
    (e.g. several hooks planted in one chapter) dedups row by row instead of
    being handed to the primitive as one blob whose "key cell" would straddle
    embedded newlines and pipes. Contiguous NON-table lines (section-style
    entries: heading + prose) are grouped into one block unit — they carry no
    key cell, so the primitive appends them verbatim (data-preserving
    fallback, symmetric with the T703 never-drop policy). Blank-only spans
    yield no unit.
    """
    from shenbi.pipeline.truth_io import split_table_cells

    units: list[str] = []
    block: list[str] = []

    def _flush() -> None:
        if any(line.strip() for line in block):
            units.append("\n".join(block).strip("\n"))
        block.clear()

    for line in content.split("\n"):
        if split_table_cells(line) is not None:
            _flush()
            units.append(line)
        else:
            block.append(line)
    _flush()
    return units


#: Staging-write metadata sidecar (SDD #21 R3): records each staged target's
#: update_mode/key_field so the commit side can distinguish keyed-upsert
#: targets (live-priority row merge) from plain whole-file replaces. Lives at
#: the staging ROOT, so the commit-side ``staging/truth/*.md`` glob never
#: picks it up, and ``clear_staging``'s rmtree removes it with the rest.
_STAGING_META_NAME = ".staging-meta.json"


def _staging_meta_path(project_dir: Path) -> Path:
    return project_dir / "staging" / _STAGING_META_NAME


def _update_staging_meta(project_dir: Path, rel_path: str, key_field: str) -> None:
    """Record *rel_path*'s keyed-upsert semantics in the sidecar.

    Read -> dict.update -> write (merge semantics; a second writer must never
    erase the first writer's entries), guarded by the sidecar's own per-path
    lock so concurrent staging writers cannot interleave.
    """
    from shenbi.pipeline.truth_io import path_lock

    meta_path = _staging_meta_path(project_dir)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    # commit targets use the non-staging path form ("truth/<file>")
    target = rel_path[len("staging/") :] if rel_path.startswith("staging/") else rel_path
    with path_lock(meta_path):
        meta: dict[str, dict[str, str]] = {}
        if meta_path.exists():
            try:
                loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    meta = loaded
            except (OSError, ValueError):
                log.warning("staging_meta_unreadable", path=str(meta_path))
        meta[target] = {"update_mode": "append_dedup", "key_field": key_field}
        safe_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))


def _route_append_dedup_write(
    project_dir: Path, rel_path: str, content: str, *, key_field: str
) -> None:
    """Write an ``append_dedup`` increment through the truth_io keyed upsert.

    C3 T2 fix (F360/F828): this dispatch path used to write contract-declared
    append_dedup targets as WHOLE FILES, so cumulative truth data (chapter
    summaries, trend rows, hook rows) collapsed to the latest chapter's
    increment on every dispatch. The skill emits the increment; the program
    merges it by key — the LLM never rewrites the full file.

    Routing:

    - ``truth/<file>`` — each increment unit is upserted via
      ``truth_io.write_truth_file`` (per-path lock, atomic safe_write; key
      from the contract ``key:`` field, key VALUE from the unit's key cell —
      whole-cell, key-column positioned per the T702/T713 fixes).
    - ``staging/truth/<file>`` (checkpoint-gated writers, e.g. state-settling)
      — the increment is merged against the LIVE ``truth/<file>`` as base and
      the merged snapshot is written to the staging path. The staging commit
      is a whole-file replace, so staging must already carry the merged
      content; the live file stays untouched until commit, keeping the
      review/reject rollback (``clear_staging``) clean.
    - anything else — unroutable (truth_io writes under ``truth/`` only):
      fall back to the legacy whole-file write with a WARN.

    Raises:
        TruthFileParseError: not raised by the CURRENT wiring — both routes
            above go through the pure-string ``upsert_markdown_row`` path,
            which never parses existing files as YAML (only ``upsert_yaml``
            can, via ``truth_io._read_yaml_records``). The dispatch entry
            points' ``except TruthFileParseError`` (:func:`_dispatch_via_api`
            / :func:`_dispatch_via_ide`, converting it into a failed
            DispatchResult) stays as defense for a future ``upsert_yaml``
            wiring, not a live path today.
    """
    from shenbi.pipeline.truth_io import path_lock, upsert_markdown_row, write_truth_file

    units = _increment_units(content)

    if rel_path.startswith(_STAGING_TRUTH_PREFIX):
        filename = rel_path[len(_STAGING_TRUTH_PREFIX) :]
        staged = project_dir / rel_path
        staged.parent.mkdir(parents=True, exist_ok=True)
        live_path = project_dir / "truth" / filename
        # SDD #21 R3: the merge base is CHAINED — an existing staging file
        # for the same target is the base (it already carries this chapter's
        # earlier writers' increments); only the FIRST writer falls back to
        # the live file. Merging against live unconditionally let a second
        # parallel writer (state-settling vs foreshadowing-lifecycle) drop
        # the first writer's rows from staging (last-writer-wins, T7-03).
        # The whole read-merge-write runs under the per-path lock
        # (in-process threading; ThreadPoolExecutor is the only concurrency
        # model here — cross-process locking is out of scope).
        with path_lock(staged):
            # Existence check INSIDE the lock: two threads that both see
            # "no staging file yet" would each merge against live and the
            # later safe_write would drop the earlier writer's rows.
            base_is_staging = staged.exists()
            if base_is_staging:
                base = staged.read_text(encoding="utf-8")
            else:
                base = live_path.read_text(encoding="utf-8") if live_path.exists() else ""
            merged = base
            for unit in units:
                merged = upsert_markdown_row(merged, unit, key_field)
            safe_write(staged, merged)
            _update_staging_meta(project_dir, rel_path, key_field)
        log.info(
            "truth_increment_staged",
            path=rel_path,
            key=key_field,
            base=str(staged if base_is_staging else live_path),
            merged_size=len(merged),
        )
        return

    if rel_path.startswith(_TRUTH_DIR_PREFIX):
        filename = rel_path[len(_TRUTH_DIR_PREFIX) :]
        for unit in units:
            write_truth_file(
                project_dir,
                filename,
                unit,
                mode="upsert_markdown_row",
                key_field=key_field,
            )
        return

    log.warning(
        "append_dedup_unroutable_path",
        path=rel_path,
        hint="append_dedup declared outside truth/ — legacy whole-file write",
    )
    safe_write(project_dir / rel_path, content)


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
    per output), with ONE routed exception: contract targets declared
    ``mode: append_dedup`` under ``truth/`` are merged through the truth_io
    keyed upsert instead of overwritten (C3 T2, F360/F828 — see
    :func:`_route_append_dedup_write`). The skill's output for such a target is
    the INCREMENT (the new chapter's row/rows); the program merges it by the
    contract-declared key, so cumulative truth files accumulate instead of
    collapsing to the latest increment. It honors ``no_op_behavior: skip_write``
    (paths in *skip_paths* are not written).

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
        # Contract paths arrive staging-prefixed for checkpoint-gated skills
        # (uses_staging); the semantics map is keyed by the CONTRACT path.
        mode_meta = semantics.get(rel_path.removeprefix("staging/"), {})
        if mode_meta.get("mode") == "append_dedup":
            # Routed merge (C3 T2): upsert by key, never a whole-file rewrite.
            key_field = str(mode_meta.get("key") or "chapter")
            _route_append_dedup_write(project_dir, rel_path, content, key_field=key_field)
            written.append(rel_path)
            log.info(
                "output_written",
                path=rel_path,
                size=len(content),
                mode="append_dedup",
                key=key_field,
            )
        else:
            # z11 R1a (F1301): normalize the contract header on the chapter
            # write path (before the post-snapshot, so write-audit sees the
            # final contract-compliant content).
            _m = _CHAPTER_NUM_RE.match(Path(rel_path).stem)
            if _m and not _is_audit_file(Path(rel_path).name):
                content = ensure_chapter_header(content, int(_m.group(1)))
            safe_write(full_path, content)
            written.append(rel_path)
            log.info("output_written", path=rel_path, size=len(content), mode=mode_meta.get("mode"))

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
        # append_dedup-declared truth targets branch INSIDE _write_one into
        # _route_append_dedup_write (keyed upsert merge); everything else is a
        # whole-file write.
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
        if FORBIDDEN_FILENAME_RE.search(rel_path):
            log.error("wildcard_filename_rejected", path=rel_path, skill=skill)
            raise DispatchWriteFailureError(
                f"wildcard write rejected: filename contains forbidden "
                rf'characters (" < > [ \ control): {rel_path!r}',
                signature="forbidden_filename",
            )
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
#: ``truth/current_state.md [系统演化阶段, 参数当前位置, 进行中的情节线]`` find their H2
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
# Dispatch-level token logging (Task 7 of Plan 18)
# ---------------------------------------------------------------------------


def _log_token_usage(
    response: Any,
    skill_name: str,
    chapter: int | None = None,
    project_dir: Path | None = None,
) -> None:
    """Log token usage from API response or a bare usage object.

    Accepts either (a) a full API response object with a ``.usage`` attribute,
    or (b) a bare Usage object (e.g. ``CompletionUsage`` from the streaming
    final chunk) that has ``prompt_tokens`` / ``completion_tokens`` directly.
    The streaming path passes the bare usage object (``_call_llm_streaming_
    with_retry`` returns ``chunk.usage``), so the ``hasattr(response, "usage")``
    guard alone would skip it — handle both shapes.

    C10 spec T1 (F301/F504): the durable ledger write below is no longer
    gated on a ``state`` object being threaded through the call — 8 of the
    13 production call sites dispatch without state, which left
    cost/token-ledger.jsonl permanently empty. *chapter* is the on-the-spot
    value parsed from path_ctx/extract_chapter (F505/T401), never
    ``getattr(state, "chapter", 0)`` which was always 0.
    """
    # Form (b): bare Usage object (has prompt_tokens directly, no nested .usage).
    if hasattr(response, "prompt_tokens") and not hasattr(response, "usage"):
        usage = response
    # Form (a): response object wrapping usage.
    elif hasattr(response, "usage") and response.usage is not None:
        usage = response.usage
    else:
        return

    log.info(
        "llm_token_usage",
        skill=skill_name,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )

    _record_usage_to_ledger(skill_name, chapter, usage, project_dir)


def _record_usage_to_ledger(
    skill_name: str,
    chapter: int | None,
    usage: Any,
    project_dir: Path | None,
) -> None:
    """Persist a usage object to the durable append-only ledger (C10 spec T1).

    Fail-safe (spec risk section): the ledger is a hot-path side-effect of
    dispatch — a missing project_dir or any write error is logged WARN and
    skipped, never raising into the dispatch flow.
    """
    if project_dir is None:
        log.warning("ledger_skip_no_project_dir", skill=skill_name)
        return
    try:
        TokenLedger(project_dir).record(
            skill_name,
            chapter or 0,
            {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        )
    except Exception:
        log.warning("ledger_record_failed", skill=skill_name, exc_info=True)


def _record_estimate_row(
    skill: str,
    chapter: int | None,
    prompt_text: str,
    project_dir: Path | None,
    attempt: int = 1,
) -> None:
    """Append a lower-bound estimated row (C10 spec #36 T5 / F796).

    IDE/subprocess paths cannot report structured usage; the prompt estimate
    is a floor, explicitly marked estimated=True so the report separates it
    from metered rows. Fail-safe like _record_usage_to_ledger.
    """
    if project_dir is None:
        log.warning("ledger_skip_no_project_dir", skill=skill)
        return
    try:
        from shenbi.cost.estimate import estimate_prompt_tokens

        est = estimate_prompt_tokens(prompt_text)
        TokenLedger(project_dir).record(
            skill,
            chapter or 0,
            {"prompt_tokens": est, "completion_tokens": 0, "total_tokens": est},
            estimated=True,
            attempt=attempt,
        )
    except Exception:
        log.warning("ledger_estimate_record_failed", skill=skill, exc_info=True)


def print_token_summary(state: Any) -> None:
    """Print token usage summary at end of pipeline.

    C10 spec T1 option B / T2 (T403/F530): the durable ledger
    (cost/token-ledger.jsonl) is the single source of truth. The former
    undeclared ``state.token_usage`` in-memory dict never participated in
    to_dict/from_dict/checkpoint (resume reset it to zero) and missed every
    parallel-path dispatch (F301/F504), so this summary now reads the ledger
    via ``state.project_dir``.
    """
    project_dir = getattr(state, "project_dir", None)
    if not project_dir:
        return

    summary = TokenLedger(Path(project_dir)).summarize()
    by_skill: dict[str, dict[str, int | float]] = summary.get("by_skill", {})
    if not by_skill:
        return

    log.info("token_usage_summary_header", msg="Token usage by skill:")
    for skill_name, rec in sorted(by_skill.items()):
        avg_prompt = rec["prompt_tokens"] / max(rec["calls"], 1)
        avg_completion = rec["completion_tokens"] / max(rec["calls"], 1)
        log.info(
            "token_usage_summary_row",
            skill=skill_name,
            avg_prompt_tokens=int(avg_prompt),
            avg_completion_tokens=int(avg_completion),
            total_tokens=rec["total_tokens"],
            calls=rec["calls"],
        )


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
) -> tuple[str, str | None, Any, str | None]:
    """Stream LLM response with optional early-stop patterns.

    Returns (collected_text, stop_reason, usage, finish_reason) where:
    - stop_reason: None for normal completion or early_stop description string
    - usage: token usage object from the API response (or None)
    - finish_reason: API's finish_reason from the final chunk (e.g. "length",
      "content_filter", "stop", "tool_calls"), or None if unavailable.
      Spec §2.9: this is the truncation detection signal.
    """
    collected: list[str] = []
    stop_reason: str | None = None
    usage: Any = None
    finish_reason: str | None = None
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
        **kwargs,
    )
    for chunk in stream:
        # Collect usage from final chunk (when stream_options include_usage is set)
        if hasattr(chunk, "usage") and chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices:
            choice = chunk.choices[0]
            # Spec §2.9: capture finish_reason from the final chunk.
            # Use getattr (not attribute access) because existing test fake chunks
            # (test_dispatch_usage_capture.py, test_retry.py) build SimpleNamespace
            # or MagicMock choices that may not have finish_reason set.
            chunk_finish = getattr(choice, "finish_reason", None)
            if chunk_finish is not None:
                finish_reason = chunk_finish
            delta_content = getattr(choice.delta, "content", None)
            if delta_content:
                collected.append(delta_content)
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
    if finish_reason == "length":
        log.warning("length_truncation_detected", model=model)
    # Fallback: try stream.usage if not captured from individual chunks
    if usage is None and hasattr(stream, "usage") and stream.usage is not None:
        usage = stream.usage
    return result, stop_reason, usage, finish_reason


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
) -> tuple[str, str | None, Any, str | None]:
    """Stream LLM response with retry on transient failures.

    Retries: 429 (rate limit), 5xx (server errors), timeouts.
    Does NOT retry: 400, 401, 403 (client errors).

    Returns (collected_text, stop_reason, usage, finish_reason).
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
    - ``SHENBI_LLM_BASE_URL`` (default: https://api.deepseek.com/v1)
    - ``SHENBI_LLM_MODEL`` (default: deepseek-v4-flash)

    Token metering (C10 spec T1): every call appends one durable row to
    ``<project_dir>/cost/token-ledger.jsonl`` with the on-the-spot chapter —
    no PipelineState required (8/13 call sites dispatch without one).

    Args:
        skill: The skill name to dispatch.
        project_dir: Path to the project directory.
        prompt: The prompt text to send to the skill.
        uses_staging: Whether to use staging directories for output paths.
        shared_context: Optional shared context object for prompt building.
    """
    from openai import OpenAI

    path_ctx = parse_path_context(prompt)
    # only an int chapter is authoritative — a tolerant-parse str sentinel
    # would crash %03d placeholder formatting downstream
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        chapter = extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill,
            project_dir,
            prompt,
            chapter,
            uses_staging=uses_staging,
            shared_context=shared_context,
            path_context=path_ctx,
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
        output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
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
    except httpx.TimeoutException:
        # Exception-TYPED timeout routing — message sniffing breaks silently
        # when the provider library rewords its errors (F395, stage-8 review).
        _handle_timeout_gracefully(skill, chapter)
        log.error("api_call_timeout", skill=skill)
        return DispatchResult(False, -1, "", "API call timed out")
    except Exception as exc:
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")

    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)
    if stop_reason:
        log.info("api_dispatch_early_stop", skill=skill, stop_reason=stop_reason)

    # Dispatch-level token logging (Task 7 of Plan 18; C10 spec T1 rewire).
    # Logs token usage when the provider includes usage in streaming responses
    # (via stream_options={"include_usage": True}). Falls back to pre-flight
    # heuristic (warn_if_over_budget) when usage is unavailable.
    if usage is not None:
        _log_token_usage(usage, skill, chapter=chapter, project_dir=project_dir)

    # Spec §5.1: finish_reason-driven cap-raise (outside tenacity @retry).
    if finish_reason == "content_filter":
        log.error("content_filter_blocked", skill=skill)
        return DispatchResult(
            False, -1, "", "content_filter: output blocked by provider safety filter"
        )

    if finish_reason == "length":
        original_cap = _get_skill_max_tokens(skill)
        raised_cap = min(original_cap * 2, int(_MODEL_OUTPUT_CEILING * 0.9))
        if raised_cap <= original_cap:
            # Cap already at ceiling — can't raise further.
            log.error(
                "length_truncation_at_ceiling",
                skill=skill,
                cap=original_cap,
                ceiling=_MODEL_OUTPUT_CEILING,
            )
            return DispatchResult(
                False,
                -1,
                "",
                f"length_truncation: output exceeded max_tokens={original_cap} and cap "
                f"is at model ceiling {_MODEL_OUTPUT_CEILING}. Chapter too long — "
                f"consider splitting (spec §2.9 fail-fast).",
            )
        log.warning(
            "length_truncation_cap_raise",
            skill=skill,
            original_cap=original_cap,
            raised_cap=raised_cap,
        )
        try:
            output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
                client,
                model,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=_get_skill_temperature(skill),
                max_tokens=raised_cap,
                timeout=api_timeout,
            )
        except Exception as exc:
            # Only treat as timeout if it actually is — cap-raise may 400
            # if the provider rejects the raised max_tokens (Copilot review).
            if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                _handle_timeout_gracefully(skill, chapter)
            log.error("api_call_failed", skill=skill, error=str(exc))
            return DispatchResult(False, -1, "", f"API call failed: {exc}")

        # Log cap-raised usage.
        if usage is not None:
            _log_token_usage(usage, skill, chapter=chapter, project_dir=project_dir)

        # After cap-raise, if STILL length → fail-fast (spec §5.1: max 1 resend).
        if finish_reason == "length":
            log.error(
                "length_truncation_persistent",
                skill=skill,
                raised_cap=raised_cap,
            )
            return DispatchResult(
                False,
                -1,
                "",
                f"length_truncation: output still exceeds raised cap={raised_cap}. "
                f"Chapter too long for model output limit — consider splitting.",
            )
        if finish_reason == "content_filter":
            log.error("content_filter_blocked_after_cap_raise", skill=skill)
            return DispatchResult(
                False,
                -1,
                "",
                "content_filter: output blocked by provider safety filter (after cap-raise)",
            )
    # If we reach here (no length/content_filter, or cap-raise succeeded with
    # finish_reason="stop"), output_text is valid — fall through to the existing
    # _parse_structured_output / _write_parsed_outputs block below.

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
    except TruthFileParseError as exc:
        # Corrupt existing truth file met an append_dedup upsert: fail loud at
        # the dispatch layer (failed result, no process crash). Retrying the
        # LLM call cannot fix the file — the failure surfaces to the chapter
        # loop's failure handling (retry budget -> checkpoint for human repair).
        log.error("truth_upsert_parse_failed", skill=skill, error=str(exc))
        return DispatchResult(
            False, -1, "", f"truth file upsert aborted (existing file corrupt): {exc}"
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
    shared_context: Any = None,
    state: Any = None,
) -> DispatchResult:
    """Execute a skill via an IDE agent CLI (codex / zcode).

    Builds a complete prompt, spawns the IDE agent, parses the multi-file
    response, and writes per-file output to the project directory.
    """
    path_ctx = parse_path_context(prompt)
    # only an int chapter is authoritative — a tolerant-parse str sentinel
    # would crash %03d placeholder formatting downstream
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        chapter = extract_chapter(prompt)
    try:
        system_prompt, user_prompt, output_paths = _build_skill_prompt(
            skill,
            project_dir,
            prompt,
            chapter,
            uses_staging=uses_staging,
            shared_context=shared_context,
            path_context=path_ctx,
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
    except TruthFileParseError as exc:
        # Same policy as the API route: corrupt existing truth file -> failed
        # dispatch result, not a process crash (see _dispatch_via_api).
        log.error("truth_upsert_parse_failed", skill=skill, error=str(exc))
        return DispatchResult(
            False, -1, "", f"truth file upsert aborted (existing file corrupt): {exc}"
        )
    if not written:
        return DispatchResult(False, -1, "", "No output files written")

    missing = [p for p in output_paths if "*" not in p and not (project_dir / p).exists()]
    if missing:
        log.error("ide_missing_outputs", skill=skill, missing=missing)

    # C10 spec #36 T5 (F796): the IDE-CLI path reports no structured usage —
    # record an estimated lower-bound row unconditionally (most call sites
    # have no state; the block below is diagnostics only).
    _record_estimate_row(skill, chapter, full_prompt, project_dir)
    # Spec §3.1 / I6: the IDE-CLI path does not report structured token usage
    # (codex exec stdout is prose, not a usage object). state is threaded so a
    # future codex --json or zcode usage-report feature can record here.
    if state is not None:
        log.info(
            "ide_dispatch_uninstrumented_tokens",
            skill=skill,
            hint="IDE path cannot record usage; ledger row skipped",
        )
    return DispatchResult(True, 0, r.stdout, r.stderr)


# ---------------------------------------------------------------------------
# Tier B write audit for in-process routes (C32 R3 / F518)
# ---------------------------------------------------------------------------


def _normalize_staged_snapshot(
    snap: Mapping[str, str | None], declared: set[str]
) -> dict[str, str | None]:
    """Fold ``staging/<declared>`` snapshot keys back onto the declared relpath.

    Spec #29 R1: staged writes land on ``staging/<contract-path>`` while the
    audit's declared surface is the unprefixed contract path. Without this
    fold, pre==post on the declared key and the staged write is invisible
    (audit theater: a ``blocked:false`` no-op record). A present staged file
    OVERRIDES the live key — the staged tree is what the dispatch just
    produced and what a later commit would ship; a missing staged file
    (``None``) never folds, so the live baseline survives and a staged write
    that dropped live rows still diffs as a modification. Staged paths that
    map to no declared key are kept verbatim so they surface as undeclared
    writes.
    """
    out = dict(snap)
    for key, value in snap.items():
        if key.startswith("staging/"):
            base = key[len("staging/") :]
            if base in declared:
                if value is not None:
                    out[base] = value
                out.pop(key, None)
    return out


def _with_write_audit(
    dispatch_fn: Callable[[], DispatchResult],
    skill: str,
    project_dir: Path,
    prompt: str,
    round_dir: Path | str | None = None,
    uses_staging: bool = False,
) -> DispatchResult:
    """Wrap an in-process dispatch route (API / IDE CLI) with the Tier B write audit.

    Same finally-hook topology as ``dispatcher.executor.dispatch_with_write_audit``
    (the legacy CLI route's auditor): pre snapshot(declared write surface) ->
    dispatch -> post snapshot -> audit -> ledger record. The snapshot root is
    the pipeline project dir — the root ``_write_parsed_outputs`` actually
    writes to (the legacy route snapshots the framework repo root instead,
    F519, out of scope here). With ``uses_staging=True`` the watch face is
    extended to ``staging/<declared>`` and staged snapshot keys are folded
    back onto the declared relpath before auditing (spec #29 R1).

    Audit-failure semantics match the legacy route except the last bullet
    (infra failures fail-open here; the legacy subprocess crashes instead):
    - violations/drift on a rc==0 dispatch downgrade it to GATE_FAIL
      (success=False, returncode=2) with the reasons surfaced in stderr —
      recorded, never swallowed;
    - the audit runs even when dispatch raises, so write overreach on
      failure paths is still caught (then the original exception re-raises);
    - an audit *infrastructure* exception is logged as error and does not
      crash the dispatch (不崩) — it is not a violation verdict.
    """
    from shenbi.audit._shared import derive_output_files
    from shenbi.audit.record import record_audit_outcome
    from shenbi.audit.snapshot import snapshot_tree
    from shenbi.audit.write_audit import audit_writes

    path_ctx = parse_path_context(prompt)
    # only an int chapter is authoritative — a tolerant-parse str sentinel
    # would crash %03d placeholder formatting downstream
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        chapter = extract_chapter(prompt)
    watch = derive_output_files(skill, chapter, ctx=path_ctx)
    # Spec #29 R1: staged writes go to staging/<declared> — watch both and fold
    # the staged keys back onto the declared relpath before auditing.
    staged_watch = [f"staging/{p}" for p in watch] if uses_staging else []
    declared_keys = set(watch)
    ledger_dir = Path(round_dir) if round_dir else project_dir
    pre = _normalize_staged_snapshot(
        snapshot_tree(project_dir, watch + staged_watch), declared_keys
    )
    rc = DispatchResult(False, -1, "", "dispatch did not return a result")
    dispatch_exc: BaseException | None = None
    try:
        rc = dispatch_fn()
    except Exception as exc:
        log.error(
            "dispatch_exception",
            skill=skill,
            exc_type=type(exc).__name__,
            exc_msg=str(exc),
            project_dir=str(project_dir),
        )
        dispatch_exc = exc
    finally:
        # Franklin Important: if dispatch crashes mid-write, still run the
        # post-snapshot + audit so write overreach is caught on failure paths.
        try:
            post = _normalize_staged_snapshot(
                snapshot_tree(project_dir, watch + staged_watch), declared_keys
            )
            result = audit_writes(skill, pre, post, chapter=chapter, ctx=path_ctx)
            audit_ok = record_audit_outcome(ledger_dir, skill, result)
        except Exception:
            log.error("write_audit_infra_error", skill=skill, exc_info=True)
        else:
            if not audit_ok and rc.returncode == 0:
                reasons = "; ".join([*result.violations, *result.drift])
                stderr = (
                    f"{rc.stderr}\nwrite-audit GATE_FAIL: {reasons}"
                    if rc.stderr
                    else f"write-audit GATE_FAIL: {reasons}"
                )
                rc = DispatchResult(False, 2, rc.stdout, stderr)
    if dispatch_exc is not None:
        raise dispatch_exc
    return rc


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
    state: Any = None,
    path_context: PathContext | None = None,
) -> DispatchResult:
    """Dispatch a skill for execution.

    Routing (tried in order, all audited — C32 R3 / F518):
    1. ``SHENBI_LLM_API_KEY`` set → OpenAI-compatible API (wrapped in
       ``_with_write_audit``)
    2. IDE CLI available (codex / zcode) → spawn agent subprocess (wrapped
       in ``_with_write_audit``)
    3. Fallback → ``shenbi-dispatch`` CLI subprocess (audited inside the
       subprocess by ``dispatch_with_write_audit``)

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
        state: Optional PipelineState. No longer used for token accounting —
            the durable ledger is written inside the API path regardless of
            state (C10 spec T1). Threading it now only toggles instrumentation
            diagnostics on the IDE/legacy routes.
        path_context: Optional per-family placeholder context (spec #6 R5).
            When provided, the ``[path-context]`` carrier line is appended to
            the prompt (visible to the executing LLM as a machine-generated
            echo of the Files-to-create list) and reaches all three routes.
    """
    pd = Path(project_dir)
    if path_context is not None:
        line = format_path_context(path_context)
        if line:
            prompt = f"{prompt}\n{line}"

    # API path (audited — C32 R3 / F518)
    if os.environ.get(_ENV_LLM_API_KEY):
        return _with_write_audit(
            lambda: _dispatch_via_api(
                skill, pd, prompt, uses_staging=uses_staging, shared_context=shared_context
            ),
            skill,
            pd,
            prompt,
            round_dir,
            uses_staging=uses_staging,
        )

    # IDE CLI path (audited — C32 R3 / F518)
    if _find_ide_cli():
        return _with_write_audit(
            lambda: _dispatch_via_ide(
                skill,
                pd,
                prompt,
                uses_staging=uses_staging,
                shared_context=shared_context,
                state=state,
            ),
            skill,
            pd,
            prompt,
            round_dir,
            uses_staging=uses_staging,
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

    path_ctx = parse_path_context(prompt)
    # only an int chapter is authoritative — a tolerant-parse str sentinel
    # would crash %03d placeholder formatting downstream
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        chapter = extract_chapter(prompt)
    chapter_path = pd / "chapters" / f"chapter-{chapter}.md" if chapter is not None else None
    cli_timeout = _compute_dispatch_timeout(skill, chapter_path)

    rd = str(round_dir) if round_dir else str(project_dir)
    log.info("dispatch_start", skill=skill, test_type=test_type, round_dir=rd)
    if state is not None:
        # C10 spec T1: the legacy subprocess path receives state but cannot
        # thread it anywhere — surface the drop instead of silently discarding.
        log.warning(
            "legacy_dispatch_state_uninstrumented",
            skill=skill,
            hint="legacy subprocess path records no token usage; cost evidence requires the API path (C10 spec T5)",
        )
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
    # C10 spec #36 T5: legacy subprocess cannot report usage — estimated row.
    _record_estimate_row(skill, chapter, prompt, pd)
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
        # F408: never fabricate scoring evidence. Missing progress.json = FAIL.
        log.error("g3_fail_closed_no_progress", skill=skill, path=str(pp))
        fail_result = {
            "status": GateStatus.FAIL,
            "error": "no progress.json — fail-closed (F408)",
        }
        if chapter is not None and phase is not None:
            _record_gate_manifest(rd, phase, chapter, skill, "G3", fail_result)
        return fail_result

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
