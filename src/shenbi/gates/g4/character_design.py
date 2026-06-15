"""G4 checker for shenbi-character-design."""

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


def g4_character_design(fps: list[str], rd: str | None = None) -> str:
    """Character-design: frontmatter fields, voice_profile arrays, relationship pairs."""
    c: list[dict[str, Any]] = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)

        # protagonist.md checks
        if "protagonist" in str(fp) and pf.suffix == ".md":
            try:
                fm = yload(str(pf)) if yaml else {}
            except Exception:
                mf.append(f"G4.protag.yaml_error:{fp}")
                continue

            required_fields = [
                "name",
                "role",
                "personality_tags",
                "core_value",
                "goal_surface",
                "goal_deep",
                "fear",
                "arc_type",
                "arc_starting",
                "arc_turning",
                "arc_ending",
                "voice_profile",
            ]
            for f in required_fields:
                if (
                    f not in fm
                    or (isinstance(fm[f], (list, dict)) and not fm[f])
                    or (isinstance(fm[f], str) and not fm[f].strip())
                ):
                    mf.append(f"G4.protag.missing_{f}:{fp}")
                else:
                    c.append({"id": f"G4.protag.{f}", "s": "PASS"})

            # voice_profile sub-checks
            vp = fm.get("voice_profile", {})
            if isinstance(vp, dict):
                thresholds = {
                    "speech_patterns": 2,
                    "catchphrases": 1,
                    "avoid_patterns": 1,
                }
                for arr_name, min_len in thresholds.items():
                    val = vp.get(arr_name, [])
                    if not isinstance(val, list) or len(val) < min_len:
                        mf.append(
                            f"G4.voice.{arr_name}:need_{min_len}_got_{len(val) if isinstance(val, list) else 0}"
                        )
                    else:
                        c.append(
                            {
                                "id": f"G4.voice.{arr_name}",
                                "s": "PASS",
                                "count": len(val),
                            }
                        )
            else:
                mf.append("G4.voice.not_a_dict")

        # relationships.md checks
        if "relationships" in str(fp) and pf.suffix == ".md":
            content = pf.read_text(encoding="utf-8")
            # Count ## 关系对 headings (not table rows — bug fix #5)
            rel_pairs = len(re.findall(r"## 关系对", content))
            if rel_pairs < 3:
                mf.append(f"G4.rel.pairs:need_3_got_{rel_pairs}")
            else:
                c.append({"id": "G4.rel.pairs", "s": "PASS", "count": rel_pairs})

        # Check for major character files (SKILL.md Writes: characters/major/*.md)
        project_dir = str(Path(fps[0]).parent.parent) if fps else ""
        major_dir = Path(project_dir) / "characters" / "major"
        if major_dir.exists():
            major_files = list(major_dir.glob("*.md"))
            if len(major_files) >= 2:
                c.append({"id": "G4.cd.major_chars", "s": "PASS", "count": len(major_files)})
            else:
                mf.append(f"G4.cd.major_chars:need_2_got_{len(major_files)}")
        else:
            mf.append("G4.cd.major_dir.not_found")

    if mf:
        return fail("G4-character-design", c, "scoring", mf)
    return passed("G4-character-design", c)
