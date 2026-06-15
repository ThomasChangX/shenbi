"""G4 checker for shenbi-power-system."""

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


def g4_power_system(fps, rd=None):
    """Power system: level table (>=5 rows), advancement rules, ability boundaries,
    cost mechanism, power ceiling, cross-level combat reference.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    ps = pd / "world" / "power_system.md"
    if not ps.exists():
        mf.append("G4.ps.not_found")
    else:
        content = ps.read_text(encoding="utf-8")
        # 等级表: table with >= 5 rows
        table_rows = len(re.findall(r"^\|.+\|$", content, re.MULTILINE))
        if table_rows < 5:
            mf.append(f"G4.ps.level_table_rows:{table_rows}<5")
        else:
            c.append({"id": "G4.ps.level_table", "s": "PASS", "rows": table_rows})

        # 进阶规则
        if not re.search(r"进阶规则|## 进阶|进阶级", content):
            mf.append("G4.ps.advancement_rules")
        else:
            c.append({"id": "G4.ps.advancement", "s": "PASS"})

        # 能力边界
        if not re.search(r"能力边界|能做|不能做", content):
            mf.append("G4.ps.ability_boundaries")
        else:
            c.append({"id": "G4.ps.boundaries", "s": "PASS"})

        # 代价机制
        if not re.search(r"代价机制|## 代价|代价类型", content):
            mf.append("G4.ps.cost")
        else:
            c.append({"id": "G4.ps.cost", "s": "PASS"})

        # 力量天花板
        if not re.search(r"力量上限|力量天花板|顶端|最高境界", content):
            mf.append("G4.ps.ceiling")
        else:
            c.append({"id": "G4.ps.ceiling", "s": "PASS"})

        # 跨级战斗参考
        if not re.search(r"跨级战斗|越级", content):
            mf.append("G4.ps.cross_level")
        else:
            c.append({"id": "G4.ps.cross_level", "s": "PASS"})

    if mf:
        return fail("G4-power-system", c, "scoring", mf)
    return passed("G4-power-system", c)
