"""G4 checker for shenbi-faction-builder."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from shenbi.gates.shared import (  # noqa: F401
    ALL_SKILLS,
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    FIXTURES,
    G4_CHECKER_SKILLS,
    META_NARRATIVE,
    PROJECT,
    SKILLS,
    TESTS,
    TRANSITION_SPECIFIC,
    _find_report,
    _normalize_file_paths,
    count_transition_words,
    fail,
    jload,
    passed,
    read_genre_config,
    unimplemented,
    word_count_md,
    write_gate_marker,
    yload,
)


def g4_faction_builder(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    """Faction builder: >= 2 factions each with hierarchy, internal conflicts,
    cross-faction relations, interest-driven behavior.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    factions_path = pd / "world" / "factions.md"
    if not factions_path.exists():
        mf.append("G4.factions.not_found")
    else:
        content = factions_path.read_text(encoding="utf-8")
        factions = re.findall(r"## 势力[：:]", content)
        if len(factions) < 2:
            mf.append(f"G4.factions.count:{len(factions)}<2")
        else:
            c.append({"id": "G4.factions.count", "s": "PASS", "count": len(factions)})
            valid = 0
            for match in re.finditer(r"## 势力[：:].*?\n(?=## 势力|\Z)", content, re.DOTALL):
                faction_text = match.group()
                has_hierarchy = bool(re.search(r"层级结构|### 层级", faction_text))
                has_internal = bool(re.search(r"内部矛盾|### 内部", faction_text))
                has_cross = bool(re.search(r"跨势力|跨势力动态", faction_text))
                has_interest = bool(re.search(r"利益驱动", faction_text))
                if has_hierarchy and has_internal and has_cross and has_interest:
                    valid += 1
            if valid < 2:
                mf.append(f"G4.factions.complete:{valid}/{len(factions)}")
            else:
                c.append({"id": "G4.factions.complete", "s": "PASS", "complete": valid})

    if mf:
        return fail("G4-faction-builder", c, "scoring", mf)
    return passed("G4-faction-builder", c)
