"""G4 checker for shenbi-plot-thread-weaver."""

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


def g4_plot_thread_weaver(fps, rd=None):
    """Plot thread weaver: A/B/C lines, thread advancement table, blank detection."""
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    tm = pd / "outline" / "thread_map.md"
    if not tm.exists():
        mf.append("G4.thread.not_found")
    else:
        content = tm.read_text(encoding="utf-8")
        # A线/B线/C线
        lines_found = []
        for label in ["A 长线", "B 中线", "C 短线", "## A", "## B", "## C"]:
            if label in content:
                lines_found.append(label)
        if not lines_found:
            mf.append("G4.pt.lines:missing_A/B/C")
        else:
            c.append({"id": "G4.pt.lines", "s": "PASS", "found": lines_found[:3]})

        # 线索推进表 (table format)
        table_rows = len(re.findall(r"^\|.+\|$", content, re.MULTILINE))
        if table_rows < 3:
            mf.append(f"G4.pt.table:{table_rows}<3")
        else:
            c.append({"id": "G4.pt.table", "s": "PASS", "rows": table_rows})

        # 空白检测
        if "空白" not in content:
            mf.append("G4.pt.blank_detection")
        else:
            c.append({"id": "G4.pt.blank_detection", "s": "PASS"})

    if mf:
        return fail("G4-plot-thread-weaver", c, "scoring", mf)
    return passed("G4-plot-thread-weaver", c)
