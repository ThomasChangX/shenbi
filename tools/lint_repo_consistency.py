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
from collections.abc import Iterable
from pathlib import Path

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
    """Return (path, synonym) for every banned terminology term found in a skill body."""
    out: list[tuple[str, str]] = []
    for path, md in files:
        for syn in BANNED_SYNONYMS:
            if syn in md.lower():
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
        if path.endswith("contract.py"):
            continue
        if re.search(r'["\']contract["\']\s*\]', src) or re.search(
            r"\.get\(\s*[\"']contract[\"']\s*\)", src
        ):
            flagged.append(path)
    return flagged


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
    for v in vios:
        print(v)
    return 1 if vios else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
