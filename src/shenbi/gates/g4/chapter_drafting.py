"""G4 checker for shenbi-chapter-drafting."""

import re
import sys
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
        while proj_dir.name != "skill-output" and proj_dir.parent != proj_dir:
            proj_dir = proj_dir.parent
        project_root = proj_dir.parent if proj_dir.name == "skill-output" else pf.parent
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
                    from shenbi.gates.g5 import _text_fingerprint

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
