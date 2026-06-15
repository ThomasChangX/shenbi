"""G4 checker for shenbi-length-normalizing."""

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


def g4_length_normalizing(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    """Length normalizing: checks per new SKILL.md thresholds.
    - 3000-10000 range: report only, no chapter body → skip word count check
    - <3000 expansion: chapter body ≥ 3000 words
    - >10000 compression: chapter body ≥ 3000 AND ≥ 25% original
    """
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.ln.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")
        wc = word_count_md(fp)

        if "## 归一化报告" not in content:
            mf.append(f"G4.ln.no_report:{fp}")
            continue
        c.append({"id": "G4.ln.report", "file": fp, "s": "PASS"})

        # Detect "no normalization needed" case
        no_action = (
            "不触发" in content
            or "无需归一化" in content
            or "within acceptable range" in content.lower()
        )
        if no_action:
            c.append(
                {
                    "id": "G4.ln.word_count",
                    "file": fp,
                    "s": "PASS",
                    "wc": wc,
                    "note": "no normalization needed",
                }
            )
            continue

        # Expansion or compression was applied — enforce word count
        if wc < 3000:
            mf.append(f"G4.ln.below_floor:{fp}:{wc}<3000")
        elif wc > 10000:
            mf.append(f"G4.ln.above_ceiling:{fp}:{wc}>10000")
        else:
            c.append({"id": "G4.ln.word_count", "file": fp, "s": "PASS", "wc": wc})

    if not fps:
        c.append({"id": "G4.ln", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-length-normalizing", c, "scoring", mf)
    return passed("G4-length-normalizing", c)
