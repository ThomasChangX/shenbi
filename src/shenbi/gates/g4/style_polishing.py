"""G4 checker for shenbi-style-polishing."""

from __future__ import annotations
from typing import Any
from pathlib import Path

from shenbi.gates.shared import (
    bak_path,
    fail,
    passed,
    resolve_input_path,
    word_count_md,
)


def g4_style_polishing(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Style polishing: 润色说明 block present, word count change ratio check."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.sp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "## 润色说明" not in content:
            mf.append(f"G4.sp.no_report:{fp}")
        else:
            c.append({"id": "G4.sp.report", "file": fp, "s": "PASS"})

        # Word count change ratio within [0.85, 1.15]
        # Check the .bak sibling (pre-polish version) at the same resolved
        # root as the polished content (pf = base/fp), not a bare fp.
        bak = Path(bak_path(pf))
        if bak.exists():
            wc_before = word_count_md(bak)
            wc_after = word_count_md(pf)
            if wc_before > 0:
                ratio = wc_after / wc_before
                if ratio < 0.85 or ratio > 1.15:
                    mf.append(f"G4.sp.word_ratio:{fp}:{ratio:.2f}")
                else:
                    c.append(
                        {
                            "id": "G4.sp.word_ratio",
                            "file": fp,
                            "s": "PASS",
                            "before": wc_before,
                            "after": wc_after,
                        }
                    )

    if not fps:
        c.append({"id": "G4.sp", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-style-polishing", c, "scoring", mf)
    return passed("G4-style-polishing", c)
