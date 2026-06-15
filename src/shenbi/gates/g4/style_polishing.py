"""G4 checker for shenbi-style-polishing."""

from __future__ import annotations
from typing import Any
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


def g4_style_polishing(fps: list[str], rd: str | None = None) -> str:
    """Style polishing: 润色说明 block present, word count change ratio check."""
    c: list[dict[str, Any]] = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.sp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "## 润色说明" not in content:
            mf.append(f"G4.sp.no_report:{fp}")
        else:
            c.append({"id": "G4.sp.report", "file": fp, "s": "PASS"})

        # Word count change ratio within [0.85, 1.15]
        # Check if there's a .bak file (pre-polish version)
        bak = Path(str(fp) + ".bak")
        if bak.exists():
            wc_before = word_count_md(str(bak))
            wc_after = word_count_md(fp)
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
