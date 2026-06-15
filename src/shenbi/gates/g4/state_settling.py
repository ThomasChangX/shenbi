"""G4 checker for shenbi-state-settling."""

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


def g4_state_settling(fps: list[str], rd: str | None = None) -> str:
    """State settling: current_state has position, char_matrix has characters, summaries appended, emotional arcs."""
    c: list[dict[str, Any]] = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.ss.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "current_state" in str(fp):
            if "## 位置" not in content and "### 位置变化" not in content:
                mf.append(f"G4.ss.no_position:{fp}")
            else:
                c.append({"id": "G4.ss.position", "file": fp, "s": "PASS"})

        if "character_matrix" in str(fp):
            if "## 已登场角色" not in content and "## 角色" not in content:
                mf.append(f"G4.ss.no_characters:{fp}")
            else:
                c.append({"id": "G4.ss.characters", "file": fp, "s": "PASS"})

        if "chapter_summaries" in str(fp):
            if not re.search(r"## 第\d+章", content):
                mf.append(f"G4.ss.no_chapter_summary:{fp}")
            else:
                c.append({"id": "G4.ss.summaries", "file": fp, "s": "PASS"})

        if "emotional_arcs" in str(fp):
            if not re.search(r"### 第\d+章", content):
                mf.append(f"G4.ss.no_emotional_arc:{fp}")
            else:
                c.append({"id": "G4.ss.arcs", "file": fp, "s": "PASS"})

        if "particle_ledger" in str(fp):
            if "## 粒子账本" not in content and "particle" not in content.lower():
                mf.append(f"G4.ss.no_particle_ledger:{fp}")
            else:
                c.append({"id": "G4.ss.particle_ledger", "file": fp, "s": "PASS"})

        if "pending_hooks" in str(fp):
            if "state" not in content:
                mf.append(f"G4.ss.no_hook_state:{fp}")
            else:
                c.append({"id": "G4.ss.pending_hooks", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.ss", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)
