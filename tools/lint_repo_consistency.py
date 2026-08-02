#!/usr/bin/env python3
"""Repo-consistency lints (spec §5.5 #3,#4,#7).

3. body-ban        — skills/*/SKILL.md may not carry a hand-written 数据契约
                     block or **Reads:**/**Writes:**/**Updates:** (archived
                     rounds and the AUTO-GENERATED banner are exempt).
4. loader-uniqueness — only contract.py may read the frontmatter contract: key.
7. terminology     — banned synonyms (hook pool, truth-files, the author) +
                     section-header canonical set.
"""

from __future__ import annotations

import re
from collections.abc import Container, Iterable
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
BANNER = "<!-- AUTO-GENERATED from frontmatter — do not edit -->"
BODY_END = "<!-- END AUTO-GENERATED -->"
# Strip the auto-generated block before scanning, so a hand-written contract
# block added ALONGSIDE the auto-gen one is still caught (spec §3.3).
AUTO_BLOCK_RE = re.compile(re.escape(BANNER) + r".*?" + re.escape(BODY_END) + r"\n?", re.DOTALL)
CONTRACT_BODY_RE = re.compile(r"\*\*(Reads|Writes|Updates):\*\*|^## 数据契约", re.MULTILINE)
BANNED_SYNONYMS = {
    "hook pool": "hook ledger",
    "truth-files": "truth files",
    "the author": "your human partner",
}
# Layer A: output-section header deviants that must normalize to 输出格式.
# (We flag a banned set, NOT "anything not canonical" — skills legitimately have
# many other section headers like 检查执行 / 创作原则 / 缺陷证据格式.)
BANNED_HEADERS = {"输出契约", "输出", "Key Results", "输出文件"}
CANONICAL_OUTPUT_HEADER = "输出格式"
File = tuple[str, str]


def _skill_files() -> list[File]:
    """Return (relative-path, contents) for every skills/*/SKILL.md."""
    out: list[File] = []
    for p in sorted((REPO / "skills").glob("*/SKILL.md")):
        out.append((str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


def find_body_contract_blocks(files: Iterable[File]) -> list[str]:
    """Flag skill bodies carrying a hand-written 数据契约 block or Reads/Writes/Updates."""
    flagged: list[str] = []
    for path, md in files:
        if "tests/rounds/archived" in path:
            continue
        # Remove any auto-generated block first; a hand-written block that
        # remains after removal is a forbidden second source.
        stripped = AUTO_BLOCK_RE.sub("", md)
        if CONTRACT_BODY_RE.search(stripped):
            flagged.append(path)
    return flagged


def find_banned_synonyms(files: Iterable[File]) -> list[tuple[str, str]]:
    """Return (path, synonym) for every banned terminology term found in skill prose."""
    out: list[tuple[str, str]] = []
    for path, md in files:
        # Strip backtick code/filename spans — terminology targets prose, not code
        # references (e.g. `truth-files-reference.md` is a filename, not the synonym).
        prose = re.sub(r"`[^`]*`", "", md)
        for syn in BANNED_SYNONYMS:
            if syn in prose.lower():
                out.append((path, syn))
    return out


def find_section_header_deviants(files: Iterable[File]) -> list[tuple[str, str]]:
    """Flag Layer A output-section header deviants (must normalize to 输出格式).

    Does NOT flag arbitrary non-canonical headers — skills legitimately carry
    many section titles (检查执行, 创作原则, 缺陷证据格式, …). Only the banned
    output-section synonyms are drift.
    """
    out: list[tuple[str, str]] = []
    for path, md in files:
        for m in re.finditer(r"^##\s+(.+?)\s*$", md, re.MULTILINE):
            header = m.group(1).strip()
            if header in BANNED_HEADERS:
                out.append((path, header))
    return out


def find_extra_contract_key_readers(files: Iterable[File]) -> list[str]:
    """A module other than contract.py indexing/reading the 'contract' key."""
    flagged: list[str] = []
    for path, src in files:
        if path.endswith(("contract.py", "legacy.py")):
            continue
        if re.search(r'["\']contract["\']\s*\]', src) or re.search(
            r"\.get\(\s*[\"']contract[\"']\s*\)", src
        ):
            flagged.append(path)
    return flagged


# Skills whose decisions.json is structurally validated by G4 g4_decisions
# (alone or via make_composite_checker). These are NOT dead even with no skill
# reads: — G4 consumes their schema. Verified against the checkers dict in
# src/shenbi/gates/g4/generic.py (7 skills use g4_decisions as of this audit).
_G4_DECISIONS_SKILLS = frozenset(
    {
        "shenbi-chapter-drafting",
        "shenbi-chapter-planning",
        "shenbi-context-composing",
        "shenbi-market-radar",
        "shenbi-chapter-revision",
        "shenbi-short-drafting",
        "shenbi-state-settling",
    }
)

# A SKILL.md with frontmatter splits into [pre, frontmatter, body] on "---".
_FRONTMATTER_DELIM = "---"
_EXPECTED_FRONTMATTER_PARTS = 3


def _write_path(entry: object) -> str | None:
    """Extract the file path from a writes/reads entry (string OR dict-form).

    Spec contract: writes/reads entries may be a bare string OR a dict with a
    `file:` key (optionally `mode:` / `fields:`). This normalizer handles both.
    """
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("file")
    return None


def _all_skill_frontmatter() -> dict[str, dict[str, Any]]:
    """Return {skill_name: parsed frontmatter dict} for all shenbi-* skills."""
    out: dict[str, dict[str, Any]] = {}
    for skill_md in sorted((REPO / "skills").glob("shenbi-*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        if text.startswith(_FRONTMATTER_DELIM):
            parts = text.split(_FRONTMATTER_DELIM, 2)
            if len(parts) >= _EXPECTED_FRONTMATTER_PARTS:
                loaded = yaml.safe_load(parts[1])
                if isinstance(loaded, dict):
                    out[skill_md.parent.name] = loaded
    return out


def _code_reference_blob() -> str:
    """Concatenate all src/shenbi + tools *.py file contents into one blob.

    Used by _is_dead_decisions_sidecar to check if a decisions.json path stem
    is referenced in code. Pure-Python (rglob + read_text) — matches the
    existing lint style, no subprocess / shell-out grep (cross-platform safe).
    """
    parts: list[str] = []
    for root in (REPO / "src" / "shenbi", REPO / "tools"):
        for py in root.rglob("*.py"):
            parts.append(py.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _is_dead_decisions_sidecar(
    write_entry: object,
    skill: str,
    all_reads: Container[str],
    g4_skills: Container[str],
    code_blob: str,
) -> bool:
    """Return True iff a decisions.json write has no consumer (spec §3.5).

    A decisions.json write is 'dead' iff ALL of:
      1. No skill declares it in reads: (string OR dict-form)
      2. The producer skill is NOT in _G4_DECISIONS_SKILLS (G4 validates it)
      3. No src/tools code references the path stem
    """
    path = _write_path(write_entry)
    if not (isinstance(path, str) and path.endswith("-decisions.json")):
        return False
    if path in all_reads:
        return False  # a skill reads it
    if skill in g4_skills:
        return False  # G4 validates it
    # Code reference: check the path stem (strip the -N- chapter index).
    stem = path.replace("chapter-N-", "chapter-").replace("short-N-", "short-").replace("-N-", "-")
    return stem not in code_blob  # dead iff no code references it


def find_dead_decisions_sidecars() -> list[str]:
    """Flag decisions.json writes with no consumer (spec §3.5).

    Returns a list of violation strings. See _is_dead_decisions_sidecar for
    the 'dead' definition (smarter than the spec's original 'no reads' —
    accounts for G4 + code consumers found in Task 4 disposition).
    """
    frontmatters = _all_skill_frontmatter()
    # Collect all reads paths across all skills (string + dict-form).
    all_reads: set[str] = set()
    for fm in frontmatters.values():
        contract = fm.get("contract") or {}
        for r in contract.get("reads") or []:
            p = _write_path(r)
            if p:
                all_reads.add(p)
    code_blob = _code_reference_blob()

    vios: list[str] = []
    for skill, fm in frontmatters.items():
        contract = fm.get("contract") or {}
        for w in contract.get("writes") or []:
            if _is_dead_decisions_sidecar(w, skill, all_reads, _G4_DECISIONS_SKILLS, code_blob):
                path = _write_path(w) or "?"
                vios.append(f"dead-decisions-sidecar: {skill}: {path}")
    return vios


def main() -> int:
    """Run all repo-consistency checks; print violations, exit non-zero if any."""
    vios: list[str] = []
    skills = _skill_files()
    for p in find_body_contract_blocks(skills):
        vios.append(f"body-ban: {p}")
    for p, syn in find_banned_synonyms(skills):
        vios.append(f"terminology: {p}: '{syn}' -> '{BANNED_SYNONYMS[syn]}'")
    for p, h in find_section_header_deviants(skills):
        vios.append(f"section-header: {p}: '## {h}'")
    py_files = [
        (str(p.relative_to(REPO)), p.read_text(encoding="utf-8"))
        for p in (REPO / "src" / "shenbi").rglob("*.py")
    ]
    for p in find_extra_contract_key_readers(py_files):
        vios.append(f"loader-uniqueness: {p} reads frontmatter contract: key")
    for v in find_dead_decisions_sidecars():
        vios.append(v)
    for v in vios:
        print(v)
    return 1 if vios else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
