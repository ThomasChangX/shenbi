"""G4 checker for shenbi-story-architecture."""

from __future__ import annotations
from typing import Any
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


def g4_story_architecture(fps: list[str], rd: str | None = None) -> str:
    """Story architecture: story_frame frontmatter conflicts, volume_map Objective+KR."""
    c: list[dict[str, Any]] = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    # story_frame.md: frontmatter with surface/personal/deep conflicts
    sf = pd / "outline" / "story_frame.md"
    if sf.exists():
        try:
            fm = yload(str(sf)) if yaml else {}
            for field in ["surface_conflict", "personal_conflict", "deep_conflict"]:
                val = fm.get(field, "")
                if not val or (isinstance(val, str) and not val.strip()):
                    mf.append(f"G4.sf.missing_{field}")
                else:
                    c.append({"id": f"G4.sf.{field}", "s": "PASS"})
        except Exception:
            mf.append("G4.sf.yaml_error")
    else:
        mf.append("G4.sf.not_found")

    # volume_map.md: >= 1 volume with Objective + Key Results
    vm = pd / "outline" / "volume_map.md"
    if vm.exists():
        content = vm.read_text(encoding="utf-8")
        volumes = re.findall(r"## 第[一二三四五六七八九十\d]+卷", content)
        volumes_with_obj = 0
        for vol_match in re.finditer(
            r"## 第[一二三四五六七八九十\d]+卷[：:].*?\n(?=## 第[一二三四五六七八九十\d]+卷|\Z)",
            content,
            re.DOTALL,
        ):
            vol_text = vol_match.group()
            has_obj = bool(re.search(r"\*\*Objective\*\*", vol_text))
            has_kr = bool(re.search(r"Key\s*Results?", vol_text))
            if has_obj and has_kr:
                volumes_with_obj += 1
        if len(volumes) < 1:
            mf.append("G4.volumes.count:0")
        elif volumes_with_obj < 1:
            mf.append(f"G4.volumes.obj_kr:{volumes_with_obj}/{len(volumes)}")
        else:
            c.append(
                {
                    "id": "G4.volumes",
                    "s": "PASS",
                    "count": len(volumes),
                    "with_obj_kr": volumes_with_obj,
                }
            )
    else:
        mf.append("G4.volumes.not_found")

    # rhythm_principles.md: must exist (created by story-architecture, updated by pacing-design)
    rp_path = pd / "outline" / "rhythm_principles.md"
    if rp_path.exists():
        rp_content = rp_path.read_text(encoding="utf-8")
        if len(rp_content.strip()) > 0:
            c.append({"id": "G4.sa.rhythm_principles", "s": "PASS"})
        else:
            mf.append("G4.sa.rhythm_principles.empty")
    else:
        mf.append("G4.sa.rhythm_principles.not_found")

    if mf:
        return fail("G4-story-architecture", c, "scoring", mf)
    return passed("G4-story-architecture", c)
