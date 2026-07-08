"""G4 checker for shenbi-context-composing."""

from __future__ import annotations
import re
from typing import Any

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_input_path,
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


def g4_context_composing(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Context composing: layer-based P1-P7 section titles present (P1+P2 non-empty)."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.cc.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # Required layer-based section titles (P1-P7) OR pipeline route-based
        # format (route-a:, route-b:, route-c:) from pipeline-context-assemble.
        # In pipeline mode, context-composing curates the pre-assembled output
        # rather than generating P1-P7 from scratch.
        has_p_format = all(s in content for s in REQUIRED_SECTIONS)
        has_route_format = bool(re.search(r"## route-[abc]:", content))

        if not has_p_format and not has_route_format:
            missing = [s for s in REQUIRED_SECTIONS if s not in content]
            mf.append(f"G4.cc.sections:missing_{missing}")
        else:
            fmt = "P1-P7" if has_p_format else "route-based"
            c.append({"id": "G4.cc.sections", "file": fp, "s": "PASS", "format": fmt})

        # Reject obsolete flat-model titles
        obsolete = [s for s in OBSOLETE_SECTIONS if s in content]
        if obsolete:
            mf.append(f"G4.cc.obsolete_titles:{obsolete}")

        # P1+P2 non-empty (only for P1-P7 format; route-based skips this)
        if has_p_format:
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
        elif has_route_format:
            # Route-based format: check that content is substantive (non-empty routes)
            route_count = len(re.findall(r"## route-[abc]:", content))
            if route_count >= 2:
                c.append(
                    {"id": "G4.cc.routes", "file": fp, "s": "PASS", "route_count": route_count}
                )
            else:
                mf.append(f"G4.cc.routes:only_{route_count}_routes")

    if not fps:
        c.append({"id": "G4.cc", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-context-composing", c, "scoring", mf)
    return passed("G4-context-composing", c)
