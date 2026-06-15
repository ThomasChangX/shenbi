"""G4 checker for shenbi-pacing-design."""

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


def g4_pacing_design(fps, rd=None):
    """Pacing design: 4-beat cycle, 3-line ratio table (QUEST/FIRE/CONSTELLATION),
    >= 6 scene types, monotony detection rules.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    rp = pd / "outline" / "rhythm_principles.md"
    if not rp.exists():
        mf.append("G4.rhythm.not_found")
    else:
        content = rp.read_text(encoding="utf-8")
        # 四拍循环
        beats = ["铺垫", "升级", "爆发", "余波"]
        missing_beats = [b for b in beats if b not in content]
        if missing_beats:
            mf.append(f"G4.pd.beats:missing_{missing_beats}")
        else:
            c.append({"id": "G4.pd.beats", "s": "PASS"})

        # 三线比例 (QUEST/FIRE/CONSTELLATION)
        has_quest = "QUEST" in content
        has_fire = "FIRE" in content
        has_const = "CONSTELLATION" in content
        if not (has_quest and has_fire and has_const):
            mf.append("G4.pd.three_lines:incomplete")
        else:
            c.append({"id": "G4.pd.three_lines", "s": "PASS"})

        # >= 6 scene types
        scene_matches = re.findall(
            r"(?:战斗|对话|日常|探索|修炼|阴谋|逃亡|揭示|情感|智斗)", content
        )
        unique_scenes = len(set(scene_matches)) if scene_matches else 0
        if unique_scenes < 6:
            mf.append(f"G4.pd.scene_types:{unique_scenes}<6")
        else:
            c.append({"id": "G4.pd.scene_types", "s": "PASS", "types": unique_scenes})

        # 单调性检测规则 (only check for the specific term)
        if "单调性" not in content:
            mf.append("G4.pd.monotony")
        else:
            c.append({"id": "G4.pd.monotony", "s": "PASS"})

    if mf:
        return fail("G4-pacing-design", c, "scoring", mf)
    return passed("G4-pacing-design", c)
