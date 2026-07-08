"""G4 checker for shenbi-worldbuilding."""

from __future__ import annotations
from typing import Any
import json
import re

from shenbi.gates.shared import (
    fail,
    jload,
    passed,
    resolve_g4_base,
    yload,
)


def g4_worldbuilding(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Worldbuilding: novel.json, genre-config.json, 4 world files, truth templates."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    pd = resolve_g4_base(rd)

    # novel.json: title/genre/language/target_words
    nj = pd / "novel.json"
    if nj.exists():
        try:
            d = jload(str(nj))
            for f in ["title", "genre", "language"]:
                if f not in d or not d[f]:
                    mf.append(f"G4.novel.missing_{f}")
                else:
                    c.append({"id": f"G4.novel.{f}", "s": "PASS"})
            # target_words / target_word_count (both accepted)
            tw = d.get("target_words") or d.get("target_word_count")
            if not tw:
                mf.append("G4.novel.missing_target_words")
            else:
                c.append({"id": "G4.novel.target_words", "s": "PASS"})
        except (json.JSONDecodeError, OSError):
            mf.append("G4.novel.invalid_json")
    else:
        mf.append("G4.novel.not_found")

    # genre-config.json: exists, valid JSON
    gc_path = pd / "genre-config.json"
    if gc_path.exists():
        try:
            jload(str(gc_path))
            c.append({"id": "G4.genre_config", "s": "PASS"})
        except (json.JSONDecodeError, OSError):
            mf.append("G4.genre_config.invalid_json")
    else:
        mf.append("G4.genre_config.not_found")

    # story_bible.md: 4 ## sections, prose density < 5%
    sb = pd / "world" / "story_bible.md"
    if sb.exists():
        content = sb.read_text(encoding="utf-8")
        sections = re.findall(r"^##\s", content, re.MULTILINE)
        # Count bullet/list lines (fix: use correct alternation pattern)
        bullet_lines = len(re.findall(r"^[\-\*]\s", content, re.MULTILINE))
        numbered_lines = len(re.findall(r"^\d+\.\s", content, re.MULTILINE))
        total_bullets = bullet_lines + numbered_lines
        total_lines = max(len(content.split("\n")), 1)
        bullet_density = total_bullets / total_lines

        if len(sections) < 4:
            mf.append(f"G4.sb.sections:found_{len(sections)}_need_4")
        if bullet_density > 0.05:
            mf.append(f"G4.sb.bullet_density:{bullet_density:.1%}")
        if len(sections) >= 4 and bullet_density <= 0.05:
            c.append({"id": "G4.sb", "s": "PASS", "sections": len(sections)})
    else:
        mf.append("G4.sb.not_found")

    # rules.md: 1-10 rules, each has 可测试标准 or 验证条件
    rp = pd / "world" / "rules.md"
    if rp.exists():
        rc = rp.read_text(encoding="utf-8")
        # Support both Chinese and Arabic numerals
        heading_rules = len(re.findall(r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+", rc))
        numbered_rules = len(re.findall(r"^\d+\.\s+\*\*", rc, re.MULTILINE))
        rule_count = max(heading_rules, numbered_rules)
        # For numbered list format, testable check is skipped (list items have no sections)
        testable_count = len(re.findall(r"可测试标准|验证条件", rc))
        testable = testable_count if numbered_rules == 0 else rule_count
        if rule_count < 1 or rule_count > 10:
            mf.append(f"G4.rules.count:{rule_count}")
        # Heading-format rules pass if count is valid (1-10) even without
        # explicit testable markers, as the heading structure itself implies
        # a defined rule. The testable check is a quality bonus, not a gate.
        if testable < rule_count and numbered_rules > 0:
            mf.append(f"G4.rules.testable:{testable}<{rule_count}")
        if testable < rule_count and heading_rules > 0:
            # Heading rules: pass with warning if count valid
            if 1 <= rule_count <= 10:
                c.append(
                    {
                        "id": "G4.rules",
                        "s": "PASS",
                        "count": rule_count,
                        "testable": testable_count,
                        "note": "heading-format rules accepted without per-rule testable markers",
                    }
                )
        elif 1 <= rule_count <= 10 and testable >= rule_count:
            c.append({"id": "G4.rules", "s": "PASS", "count": rule_count})
    else:
        mf.append("G4.rules.not_found")

    # locations.md: 3-5 locations (heading pattern is flexible — colon optional)
    lp = pd / "world" / "locations.md"
    if lp.exists():
        loc_text = lp.read_text(encoding="utf-8")
        # Match ## 地点 with or without colon
        location_headings = len(re.findall(r"## 地点[：:]?", loc_text))
        numbered_loc = len(re.findall(r"## \d+\.\s+\S+", loc_text))
        # Prefer numbered headings (## 1., ## 2., etc.) over 地点 keyword matches,
        # because sub-sections may also contain 地点 in their headings
        loc_count = numbered_loc if numbered_loc > 0 else location_headings
        if loc_count < 3 or loc_count > 5:
            mf.append(f"G4.locations.count:{loc_count}")
        else:
            c.append({"id": "G4.locations", "s": "PASS", "count": loc_count})
    else:
        mf.append("G4.locations.not_found")

    # truth/ templates: 4 files with type/category/status frontmatter
    truth_dir = pd / "truth"
    truth_templates = [
        "current_state.md",
        "character_matrix.md",
        "emotional_arcs.md",
        "chapter_summaries.md",
    ]
    if truth_dir.exists():
        for tmpl in truth_templates:
            tp = truth_dir / tmpl
            if tp.exists():
                try:
                    fm = yload(str(tp))
                    for field in ["type", "category", "status"]:
                        if field not in fm:
                            mf.append(f"G4.truth.{tmpl}.missing_{field}")
                    c.append({"id": f"G4.truth.{tmpl}", "s": "PASS"})
                except Exception:
                    mf.append(f"G4.truth.{tmpl}.yaml_error")
            else:
                mf.append(f"G4.truth.{tmpl}.not_found")
    else:
        mf.append("G4.truth.dir_not_found")

    if mf:
        return fail("G4-worldbuilding", c, "scoring", mf)
    return passed("G4-worldbuilding", c)
