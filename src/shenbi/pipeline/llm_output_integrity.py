"""Unified LLM-output integrity checks for the dispatch write path.

Spec: 2026-07-19 output-structural-integrity-beyond-json-design (merged Spec 19
+ former Spec 20).

This module is the single source of truth for the pattern catalog and the five
check functions invoked from ``dispatch_helper._write_parsed_outputs``. The
former Specs 19/20 maintained overlapping pattern lists; they are de-duplicated
here, split by detection mode:

  * ``WRITE_FAILURE_PATTERNS`` — the LLM reports it cannot write. These trip
    only under the dominance rule (start-of-content OR matched region >50% of
    output) so a chapter that merely *mentions* a sandbox in dialogue does not.
  * ``LEAKAGE_PATTERNS`` — model meta-commentary in prose (NOT a write failure).
  * ``VERDICT_MARKERS`` / ``PREAMBLE_MARKERS`` — audit-completeness signals.

All check functions return ``list[str]`` issue strings tagged
``G4.<group>.<rule>`` so the G4 composite-checker registry can route severity.
"""

from __future__ import annotations

import re
from pathlib import Path

# --- Write-failure signatures: the LLM reports it cannot write. ---
# These supersede the broader standalone patterns from the former specs
# (e.g. bare `由于沙箱限制`, `can't be updated.*sandbox`) which are now covered
# by the more specific entries below.
WRITE_FAILURE_PATTERNS: list[str] = [
    r"由于沙箱限制.*?(?:无法|不能).*?(?:写|写入)",
    r"(?:can't|cannot|unable to).*?(?:write|update|create).*?(?:file|sandbox|read-only)",
    r"read-only sandbox",
    r"Use the existing.*?from input",
    r"was already provided via.*?markers",
    r"I (?:cannot|can't|could not) (?:write|create|update) (?:the )?(?:file|output)",
]

# --- Model meta-commentary leakage in prose (NOT a write failure). ---
LEAKAGE_PATTERNS: list[str] = [
    r"Now the .* JSON",
    r"Let me write",
    r"schema:",
    r"Here's a summary of the revision",
    r"修订执行摘要",
    r"Revision complete",
    r"All \d+ files have been",
]

# --- Audit completeness markers ---
VERDICT_MARKERS: list[str] = ["判定", "结论", "verdict", "通过", "阻断", "PASS", "BLOCK"]
PREAMBLE_MARKERS: list[str] = ["现在执行", "inputs confirmed", "now executing", "开始审计"]

#: Minimum audit size in bytes — real audits are > 500 bytes.
_AUDIT_MIN_BYTES = 200

#: Retry-prompt suffix confirming write capability.
RETRY_WRITE_CONFIRMATION = (
    "CRITICAL: You have filesystem write access in this environment. "
    "Output the complete file content directly — do not explain, apologize, "
    "or reference sandbox limitations. Previous attempt failed with: '{signature}'."
)

# Pre-compile for performance.
_WRITE_FAILURE_RES = [re.compile(p, re.IGNORECASE) for p in WRITE_FAILURE_PATTERNS]
_LEAKAGE_RES = [re.compile(p, re.IGNORECASE) for p in LEAKAGE_PATTERNS]
_LINE_REF_RE = re.compile(r"L(\d+)(?:-(\d+))?")


def detect_write_failure(content: str) -> tuple[bool, str | None]:
    """Check if content is a write-failure diagnostic instead of file content.

    False-positive mitigation (spec §3.2): a pattern only counts as a failure
    when it appears at the START of the content OR the matched span sits within
    a region that comprises >50% of the total output. A chapter that merely
    *mentions* a sandbox in passing is NOT a failure.

    Returns ``(is_failure, matched_pattern_or_None)``.
    """
    total_len = max(len(content), 1)
    for rx in _WRITE_FAILURE_RES:
        match = rx.search(content)
        if not match:
            continue
        start, end = match.span()
        # Case 1: pattern at the very start (ignoring leading whitespace).
        at_start = content[:start].strip() == ""
        # Case 2: the region from first non-empty char to end of match covers
        # more than half the output — i.e. the diagnostic dominates rather
        # than being embedded in real content.
        dominant = end > total_len * 0.5
        if at_start or dominant:
            return True, match.group(0)
    return False, None


def check_prose_leakage(path: Path) -> list[str]:
    """Detect model meta-commentary leakage in prose files.

    Returns ``G4.pi.model_leakage`` issues (one per distinct pattern) and a
    single ``G4.pi.unfinished_ending`` issue if the file ends with a trailing
    punctuation character indicating mid-thought truncation.
    """
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    for rx in _LEAKAGE_RES:
        matches = rx.findall(text)
        if matches:
            issues.append(
                f"G4.pi.model_leakage:{path.name} — found '{matches[0]}' pattern "
                f"({len(matches)} occurrences). Chapter file contains model "
                f"meta-commentary, not prose."
            )

    last_500 = text[-500:].strip()
    if last_500 and last_500[-1] in ":,；：，":
        issues.append(
            f"G4.pi.unfinished_ending:{path.name} — file ends with "
            f"'{last_500[-20:]}' — truncated mid-thought"
        )

    return issues


def check_markdown_fence_balance(path: Path) -> list[str]:
    """Verify Markdown code fences are balanced in prose files."""
    text = path.read_text(encoding="utf-8")
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        return [
            f"G4.pi.fence_imbalance:{path.name} — odd number of ``` markers "
            f"({fence_count}). Orphan code fence — file was likely extracted "
            f"incorrectly."
        ]
    return []


def check_audit_completeness(path: Path) -> list[str]:
    """Verify audit files contain an actual verdict, not just a preamble."""
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    if len(text) < _AUDIT_MIN_BYTES:
        issues.append(
            f"G4.ac.too_short:{path.name} — audit file is {len(text)} bytes, likely aborted stub"
        )

    has_verdict = any(marker in text for marker in VERDICT_MARKERS)
    if not has_verdict:
        issues.append(
            f"G4.ac.no_verdict:{path.name} — audit file contains no verdict/conclusion marker"
        )

    has_only_preamble = any(marker in text for marker in PREAMBLE_MARKERS) and not has_verdict
    if has_only_preamble:
        issues.append(
            f"G4.ac.aborted_stub:{path.name} — audit file contains only "
            f"execution preamble, no results"
        )

    return issues


def check_audit_line_refs(path: Path, chapter_path: Path) -> list[str]:
    """Verify audit line references point to valid lines in the chapter."""
    if not chapter_path.exists():
        return []  # Chapter missing is handled elsewhere.

    audit_text = path.read_text(encoding="utf-8")
    chapter_lines = chapter_path.read_text(encoding="utf-8").split("\n")
    max_line = len(chapter_lines)

    issues: list[str] = []
    for start_str, end_str in _LINE_REF_RE.findall(audit_text):
        start = int(start_str)
        end = int(end_str) if end_str else start
        if end > max_line:
            issues.append(
                f"G4.av.stale_line_ref:{path.name} — references L{start}-{end} "
                f"but chapter has only {max_line} lines. Audit ran against a "
                f"different version of the chapter."
            )
    return issues
