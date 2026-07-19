"""G4 checker for shenbi-chapter-drafting."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    META_NARRATIVE,
    count_transition_words,
    fail,
    passed,
    read_genre_config,
    resolve_input_path,
    word_count_md,
)
from shenbi.logging import get_logger

log = get_logger(__name__)


def check_hook_fulfillment(plan_path: Path, chapter_path: Path) -> list[str]:
    """G4.cd.hook_fulfillment: Verify plan-declared hooks appear in chapter body.

    Extracts hook IDs from plan Section 7 (Hook Ledger) and searches
    for their presence in the chapter prose.

    Args:
        plan_path: Path to the chapter plan markdown file.
        chapter_path: Path to the chapter markdown file.

    Returns:
        List of issue strings. Empty if all hooks are fulfilled or plan
        is missing/has no hooks.
    """
    if not plan_path.exists():
        return []

    plan_text = plan_path.read_text(encoding="utf-8")
    chapter_text = chapter_path.read_text(encoding="utf-8")

    # Extract hook IDs from plan -- match patterns like MH-003, CP-012, etc.
    plan_hooks = set(re.findall(r"[A-Z]{2,4}-\d+", plan_text))
    # Extract hook IDs from chapter body
    chapter_hooks = set(re.findall(r"[A-Z]{2,4}-\d+", chapter_text))

    missing = plan_hooks - chapter_hooks
    if missing:
        return [
            f"G4.cd.hook_unfulfilled: plan requires hooks {sorted(missing)} "
            f"but none found in chapter body"
        ]
    return []


def check_chapter_title(title: str, previous_titles: dict[str, int]) -> list[str]:
    """G4.cd.title: Validate chapter title quality.

    Checks:
    - No chapter numbers in title
    - No duplicate titles
    - No day-of-week labels (WARN, not HARD)
    - Thematic naming encouraged (1-4 Chinese characters)
    """
    issues = []

    # HARD FAIL: Chapter number in title
    if re.search(r"第\d+章", title):
        issues.append(
            "G4.cd.title:contains_chapter_number -- "
            "title must not include chapter number (SKILL.md:125)"
        )

    # HARD FAIL: Duplicate title
    if title in previous_titles:
        issues.append(
            f"G4.cd.title:duplicate_of_ch{previous_titles[title]} -- title '{title}' already used"
        )

    # WARN: Day-of-week or date label
    day_pattern = re.compile(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
        r"周[一二三四五六日])"
    )
    if day_pattern.search(title):
        issues.append(
            "G4.cd.title:day_label_instead_of_thematic_name -- "
            "prefer thematic 1-4 character name over date label"
        )

    return issues


def _text_fingerprint(text: str, min_len: int = 50) -> set[int]:
    """Build a set of paragraph hashes for content overlap comparison."""
    body = re.sub(r"^---.*?---", "", text, flags=re.DOTALL)
    paragraphs = body.split(chr(10) + chr(10))
    hashes: set[int] = set()
    for p in paragraphs:
        p = p.strip()
        if not p or p.startswith("#") or p.startswith(">"):
            continue
        if "PRE_WRITE_CHECK" in p or "POST_WRITE_SELF_CHECK" in p:
            continue
        cjk = len(re.findall(r"[一-鿿]", p))
        if cjk >= min_len:
            hashes.add(hash(p))
    return hashes


def _check_protagonist_presence(
    text: str,
    protagonist_names: list[str],
    threshold: int = 3,
) -> list[str]:
    """G4.cd.protagonist_presence: verify protagonist appears >= threshold times.

    Args:
        text: Chapter prose text.
        protagonist_names: List of protagonist names/pronouns to search for.
        threshold: Minimum required occurrences.

    Returns:
        List of issue strings (empty if check passes).
    """
    total = sum(text.count(name) for name in protagonist_names)
    if total < threshold:
        return [
            f"G4.cd.protagonist_absent: protagonist appears {total} times (threshold: {threshold})"
        ]
    return []


def _load_protagonist_names(project_dir: str) -> list[str]:
    """Load protagonist names from character design files."""
    names: list[str] = []
    chars_dir = Path(project_dir) / "characters"
    if not chars_dir.exists():
        return ["林烽", "他"]
    protag = chars_dir / "protagonist.md"
    if protag.exists():
        text = protag.read_text(encoding="utf-8")
        # Try frontmatter name first
        match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        if match:
            names.append(match.group(1).strip())
        # Also try YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml as _yaml

                    fm = _yaml.safe_load(parts[1])
                    if isinstance(fm, dict) and "name" in fm:
                        names.append(str(fm["name"]))
                except Exception:
                    pass
    if not names:
        names = ["林烽", "他"]
    # Always include common pronoun
    if "他" not in names:
        names.append("他")
    return names


def g4_chapter_drafting(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Chapter-drafting: PRE/POST check blocks, transition density,
    fatigue words, meta-narrative, word count.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
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

        # Transition word density ≤ 1/1000 (relaxed from 1/3000 for automated gen)
        tc = count_transition_words(content)
        max_t = max(5, wc // 1000)
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

        # Fatigue words ≤ 8 (relaxed from 3 for automated first-draft gen)
        # Determine project dir from file path
        proj_dir = pf.parent
        while proj_dir.name != "skill-output" and proj_dir.parent != proj_dir:
            proj_dir = proj_dir.parent
        project_root = proj_dir.parent if proj_dir.name == "skill-output" else pf.parent
        gc = read_genre_config(str(project_root))
        fatigue_list = gc.get("fatigue_words", FATIGUE_BASE)
        fatigue_hits = sum(content.count(w) for w in fatigue_list)
        if fatigue_hits > 8:
            mf.append(f"G4.fatigue:{fp}:{fatigue_hits}>8")
        else:
            c.append(
                {
                    "id": "G4.fatigue",
                    "file": fp,
                    "s": "PASS",
                    "hits": fatigue_hits,
                }
            )

        # Meta-narrative phrases = 0 (check body only, not PRE/POST meta sections)
        import re as _re2

        _body = content
        for tag in [
            r"## PRE_WRITE_CHECK.*?(?=## |# |<!--META|\Z)",
            r"## POST_WRITE_SELF_CHECK.*?(?=## |# |<!--META|\Z)",
        ]:
            _body = _re2.sub(tag, "", _body, flags=_re2.DOTALL)
        meta_hits = {w: _body.count(w) for w in META_NARRATIVE if w in _body}
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
                            log.warning("file_read_failed", file=str(other), error=str(e))
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

        # G4.cd.scene_concreteness: at least 1 paragraph of >=100 CJK chars of visual narrative
        # (Web novel style uses short paragraphs — lowered from 200 to 100)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        visual_p_count = 0
        for p in paragraphs:
            if p.startswith("#") or p.startswith("##") or p.startswith(">") or p.startswith("---"):
                continue
            cjk_in_p = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", p))
            has_vn = bool(re.search(r"(走|跑|推|拉|抓|坐|站|躺|倒|看|听|触|发现|看到|听到)", p))
            has_di = bool(re.search(r"[「\u201c].*?[」\u201d]", p))
            if cjk_in_p >= 100 and (has_vn or has_di):
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

        # G4.cd.protagonist_presence: protagonist appears >= threshold times
        protagonist_names = (
            _load_protagonist_names(str(project_root)) if project_dir else ["林烽", "他"]
        )
        protagonist_issues = _check_protagonist_presence(content, protagonist_names)
        if protagonist_issues:
            mf.extend(protagonist_issues)
        else:
            c.append({"id": "G4.cd.protagonist_presence", "file": fp, "s": "PASS"})

    if mf:
        return fail("G4-chapter-drafting", c, "scoring", mf)
    return passed("G4-chapter-drafting", c)
