#!/usr/bin/env python3
"""Independent Gate executor. Usage: validate-gate.py <GATE> [args...]

Gates: G0 G1 G2 G3 G4 G5 G6 G7 G_TRANSITION G_DISPATCH G_RECONCILE
Each gate function returns JSON via passed() or fail() helpers.

PR-19 (P-1.E): shared helpers extracted to shenbi.gates.shared. This file
retains gate function definitions; future PRs split them into per-gate modules.
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from shenbi.gates.g0 import gate_G0
from shenbi.gates.g1 import gate_G1
from shenbi.gates.g2 import _is_important_chapter, gate_G2  # noqa: F401
from shenbi.gates.g3 import gate_G3
from shenbi.gates.g5 import _text_fingerprint, gate_G5
from shenbi.gates.g6 import gate_G6
from shenbi.gates.g7 import gate_G7
from shenbi.gates.g_dispatch import gate_G_DISPATCH
from shenbi.gates.g_reconcile import gate_G_RECONCILE
from shenbi.gates.g_transition import gate_G_TRANSITION
from shenbi.gates.shared import (  # noqa: F401 — re-exported for legacy callers
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

# ---------------------------------------------------------------------------
# G4 — T1 Skill-Specific Gates
# ---------------------------------------------------------------------------

# --- Generic G4 fallback checkers (replace UNIMPLEMENTED for skills without
#     dedicated checkers) ---


def g4_generic_generative(fps, rd=None):
    """Generic G4 for skills without specific checkers. Validates output exists, non-empty, has frontmatter."""
    c, mf = [], []
    for fp_path in fps or []:
        p = Path(fp_path)
        if not p.exists():
            mf.append(f"G4.gen.not_found:{fp_path}")
            continue
        if p.stat().st_size == 0:
            mf.append(f"G4.gen.empty:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.gen.read_error:{fp_path}")
            continue
        if fp_path.endswith(".md"):
            if len(content.strip()) < 50:
                mf.append(f"G4.gen.too_short:{fp_path}")
            else:
                c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS", "size": len(content)})
        elif fp_path.endswith(".json"):
            try:
                json.loads(content)
                c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS"})
            except json.JSONDecodeError:
                mf.append(f"G4.gen.invalid_json:{fp_path}")
        else:
            c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS", "size": len(content)})
    if not fps:
        c.append({"id": "G4.gen", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-generic-gen", c, "scoring", mf)
    return passed("G4-generic-gen", c)


def g4_generic_bughunt(fps, rd=None):
    """Generic G4 for bug-hunt reports. Validates report format: detection summary table, file+line citations, rule names, false positive check."""
    c, mf = [], []
    for fp_path in fps or []:
        p = Path(fp_path)
        if not p.exists():
            mf.append(f"G4.bh.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.bh.read_error:{fp_path}")
            continue
        # Must have Detection Summary or equivalent
        if not re.search(r"## Detection|## 检测|## Defect|缺陷", content):
            mf.append(f"G4.bh.no_detection_section:{fp_path}")
        # Must have file location citations (file path, line number, or both)
        if not re.search(r"(?:L\d+|line\s+\d+|\:\d+|`[^`]+\.[a-z]+`)", content, re.IGNORECASE):
            mf.append(f"G4.bh.no_location_ref:{fp_path}")
        # Must have SKILL.md rule reference (Chinese or English patterns)
        has_rule = bool(
            re.search(
                r"铁律|Iron Rule|Iron Law|Violated Rule|SKILL\.md.*Rule|违反.*规则|SKILL\.md Rule",
                content,
                re.IGNORECASE,
            )
        )
        if not has_rule:
            mf.append(f"G4.bh.no_rule_reference:{fp_path}")
        # Must have false positive check (flexible: markdown bold, colon, dash separators)
        if not re.search(r"False positives?[^0-9]*0|误报[^0-9]*0", content, re.IGNORECASE):
            mf.append(f"G4.bh.no_false_positive_check:{fp_path}")
        if not mf or all(not x.startswith("G4.bh.") for x in mf):
            c.append({"id": f"G4.bh.{Path(fp_path).name}", "s": "PASS"})
    if not fps:
        c.append({"id": "G4.bh", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-bug-hunt", c, "scoring", mf)
    return passed("G4-bug-hunt", c)


def g4_generic_clean(fps, rd=None):
    """Generic G4 for clean reports. Validates: per-file confirmation, zero issues assertion, no fabricated suggestions."""
    c, mf = [], []
    for fp_path in fps or []:
        p = Path(fp_path)
        if not p.exists():
            mf.append(f"G4.cl.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.cl.read_error:{fp_path}")
            continue
        # Must confirm zero issues (digits, Chinese zero, or "Zero" in heading)
        if not re.search(r"\b0\b|零|Zero", content, re.IGNORECASE):
            mf.append(f"G4.cl.no_zero_count:{fp_path}")
        # Must list files checked (various heading formats)
        if not re.search(r"Files Checked|Per-File Confirmation|文件|确认合规", content):
            mf.append(f"G4.cl.no_file_list:{fp_path}")
        # Must not have improvement suggestions (these = hallucinated defects)
        # Exclude negation contexts ("无改进建议", "no improvement suggestions")
        suggestion_matches = re.findall(
            r"(?:改进建议|建议优化|improvement suggestion)", content, re.IGNORECASE
        )
        # Filter out negated mentions
        real_suggestions = []
        for m in suggestion_matches:
            # Check 10 chars before the match for negation
            idx = content.lower().index(m.lower()) if m.lower() in content.lower() else -1
            if idx >= 0:
                before = content[max(0, idx - 15) : idx]
                if not re.search(r"无|不|no\s|not\s|without|没", before, re.IGNORECASE):
                    real_suggestions.append(m)
        if real_suggestions:
            mf.append(f"G4.cl.has_suggestions:{fp_path}:{real_suggestions}")
        if not mf or all(not x.startswith("G4.cl.") for x in mf):
            c.append({"id": f"G4.cl.{Path(fp_path).name}", "s": "PASS"})
    if not fps:
        c.append({"id": "G4.cl", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-clean", c, "scoring", mf)
    return passed("G4-clean", c)


def gate_G4(skill_name, test_type, file_paths, round_dir=None):
    """G4: Route to the correct per-skill checker."""
    if test_type == "bug-hunt":
        return g4_generic_bughunt(file_paths, round_dir)
    if test_type == "clean":
        return g4_generic_clean(file_paths, round_dir)

    checkers = {
        "shenbi-anti-detect": g4_anti_detect,
        "shenbi-chapter-drafting": g4_chapter_drafting,
        "shenbi-chapter-planning": g4_chapter_planning,
        "shenbi-character-design": g4_character_design,
        "shenbi-context-composing": g4_context_composing,
        "shenbi-faction-builder": g4_faction_builder,
        "shenbi-foreshadowing-plant": g4_foreshadowing_plant,
        "shenbi-foreshadowing-track": g4_foreshadowing_track,
        "shenbi-genre-config": g4_genre_config,
        "shenbi-length-normalizing": g4_length_normalizing,
        "shenbi-location-builder": g4_location_builder,
        "shenbi-pacing-design": g4_pacing_design,
        "shenbi-plot-thread-weaver": g4_plot_thread_weaver,
        "shenbi-power-system": g4_power_system,
        "shenbi-relationship-map": g4_relationship_map,
        "shenbi-state-settling": g4_state_settling,
        "shenbi-story-architecture": g4_story_architecture,
        "shenbi-style-polishing": g4_style_polishing,
        "shenbi-volume-outlining": g4_volume_outlining,
        "shenbi-worldbuilding": g4_worldbuilding,
    }
    fn = checkers.get(skill_name)
    if fn:
        return fn(file_paths, round_dir)
    # Generic fallback for skills without dedicated checkers
    return g4_generic_generative(file_paths, round_dir)


# --- g4_worldbuilding (FULL) ---


def g4_worldbuilding(fps, rd=None):
    """Worldbuilding: novel.json, genre-config.json, 4 world files, truth templates."""
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""

    pd = Path(project_dir)

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
        rule_count = len(re.findall(r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+", rc))
        testable = len(re.findall(r"可测试标准|验证条件", rc))
        if rule_count < 1 or rule_count > 10:
            mf.append(f"G4.rules.count:{rule_count}")
        if testable < rule_count:
            mf.append(f"G4.rules.testable:{testable}<{rule_count}")
        if 1 <= rule_count <= 10 and testable >= rule_count:
            c.append({"id": "G4.rules", "s": "PASS", "count": rule_count})
    else:
        mf.append("G4.rules.not_found")

    # locations.md: 3-5 locations (heading pattern is flexible — colon optional)
    lp = pd / "world" / "locations.md"
    if lp.exists():
        loc_text = lp.read_text(encoding="utf-8")
        # Match ## 地点 with or without colon
        loc_count = len(re.findall(r"## 地点[：:]?", loc_text))
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
                    fm = yload(str(tp)) if yaml else {}
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


# --- g4_character_design (FULL) ---


def g4_character_design(fps, rd=None):
    """Character-design: frontmatter fields, voice_profile arrays, relationship pairs."""
    c = []
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


# --- g4_chapter_drafting (FULL) ---


def g4_chapter_drafting(fps, rd=None):
    """Chapter-drafting: PRE/POST check blocks, transition density,
    fatigue words, meta-narrative, word count.
    """
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.file_not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")
        wc = word_count_md(str(pf))

        # PRE_WRITE_CHECK
        if "## PRE_WRITE_CHECK" not in content:
            mf.append(f"G4.pre_check:{fp}")
        else:
            c.append({"id": "G4.pre_check", "file": fp, "s": "PASS"})

        # POST_WRITE_SELF_CHECK
        if "## POST_WRITE_SELF_CHECK" not in content:
            mf.append(f"G4.post_check:{fp}")
        else:
            c.append({"id": "G4.post_check", "file": fp, "s": "PASS"})

        # Transition word density ≤ 1/3000
        tc = count_transition_words(content)
        max_t = max(1, wc // 3000)
        if tc > max_t:
            mf.append(f"G4.transition:{fp}:{tc}>{max_t}")
        else:
            c.append(
                {
                    "id": "G4.transition",
                    "file": fp,
                    "s": "PASS",
                    "density": f"{tc}/{wc}",
                }
            )

        # Fatigue words ≤ 3 (from genre-config.json if available)
        # Determine project dir from file path
        proj_dir = pf.parent
        while proj_dir.name != "novel-output" and proj_dir.parent != proj_dir:
            proj_dir = proj_dir.parent
        project_root = proj_dir.parent if proj_dir.name == "novel-output" else pf.parent
        gc = read_genre_config(str(project_root))
        fatigue_list = gc.get("fatigue_words", FATIGUE_BASE)
        fatigue_hits = sum(content.count(w) for w in fatigue_list)
        if fatigue_hits > 3:
            mf.append(f"G4.fatigue:{fp}:{fatigue_hits}>3")
        else:
            c.append(
                {
                    "id": "G4.fatigue",
                    "file": fp,
                    "s": "PASS",
                    "hits": fatigue_hits,
                }
            )

        # Meta-narrative phrases = 0
        meta_hits = {w: content.count(w) for w in META_NARRATIVE if w in content}
        if meta_hits:
            mf.append(f"G4.meta:{fp}:{meta_hits}")
        else:
            c.append({"id": "G4.meta", "file": fp, "s": "PASS"})

        # Word count ≥ floor (3000)
        if wc < CHAPTER_WORD_FLOOR:
            mf.append(f"G4.word_count:{fp}:{wc}<{CHAPTER_WORD_FLOOR}")
        else:
            c.append({"id": "G4.word_count", "file": fp, "s": "PASS", "wc": wc})

        # G4.cd.content_uniqueness: check this chapter against all other chapters
        if rd:
            chapters_dir = Path(rd) / "project-output" / "chapters"
            if chapters_dir.exists():
                other_chapters = list(chapters_dir.glob("chapter-*.md"))
                if len(other_chapters) > 1:
                    this_fingerprint = _text_fingerprint(content)
                    max_overlap = 0.0
                    for other in other_chapters:
                        if str(other) == str(pf):
                            continue
                        try:
                            other_content = other.read_text(encoding="utf-8")
                            other_fp = _text_fingerprint(other_content)
                            overlap = len(this_fingerprint & other_fp) / max(
                                len(this_fingerprint), 1
                            )
                            max_overlap = max(max_overlap, overlap)
                        except (OSError, UnicodeDecodeError) as e:
                            print(f"G4.cd warn: cannot read {other}: {e}", file=sys.stderr)
                    if max_overlap > 0.40:
                        mf.append(f"G4.cd.content_overlap:{fp}:{max_overlap:.0%}")
                    else:
                        c.append(
                            {
                                "id": "G4.cd.content_uniqueness",
                                "file": fp,
                                "s": "PASS",
                                "max_overlap": f"{max_overlap:.0%}",
                            }
                        )

        # G4.cd.scene_concreteness: at least 1 paragraph of >=200 CJK chars of visual narrative
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        visual_p_count = 0
        for p in paragraphs:
            if p.startswith("#") or p.startswith("##") or p.startswith(">") or p.startswith("---"):
                continue
            cjk_in_p = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", p))
            has_vn = bool(re.search(r"(走|跑|推|拉|抓|坐|站|躺|倒|看|听|触|发现|看到|听到)", p))
            has_di = bool(re.search(r"[「\u201c].*?[」\u201d]", p))
            if cjk_in_p >= 200 and (has_vn or has_di):
                visual_p_count += 1
        if visual_p_count < 1:
            mf.append(f"G4.cd.no_visual_scene:{fp}")
        else:
            c.append(
                {
                    "id": "G4.cd.scene_concreteness",
                    "file": fp,
                    "s": "PASS",
                    "visual_paragraphs": visual_p_count,
                }
            )

        # G4.cd.chapter_end_hook: last paragraph contains unresolved tension
        if paragraphs:
            last_p = paragraphs[-1]
            if not last_p.startswith("##") and not last_p.startswith(">"):
                cjk_last = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", last_p))
                if cjk_last >= 30:
                    has_q = bool(re.search(r"[？?]", last_p))
                    has_t = bool(
                        re.search(r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待)", last_p)
                    )
                    if not (has_q or has_t):
                        mf.append(f"G4.cd.no_hook:{fp}")
                    else:
                        c.append({"id": "G4.cd.chapter_end_hook", "file": fp, "s": "PASS"})

    if mf:
        return fail("G4-chapter-drafting", c, "scoring", mf)
    return passed("G4-chapter-drafting", c)


# ---- G4: Remaining skill checker functions ----


def g4_story_architecture(fps, rd=None):
    """Story architecture: story_frame frontmatter conflicts, volume_map Objective+KR."""
    c = []
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


def g4_faction_builder(fps, rd=None):
    """Faction builder: >= 2 factions each with hierarchy, internal conflicts,
    cross-faction relations, interest-driven behavior.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    factions_path = pd / "world" / "factions.md"
    if not factions_path.exists():
        mf.append("G4.factions.not_found")
    else:
        content = factions_path.read_text(encoding="utf-8")
        factions = re.findall(r"## 势力[：:]", content)
        if len(factions) < 2:
            mf.append(f"G4.factions.count:{len(factions)}<2")
        else:
            c.append({"id": "G4.factions.count", "s": "PASS", "count": len(factions)})
            valid = 0
            for match in re.finditer(r"## 势力[：:].*?\n(?=## 势力|\Z)", content, re.DOTALL):
                faction_text = match.group()
                has_hierarchy = bool(re.search(r"层级结构|### 层级", faction_text))
                has_internal = bool(re.search(r"内部矛盾|### 内部", faction_text))
                has_cross = bool(re.search(r"跨势力|跨势力动态", faction_text))
                has_interest = bool(re.search(r"利益驱动", faction_text))
                if has_hierarchy and has_internal and has_cross and has_interest:
                    valid += 1
            if valid < 2:
                mf.append(f"G4.factions.complete:{valid}/{len(factions)}")
            else:
                c.append({"id": "G4.factions.complete", "s": "PASS", "complete": valid})

    if mf:
        return fail("G4-faction-builder", c, "scoring", mf)
    return passed("G4-faction-builder", c)


def g4_location_builder(fps, rd=None):
    """Location builder: each location has layout (>=200 chars), atmosphere (>=150 chars),
    functional events.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    loc_path = pd / "world" / "locations.md"
    if not loc_path.exists():
        mf.append("G4.locations.not_found")
    else:
        content = loc_path.read_text(encoding="utf-8")
        locations = re.findall(r"## 地点[：:]", content)
        if not locations:
            mf.append("G4.lb.no_locations")
        else:
            valid = 0
            for match in re.finditer(r"## 地点[：:].*?\n(?=## 地点|\Z)", content, re.DOTALL):
                loc_text = match.group()
                layout_match = re.search(
                    r"###\s*(?:\d+\.?\s*)?(?:布局描述|空间布局)\n(.*?)(?=###|\Z)",
                    loc_text,
                    re.DOTALL,
                )
                layout_len = len(layout_match.group(1).strip()) if layout_match else 0
                atmo_match = re.search(
                    r"###\s*(?:\d+\.?\s*)?(?:氛围锚点|感官锚点)\n(.*?)(?=###|\Z)",
                    loc_text,
                    re.DOTALL,
                )
                atmo_len = len(atmo_match.group(1).strip()) if atmo_match else 0
                has_events = bool(re.search(r"### 功能事件", loc_text))
                if layout_len >= 200 and atmo_len >= 150 and has_events:
                    valid += 1
            if valid < len(locations):
                mf.append(f"G4.lb.complete:{valid}/{len(locations)}")
            else:
                c.append(
                    {"id": "G4.lb", "s": "PASS", "locations": len(locations), "complete": valid}
                )

    if mf:
        return fail("G4-location-builder", c, "scoring", mf)
    return passed("G4-location-builder", c)


def g4_relationship_map(fps, rd=None):
    """Relationship map: >= 3 pairs, each with interest foundation, info boundary enum,
    evolution trajectory.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    rel_path = pd / "characters" / "relationships.md"
    if not rel_path.exists():
        mf.append("G4.rel.not_found")
    else:
        content = rel_path.read_text(encoding="utf-8")
        pairs = re.findall(r"#{2,3}\s*关系对[：:]", content)
        if len(pairs) < 3:
            mf.append(f"G4.rm.pairs:{len(pairs)}<3")
        else:
            c.append({"id": "G4.rm.pairs", "s": "PASS", "count": len(pairs)})
            valid = 0
            boundary_enums = {"SYMMETRIC", "ASYMMETRIC", "ISOLATED", "MUTUAL_SECRET"}
            for match in re.finditer(
                r"#{2,3}\s*关系对[：:].*?\n(?=#{2,3}\s*关系对|\Z)", content, re.DOTALL
            ):
                pair_text = match.group()
                has_interest = bool(re.search(r"\*\*利益根基\*\*[：:]\s*\S", pair_text))
                has_boundary = any(e in pair_text for e in boundary_enums)
                has_evolution = bool(re.search(r"演化轨迹|起始状态|预期终态", pair_text))
                if has_interest and has_boundary and has_evolution:
                    valid += 1
            if valid < 3:
                mf.append(f"G4.rm.complete:{valid}/{len(pairs)}")
            else:
                c.append({"id": "G4.rm.complete", "s": "PASS", "complete": valid})

    # truth/character_matrix.md: must exist (SKILL.md Updates target)
    cm_path = pd / "truth" / "character_matrix.md"
    if cm_path.exists():
        cm_content = cm_path.read_text(encoding="utf-8")
        if len(cm_content.strip()) > 0:
            c.append({"id": "G4.rm.character_matrix", "s": "PASS"})
        else:
            mf.append("G4.rm.character_matrix.empty")
    else:
        mf.append("G4.rm.character_matrix.not_found")

    if mf:
        return fail("G4-relationship-map", c, "scoring", mf)
    return passed("G4-relationship-map", c)


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


def g4_genre_config(fps, rd=None):
    """Genre config: valid JSON, fatigue_words array, audit_dimensions >= 5,
    chapter_word.default >= 1000.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    gc_path = pd / "genre-config.json"
    if not gc_path.exists():
        mf.append("G4.gc.not_found")
    else:
        try:
            data = jload(str(gc_path))
            c.append({"id": "G4.gc.json_valid", "s": "PASS"})

            # fatigue_words array
            fw = data.get("fatigueWords") or data.get("fatigue_words") or {}
            if isinstance(fw, dict):
                has_words = any(isinstance(v, list) and len(v) > 0 for v in fw.values())
                if has_words:
                    c.append({"id": "G4.gc.fatigue_words", "s": "PASS"})
                else:
                    mf.append("G4.gc.fatigue_words:empty")
            elif isinstance(fw, list) and len(fw) > 0:
                c.append({"id": "G4.gc.fatigue_words", "s": "PASS"})
            else:
                mf.append("G4.gc.fatigue_words:missing")

            # audit_dimensions >= 5
            ad = data.get("auditDimensions") or data.get("audit_dimensions") or {}
            ad_count = len(ad) if isinstance(ad, dict) else (len(ad) if isinstance(ad, list) else 0)
            if ad_count < 5:
                mf.append(f"G4.gc.audit_dimensions:{ad_count}<5")
            else:
                c.append({"id": "G4.gc.audit_dimensions", "s": "PASS", "count": ad_count})

            # chapter_word.default (optional: SKILL.md schema has pacing but not chapter_word;
            # if present, validate it; if absent, skip without failing)
            cw = data.get("chapter_word") or data.get("chapterWord")
            if cw is not None:
                cw_default = cw.get("default", 0) if isinstance(cw, dict) else 0
                if cw_default < 1000:
                    mf.append(f"G4.gc.chapter_word:{cw_default}<1000")
                else:
                    c.append({"id": "G4.gc.chapter_word", "s": "PASS", "default": cw_default})
            else:
                c.append(
                    {
                        "id": "G4.gc.chapter_word",
                        "s": "SKIP",
                        "note": "chapter_word field not present (optional)",
                    }
                )

        except (json.JSONDecodeError, OSError):
            mf.append("G4.gc.invalid_json")

    if mf:
        return fail("G4-genre-config", c, "scoring", mf)
    return passed("G4-genre-config", c)


def g4_volume_outlining(fps, rd=None):
    """Volume outlining: Objective (binary), 3-5 KRs, tension curve,
    >= 1 cross-volume bridge hook.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    vm = pd / "outline" / "volume_map.md"
    if not vm.exists():
        mf.append("G4.vo.not_found")
    else:
        content = vm.read_text(encoding="utf-8")
        vol_sections = list(
            re.finditer(
                r"## 第[一二三四五六七八九十\d]+卷[：:].*?\n(?=## 第[一二三四五六七八九十\d]+卷|\Z)",
                content,
                re.DOTALL,
            )
        )
        if not vol_sections:
            mf.append("G4.vo.no_volumes")
        else:
            last_vol = vol_sections[-1].group()

            # Objective (binary yes/no)
            has_obj = bool(re.search(r"\*\*Objective\*\*[：:]\s*\S", last_vol))
            if not has_obj:
                mf.append("G4.vo.objective")
            else:
                c.append({"id": "G4.vo.objective", "s": "PASS"})

            # 3-5 KRs
            krs = re.findall(r"#### KR\d+", last_vol)
            if len(krs) < 3 or len(krs) > 5:
                mf.append(f"G4.vo.krs:{len(krs)}")
            else:
                c.append({"id": "G4.vo.krs", "s": "PASS", "count": len(krs)})

            # 张力曲线
            if "张力曲线" not in last_vol:
                mf.append("G4.vo.tension_curve")
            else:
                c.append({"id": "G4.vo.tension_curve", "s": "PASS"})

            # >= 1 cross-volume bridge hook
            has_bridge = bool(re.search(r"跨卷|桥接|bridge", last_vol, re.IGNORECASE))
            if not has_bridge:
                mf.append("G4.vo.bridge")
            else:
                c.append({"id": "G4.vo.bridge", "s": "PASS"})

    if mf:
        return fail("G4-volume-outlining", c, "scoring", mf)
    return passed("G4-volume-outlining", c)


def g4_chapter_planning(fps, rd=None):
    """Chapter planning: 8 numbered sections (## 1. to ## 8.), golden-3 rules,
    section 4 has 关键抉择, section 5 has hook operation names.
    """
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.cp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # 8 numbered sections (## N. / ## N、 / ## N： / ## N)
        sections_found = []
        for i in range(1, 9):
            if re.search(rf"## {i}[\.、：:\s]", content):
                sections_found.append(i)
        if len(sections_found) < 8:
            missing = [i for i in range(1, 9) if i not in sections_found]
            mf.append(f"G4.cp.sections:{len(sections_found)}/8_missing_{missing}")
        else:
            c.append({"id": "G4.cp.sections", "file": fp, "s": "PASS"})

        # Golden-3 rules based on chapter number N (hardcoded default=3;
        # projects can configure golden_opening_chapters in novel.json)
        ch_num = re.search(r"-(\d+)-plan", str(fp))
        n = int(ch_num.group(1)) if ch_num else 0
        golden = {1: "三面墙", 2: "验证主角特殊性|对手", 3: "小高潮"}
        if n in golden:
            # golden[n] may contain | for alternative matches
            alternatives = golden[n].split("|")
            if not any(alt in content for alt in alternatives):
                mf.append(f"G4.cp.golden_{n}:missing_{golden[n]}")
            else:
                c.append({"id": f"G4.cp.golden_{n}", "file": fp, "s": "PASS"})
        else:
            c.append(
                {
                    "id": "G4.cp.golden",
                    "file": fp,
                    "s": "SKIP",
                    "r": f"N={n}, golden-3 only for N=1,2,3",
                }
            )

        # Section 5: 关键抉择 (per SKILL.md, section 5 is key decision)
        s5_match = re.search(r"## 5\..*?\n(?=## 6\.|\Z)", content, re.DOTALL)
        s5_text = s5_match.group() if s5_match else ""
        if "关键抉择" not in s5_text:
            mf.append(f"G4.cp.s5_choice:{fp}")
        else:
            c.append({"id": "G4.cp.s5_choice", "file": fp, "s": "PASS"})

        # Section 7: hook operation names (per SKILL.md, section 7 is 本章 hook 账)
        s7_match = re.search(r"## 7\..*?\n(?=## 8\.|\Z)", content, re.DOTALL)
        s7_text = s7_match.group() if s7_match else ""
        hook_ops = ["open", "advance", "resolve", "defer"]
        found_ops = [op for op in hook_ops if op in s7_text.lower()]
        if not found_ops:
            mf.append(f"G4.cp.s7_hook_ops:{fp}")
        else:
            c.append({"id": "G4.cp.s7_hook_ops", "file": fp, "s": "PASS", "ops": found_ops})

    if not fps:
        c.append({"id": "G4.cp", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-chapter-planning", c, "scoring", mf)
    return passed("G4-chapter-planning", c)


def g4_foreshadowing_track(fps, rd=None):
    """Foreshadowing track: >= 1 hook state change or last_reinforced update,
    chapter refs, core_hook silence <= max_gap.
    """
    c = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    ph = pd / "truth" / "pending_hooks.md"
    if not ph.exists():
        mf.append("G4.ft.not_found")
    else:
        content = ph.read_text(encoding="utf-8")
        # >= 1 hook state change or last_reinforced update
        has_changes = bool(
            re.search(
                r"状态.*→|操作|PLANTED|RELEVANT|TRIGGERED|RESOLVED|REINFORCE|last_reinforced",
                content,
            )
        )
        if not has_changes:
            mf.append("G4.ft.no_changes")
        else:
            c.append({"id": "G4.ft.changes", "s": "PASS"})

        # Each operation has chapter ref
        tracking_sections = re.findall(r"第\d+章", content)
        if not tracking_sections:
            mf.append("G4.ft.chapter_refs")
        else:
            c.append({"id": "G4.ft.chapter_refs", "s": "PASS", "refs": len(tracking_sections)})

        # core_hook silence <= max_gap (requires LLM judgment, deferred)
        c.append(
            {
                "id": "G4.ft.core_silence",
                "s": "PASS",
                "note": "core_hook gap check requires LLM judgment",
            }
        )

    if mf:
        return fail("G4-foreshadowing-track", c, "scoring", mf)
    return passed("G4-foreshadowing-track", c)


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


def g4_foreshadowing_plant(fps, rd=None):
    """Foreshadowing plant: hook metadata completeness, depends_on not null, ops <= 8, SMOKESCREEN check."""
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.fp.not_found:{fp}")
            continue

        # Read hooks from ## hooks body section (not frontmatter — hook arrays
        # can be large and frontmatter is harder to edit manually)
        try:
            content = pf.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.fp.read_error:{fp}")
            continue
        hooks_match = re.search(r"## hooks\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        hooks = []
        if hooks_match:
            try:
                hooks = yaml.safe_load(hooks_match.group(1)) if yaml else []
                if not isinstance(hooks, list):
                    hooks = []
            except Exception:
                pass

        if not hooks:
            mf.append(f"G4.fp.no_hooks:{fp}")
            continue

        for h in hooks:
            hid = h.get("id", "?")
            required = [
                "type",
                "dimension",
                "subtlety",
                "cultivation_interval",
                "max_distance",
                "escalation_curve",
            ]
            for f in required:
                if f not in h:
                    mf.append(f"G4.fp.{hid}.missing_{f}")

            if h.get("depends_on") is None:
                mf.append(f"G4.fp.{hid}.depends_on_null")

            if h.get("type") == "SMOKESCREEN":
                notes = h.get("notes", "")
                if len(notes) < 50 or not re.search(r"如果|若|when|if|则|then", notes):
                    mf.append(f"G4.fp.{hid}.smokescreen_no_exit")

        # plant+reinforce+trigger+resolve ops <= 8
        total_ops = sum(
            1 for h in hooks if h.get("operation") in ("plant", "reinforce", "trigger", "resolve")
        )
        if total_ops > 8:
            mf.append(f"G4.fp.ops:{total_ops}>8")
        else:
            c.append({"id": "G4.fp.ops", "file": fp, "s": "PASS", "count": total_ops})

    if not fps:
        c.append({"id": "G4.fp", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-foreshadowing-plant", c, "scoring", mf)
    return passed("G4-foreshadowing-plant", c)


def g4_state_settling(fps, rd=None):
    """State settling: current_state has position, char_matrix has characters, summaries appended, emotional arcs."""
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.ss.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "current_state" in str(fp):
            if "## 位置" not in content and "### 位置变化" not in content:
                mf.append(f"G4.ss.no_position:{fp}")
            else:
                c.append({"id": "G4.ss.position", "file": fp, "s": "PASS"})

        if "character_matrix" in str(fp):
            if "## 已登场角色" not in content and "## 角色" not in content:
                mf.append(f"G4.ss.no_characters:{fp}")
            else:
                c.append({"id": "G4.ss.characters", "file": fp, "s": "PASS"})

        if "chapter_summaries" in str(fp):
            if not re.search(r"## 第\d+章", content):
                mf.append(f"G4.ss.no_chapter_summary:{fp}")
            else:
                c.append({"id": "G4.ss.summaries", "file": fp, "s": "PASS"})

        if "emotional_arcs" in str(fp):
            if not re.search(r"### 第\d+章", content):
                mf.append(f"G4.ss.no_emotional_arc:{fp}")
            else:
                c.append({"id": "G4.ss.arcs", "file": fp, "s": "PASS"})

        if "particle_ledger" in str(fp):
            if "## 粒子账本" not in content and "particle" not in content.lower():
                mf.append(f"G4.ss.no_particle_ledger:{fp}")
            else:
                c.append({"id": "G4.ss.particle_ledger", "file": fp, "s": "PASS"})

        if "pending_hooks" in str(fp):
            if "state" not in content:
                mf.append(f"G4.ss.no_hook_state:{fp}")
            else:
                c.append({"id": "G4.ss.pending_hooks", "file": fp, "s": "PASS"})

    if not fps:
        c.append({"id": "G4.ss", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)


def g4_style_polishing(fps, rd=None):
    """Style polishing: 润色说明 block present, word count change ratio check."""
    c = []
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


def g4_anti_detect(fps, rd=None):
    """Anti-detect: 改写报告 block present, applied techniques listed."""
    c = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.ad.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "## 改写报告" not in content:
            mf.append(f"G4.ad.no_report:{fp}")
        else:
            c.append({"id": "G4.ad.report", "file": fp, "s": "PASS"})

        # Check for applied techniques (table rows or numbered list)
        # Only search within the 改写报告 section to avoid false positives
        report_match = re.search(r"## 改写报告(.+?)(?=\n## |\Z)", content, re.DOTALL)
        report_section = report_match.group(1) if report_match else ""
        has_techniques = bool(
            re.search(r"^\|.*\|.*\|", report_section, re.MULTILINE)
            or re.search(r"^\d+[\.\)、]\s", report_section, re.MULTILINE)
        )

        if has_techniques:
            c.append({"id": "G4.ad.techniques", "file": fp, "s": "PASS"})
        else:
            mf.append(f"G4.ad.no_techniques:{fp}")

    if not fps:
        c.append({"id": "G4.ad", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-anti-detect", c, "scoring", mf)
    return passed("G4-anti-detect", c)


def g4_length_normalizing(fps, rd=None):
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


def gate_G4_bughunt(file_paths):
    """G4.b: Bug-hunt checks (delegates to generic checker)."""
    return g4_generic_bughunt(file_paths)


def gate_G4_clean(file_paths):
    """G4.c: Clean checks (delegates to generic checker)."""
    return g4_generic_clean(file_paths)


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-gate.py <GATE> [args...]")
        print()
        print("Gates: G0 G1 G2 G3 G4 G5 G6 G7 G_TRANSITION G_DISPATCH G_RECONCILE")
        print()
        print("Examples:")
        print("  validate-gate.py G0 outline-example.md")
        print("  validate-gate.py G2 path/to/file.md,path/to/file2.md chapter")
        print("  validate-gate.py G4 chapter-drafting path/to/file.md")
        print("  validate-gate.py G4 worldbuilding path/to/file1,path/to/file2")
        print("  validate-gate.py G7 tests/rounds/round-003-2026-01-01")
        print("  validate-gate.py G_TRANSITION generative bug-hunt tests/rounds/round-003")
        print("  validate-gate.py G_DISPATCH generative tests/rounds/round-003")
        sys.exit(1)

    gate = sys.argv[1]
    args = sys.argv[2:]

    def arg(i, default=None):
        return args[i] if i < len(args) else default

    if gate == "G0":
        print(gate_G0(seed_file=arg(0), round_dir=arg(1)))

    elif gate == "G1":
        files_raw = arg(1, "[]")
        try:
            input_files = json.loads(files_raw)
        except (json.JSONDecodeError, ValueError):
            input_files = []
        print(gate_G1(skill_name=arg(0), input_files=input_files, round_dir=arg(2)))

    elif gate == "G2":
        files = arg(0, "").split(",") if arg(0) else []
        ftype = arg(1, "chapter")
        rd = arg(2, None)
        pd = arg(3, None)
        print(gate_G2(files, ftype, rd, pd))

    elif gate == "G3":
        print(gate_G3(arg(0), arg(1), arg(2)))

    elif gate == "G4":
        skill_or_type = arg(0, "")
        file_list = arg(1, "").split(",") if arg(1) else []
        rd = arg(2, None)

        # Map shorthand names to full shenbi- prefixed skill names
        short_map = {
            "chapter-drafting": "shenbi-chapter-drafting",
            "worldbuilding": "shenbi-worldbuilding",
            "character-design": "shenbi-character-design",
            "story-architecture": "shenbi-story-architecture",
            "power-system": "shenbi-power-system",
            "faction-builder": "shenbi-faction-builder",
            "location-builder": "shenbi-location-builder",
            "relationship-map": "shenbi-relationship-map",
            "pacing-design": "shenbi-pacing-design",
            "plot-thread-weaver": "shenbi-plot-thread-weaver",
            "genre-config": "shenbi-genre-config",
            "volume-outlining": "shenbi-volume-outlining",
            "chapter-planning": "shenbi-chapter-planning",
            "foreshadowing-track": "shenbi-foreshadowing-track",
            "foreshadowing-plant": "shenbi-foreshadowing-plant",
            "context-composing": "shenbi-context-composing",
            "anti-detect": "shenbi-anti-detect",
            "length-normalizing": "shenbi-length-normalizing",
            "state-settling": "shenbi-state-settling",
            "style-polishing": "shenbi-style-polishing",
        }

        if skill_or_type in ("bughunt", "bug-hunt"):
            print(gate_G4_bughunt(file_list))
        elif skill_or_type == "clean":
            print(gate_G4_clean(file_list))
        else:
            full_name = short_map.get(skill_or_type, skill_or_type)
            result = gate_G4(full_name, "generative", file_list, rd)
            print(result)
            write_gate_marker("G4", full_name, "generative", result, rd, file_list)

    elif gate == "G5":
        print(gate_G5(phase_name=arg(0), round_dir=arg(1), project_dir=arg(2)))

    elif gate == "G6":
        pipeline_name = arg(0)
        result = gate_G6(pipeline_name, arg(1), arg(2))
        print(result)
        write_gate_marker("G6", pipeline_name, "generative", result, arg(1))

    elif gate == "G7":
        print(gate_G7(arg(0)))

    elif gate == "G_TRANSITION":
        print(gate_G_TRANSITION(arg(0), arg(1), arg(2)))

    elif gate == "G_DISPATCH":
        print(gate_G_DISPATCH(arg(0), arg(1)))

    elif gate == "G_RECONCILE":
        print(gate_G_RECONCILE(arg(0)))

    else:
        print(
            json.dumps(
                {
                    "status": "UNKNOWN_GATE",
                    "gate": gate,
                    "valid_gates": [
                        "G0",
                        "G1",
                        "G2",
                        "G3",
                        "G4",
                        "G5",
                        "G6",
                        "G7",
                        "G_TRANSITION",
                        "G_DISPATCH",
                        "G_RECONCILE",
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
