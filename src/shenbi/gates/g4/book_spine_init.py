"""G4 checker for shenbi-book-spine-init."""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.shared import fail, passed


def g4_book_spine_init(fps: list[str], rd: str | None = None) -> str:
    """Validate book_spine.md has required frontmatter fields + sections."""
    c, mf = [], []
    base = Path(rd) if rd else Path.cwd()
    for fp in fps or []:
        p = base / fp if not Path(fp).is_absolute() else Path(fp)
        if not p.exists():
            mf.append(f"G4.bsi.not_found:{fp}")
            continue
        content = p.read_text(encoding="utf-8")
        for field in ["updated:", "total_chapters:", "status:"]:
            if field not in content:
                mf.append(f"G4.bsi.missing_field:{field}")
        for section in ["核心冲突", "themes", "主角弧", "主线钩子"]:
            if section not in content:
                mf.append(f"G4.bsi.missing_section:{section}")
    if not fps:
        c.append({"id": "G4.bsi", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-book-spine-init", c, "scoring", mf)
    return passed("G4-book-spine-init", c)
