"""Three-source decisions-declaration reconciliation (spec #30 T4, T106/F439).

Every skill that produces a decisions sidecar must be declared consistently in:
  1. docs/framework/decisions-schema.md   (Per-Skill Differences table)
  2. docs/framework/truth-files.yaml      (kind: decisions entries)
  3. skills/<skill>/SKILL.md              (contract writes containing "decisions")

Exit 0 = all three sources agree; exit 1 = drift report on stdout.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
TRUTH_FILES = REPO / "docs" / "framework" / "truth-files.yaml"
SCHEMA_DOC = REPO / "docs" / "framework" / "decisions-schema.md"


def _skill_names_from_writes() -> set[str]:
    """Skills whose contract writes/updates declare a *decisions*.json output."""
    result: set[str] = set()
    for skill_md in sorted(SKILLS.glob("shenbi-*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        # crude YAML scan of the contract block only
        block = m.group(1)
        in_outputs = False
        for line in block.splitlines():
            s = line.strip()
            if re.match(r"^(writes|updates):", s):
                in_outputs = True
                continue
            if in_outputs:
                if s.startswith("-") and "decisions" in s and s.endswith(".json"):
                    result.add(skill_md.parent.name.removeprefix("shenbi-"))
                    in_outputs = False
                    break
                if (
                    s
                    and not s.startswith("-")
                    and not s.startswith(("file:", "mode:", "key:", "fields:"))
                ):
                    in_outputs = False
    return result


# file-stem -> skill name (the authoritative mapping; drift here fails the test)
STEM_TO_SKILL = {
    "chapter-N-context-decisions": "context-composing",
    "market-radar-decisions": "market-radar",
    "chapter-N-decisions": "chapter-drafting",
    "chapter-N-plan-decisions": "chapter-planning",
    "chapter-N-revision-decisions": "chapter-revision",
    "state-settling-decisions": "state-settling",
    "genre-config-decisions": "genre-config",
    "short-N-decisions": "short-drafting",
}


def _truth_file_skills() -> set[str]:
    text = TRUTH_FILES.read_text(encoding="utf-8")
    entries = re.findall(r"name:\s*([\w\-/{}.]+decisions\.json),\s*kind:\s*decisions", text)
    skills = set()
    for path in entries:
        stem = Path(path).stem
        skill = STEM_TO_SKILL.get(stem)
        if skill is None:
            print(
                f"lint_decisions_sources: unmapped decisions file '{path}' — extend STEM_TO_SKILL"
            )
            sys.exit(1)
        skills.add(skill)
    return skills


def _schema_doc_skills() -> set[str]:
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    m = re.search(r"## Per-Skill Differences.*?\n(\|.*\n)+", text, re.DOTALL)
    if not m:
        return set()
    return {row.strip("` ") for row in re.findall(r"\|\s*`([\w\-]+)`\s*\|", m.group(0))}


def main() -> int:
    """Reconcile the three decisions-declaration sources; exit 1 on drift."""
    writes = _skill_names_from_writes()
    truth = _truth_file_skills()
    doc = _schema_doc_skills()
    drift = False
    for label, a, b in [
        ("SKILL-writes", writes, truth),
        ("truth-files", truth, writes),
        ("SKILL-writes", writes, doc),
        ("schema-doc", doc, writes),
        ("truth-files", truth, doc),
        ("schema-doc", doc, truth),
    ]:
        missing = a - b
        if missing:
            drift = True
            print(f"{label} declares {sorted(missing)} but counterpart does not")
    if not drift:
        print(f"lint_decisions_sources: OK ({len(writes)} producers aligned across 3 sources)")
        return 0
    print(f"  writes={sorted(writes)}\n  truth={sorted(truth)}\n  doc={sorted(doc)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
