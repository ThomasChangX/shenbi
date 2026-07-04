"""G4 checker for shenbi-context-composing."""

from __future__ import annotations
from typing import Any
from pathlib import Path

from shenbi.gates.shared import (
    fail,
    passed,
)


# Layer-based section titles (spec §3.5). The checker matches on the
# language prefix so a title like "## P2 书脊（L5）" still validates.
REQUIRED_SECTIONS = [
    "## P1 章节备忘",
    "## P2 书脊",
    "## P3 当前大弧",
    "## P4 当前卷摘要",
    "## P5 当前弧段",
    "## P6 近章拍点",
    "## P7 世界铁律与文风",
    "## 近章结尾多样性",
    "## Hook 债务简报",
]

# Obsolete flat-model titles that must not appear (old P3/P5 meanings).
OBSOLETE_SECTIONS = [
    "## P3 活跃伏笔",
    "## P5 世界铁律",
    "## P2 近期摘要",
    "## P6 角色状态",
    "## P7 文风指纹",
]


def _section_body(content: str, title_prefix: str) -> str:
    """Return the body text under the first H2 section whose title starts
    with title_prefix, up to the next H2 header. Robust against adjacent
    empty sections (no regex boundary pitfalls).
    """
    capturing = False
    body: list[str] = []
    for line in content.splitlines():
        if line.startswith("## ") and title_prefix in line:
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            body.append(line)
    return "\n".join(body).strip()


def g4_context_composing(fps: list[str], rd: str | None = None) -> str:
    """Context composing: layer-based P1-P7 section titles present (P1+P2 non-empty)."""
    c: list[dict[str, Any]] = []
    mf = []

    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        pf = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not pf.exists():
            mf.append(f"G4.cc.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # Required layer-based section titles
        missing = [s for s in REQUIRED_SECTIONS if s not in content]
        if missing:
            mf.append(f"G4.cc.sections:missing_{missing}")
        else:
            c.append({"id": "G4.cc.sections", "file": fp, "s": "PASS"})

        # Reject obsolete flat-model titles
        obsolete = [s for s in OBSOLETE_SECTIONS if s in content]
        if obsolete:
            mf.append(f"G4.cc.obsolete_titles:{obsolete}")

        # P1+P2 non-empty (content between this H2 and the next H2)
        p1_content = _section_body(content, "## P1 章节备忘")
        p2_content = _section_body(content, "## P2 书脊")
        if not p1_content or not p2_content:
            mf.append(f"G4.cc.p1p2_empty:{fp}")
        else:
            c.append(
                {
                    "id": "G4.cc.p1p2",
                    "file": fp,
                    "s": "PASS",
                    "p1_len": len(p1_content),
                    "p2_len": len(p2_content),
                }
            )

    if not fps:
        c.append({"id": "G4.cc", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-context-composing", c, "scoring", mf)
    return passed("G4-context-composing", c)
