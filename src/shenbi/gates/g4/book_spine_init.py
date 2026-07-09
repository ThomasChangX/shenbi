"""G4 checker for shenbi-book-spine-init."""

from __future__ import annotations
from typing import Any

from shenbi.gates.shared import fail, passed, resolve_input_path


def g4_book_spine_init(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Validate book_spine.md has required frontmatter fields + sections."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp in fps or []:
        p = resolve_input_path(fp, rd)
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
