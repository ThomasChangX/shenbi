"""G4 checker for shenbi-context-composing."""

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


def g4_context_composing(fps, rd=None):
    """Context composing: P1-P7 labels present, P1+P2 non-empty."""
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.cc.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # P1-P7 labels present
        p_labels = []
        for i in range(1, 8):
            if f"P{i}" in content:
                p_labels.append(f"P{i}")
        if len(p_labels) < 7:
            missing = [f"P{i}" for i in range(1, 8) if f"P{i}" not in content]
            mf.append(f"G4.cc.labels:missing_{missing}")
        else:
            c.append({"id": "G4.cc.labels", "file": fp, "s": "PASS"})

        # P1+P2 non-empty (accept colon or space after label)
        p1_match = re.search(r"P1[：:\s](.*?)(?=\n\s*P2|\Z)", content, re.DOTALL)
        p2_match = re.search(r"P2[：:\s](.*?)(?=\n\s*P3|\Z)", content, re.DOTALL)
        p1_content = p1_match.group(1).strip() if p1_match else ""
        p2_content = p2_match.group(1).strip() if p2_match else ""
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
