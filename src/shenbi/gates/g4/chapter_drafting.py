"""G4 checker for shenbi-chapter-drafting."""

from __future__ import annotations
from shenbi.status import GateStatus
from typing import Any
import re
from pathlib import Path

from shenbi.text.voice_lexicon import (
    DEFAULT_VOICE_DENSITY_MIN,
    catchphrases_from_card,
    distinct_voice_signals,
)

from shenbi.gates.shared import (
    FATIGUE_BASE,
    META_BLOCK_RE,
    META_NARRATIVE,
    chapter_word_floor,
    count_similes,
    count_transition_words,
    fail,
    passed,
    read_genre_config,
    resolve_input_path,
    segment_sentences,
    strip_narrative_body,
    total_chars_md_text,
    word_count_md,
    strip_scene_markers,
    split_scenes,
    parse_scene_declarations,
    scene_hook_mismatches,
    is_scene_marker_line,
)
from shenbi.logging import get_logger
from shenbi.text.cjk import dialogue_char_ratio

log = get_logger(__name__)


_HOOK_LEDGER_HEADING = re.compile(
    r"^#{1,3}\s*(?:Section\s*7.*|\d+[.、]\s*Hook Ledger.*|Hook Ledger.*|.*伏笔清单.*|.*钩子台账.*)$",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_hook_ledger_section(plan_text: str) -> str:
    """Return the Hook Ledger section body (heading to next same-or-higher
    heading); empty string when the plan has no such section.
    """
    m = _HOOK_LEDGER_HEADING.search(plan_text)
    if m is None:
        return ""
    rest = plan_text[m.end() :]
    nxt = re.search(r"^#{1,3}\s+\S", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


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

    # F749 (spec #39 T11): scan ONLY the Hook Ledger section (docstring's
    # declared "Section 7") — IDs elsewhere in the plan are not requirements.
    section = _extract_hook_ledger_section(plan_text)
    plan_hooks = set(re.findall(r"[A-Z]{2,4}-\d+", section)) if section else set()
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
    """
    issues = []

    # HARD FAIL: Chapter number in title
    if re.search(r"第\d+章", title):
        issues.append(
            "G4.cd.title:contains_chapter_number -- "
            "title must not include chapter number (SKILL.md「章节标题不要包含章节号」)"
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


# F415-0815 (C28 R3b): in-process (path, mtime_ns, size) fingerprint
# memoization. Production G4 runs are subprocess-per-call (cold per spawn) —
# the cache serves in-process multi-file callers (g5.5's embedded gate_G4
# loop, tests) and future in-process gate invocation. Failures are never
# cached; verdicts stay idempotent under the stat key. One slot per path:
# each rewrite replaces the entry, so the cache is bounded by the number
# of distinct files (no unbounded growth across chapter rewrites).
_FINGERPRINT_CACHE: dict[str, tuple[tuple[int, int], frozenset[int]]] = {}


def _fingerprint_of(path: Path) -> frozenset[int]:
    """Fingerprint of a chapter file, memoized per path under (mtime_ns, size)."""
    try:
        st = path.stat()
        slot = _FINGERPRINT_CACHE.get(str(path))
        if slot is not None and slot[0] == (st.st_mtime_ns, st.st_size):
            return slot[1]
        fp = frozenset(_text_fingerprint(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError) as e:
        log.warning("file_read_failed", file=str(path), error=str(e))
        return frozenset()
    _FINGERPRINT_CACHE[str(path)] = ((st.st_mtime_ns, st.st_size), fp)
    return fp


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
        return []
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
                except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
                    pass  # malformed YAML frontmatter → fall back to regex name match above
    if not names:
        return []
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

    # spec #71 golden-slot line predicates (compiled once, outside the loop —
    # loop-body definitions trip ruff B023).
    _GOLDEN_PRE_RE = re.compile(r"^\s*-\s*本章金句位\s*[:：]\s*(.*)$", re.MULTILINE)
    _GOLDEN_POST_RE = re.compile(r"^\s*-\s*\[.\]\s*金句位\s*[:：]\s*(.+)$", re.MULTILINE)
    _EMPTY_VALUES = frozenset({"", "无", "N/A", "待定"})

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
            c.append({"id": "G4.pre_check", "file": fp, "s": GateStatus.PASS})

        # POST_WRITE_SELF_CHECK
        if "## POST_WRITE_SELF_CHECK" not in content:
            mf.append(f"G4.post_check:{fp}")
        else:
            c.append({"id": "G4.post_check", "file": fp, "s": GateStatus.PASS})

        # Transition word density ≤ 1/1000 (relaxed from 1/3000 for automated gen)
        # Count on the narrative body only (probe escalation #4): the raw
        # content includes the framework-mandated PRE_WRITE_CHECK checklist,
        # which itself enumerates transition words — the gate was counting
        # its own checklist (6 of 8 hits on probe chapter 1).
        tc = count_transition_words(strip_narrative_body(content))
        max_t = max(5, wc // 1000)
        if tc > max_t:
            mf.append(f"G4.transition:{fp}:{tc}>{max_t}")
        else:
            c.append(
                {
                    "id": "G4.transition",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "density": f"{tc}/{wc}",
                }
            )

        # Fatigue words ≤ 8 (relaxed from 3 for automated first-draft gen)
        # Determine project dir from file path
        # spec #48 C34 (F407): project_root resolution order = explicit
        # project_dir param (if it carries genre-config) > genre-config
        # ancestor walk (nearest on path; single-project assumption) > pf.parent.
        candidates: list[Path] = []
        if project_dir:
            candidates.append(Path(project_dir))
        walk = pf.parent
        while walk.parent != walk and not (walk / "genre-config.json").exists():
            walk = walk.parent
        candidates.append(walk if (walk / "genre-config.json").exists() else pf.parent)
        project_root = next(
            (cdir for cdir in candidates if (cdir / "genre-config.json").exists()),
            candidates[-1],
        )
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
                    "s": GateStatus.PASS,
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
            c.append({"id": "G4.meta", "file": fp, "s": GateStatus.PASS})

        # Word count ≥ floor, on the TOTAL non-whitespace 口径 (probe
        # escalation #4): the memo layer plans length in total chars (~3400),
        # so a CJK-only floor demanded ≈3565 total — plan-compliant chapters
        # structurally failed (production fixture ch36/37/39/41 all 27xx-CJK).
        # Spec #72 口径统一: floor reads chapter_word.min (the 2800-4000
        # band's lower edge); default stays math-only (G0.3/G6 derivations).
        word_floor = chapter_word_floor(str(project_root))
        total = total_chars_md_text(content)
        if total < word_floor:
            mf.append(f"G4.word_count:{fp}:{total}<{word_floor}")
        else:
            c.append(
                {
                    "id": "G4.word_count",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "wc": wc,
                    "total": total,
                    "floor": word_floor,
                }
            )

        # spec #72 G4.cd.scene_count — durable markers delimit >= 2 scenes
        scene_markers = sum(1 for ln in content.split("\n") if is_scene_marker_line(ln))
        if scene_markers < 2:
            mf.append(f"G4.cd.scene_count:{fp}:{scene_markers}<2")
        else:
            c.append(
                {
                    "id": "G4.cd.scene_count",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "scenes": scene_markers,
                }
            )

        # spec #72 G4.cd.scene_hook_match — declared hooks land verbatim on
        # each scene's final line (predicate: 声明剥空白 ⊆ 场景末非空行)
        _m_num = re.search(r"chapter-(\d+)", str(fp))
        plan_text_src = None
        if _m_num and (rd or project_root):
            _plan_base = Path(rd) if rd else Path(project_root)
            _plan_path = _plan_base / "plans" / f"chapter-{_m_num.group(1)}-plan.md"
            if _plan_path.is_file():
                plan_text_src = _plan_path.read_text(encoding="utf-8")
        if plan_text_src is not None:
            decls = parse_scene_declarations(plan_text_src)
            if decls:
                hook_issues = scene_hook_mismatches(decls, split_scenes(content))
                if hook_issues:
                    mf.append(f"G4.cd.scene_hook_match:{fp}:{';'.join(hook_issues)}")
                else:
                    c.append({"id": "G4.cd.scene_hook_match", "file": fp, "s": GateStatus.PASS})

        # G4.cd.content_uniqueness: check this chapter against all other chapters
        if rd:
            chapters_dir = Path(rd) / "project-output" / "chapters"
            if chapters_dir.exists():
                other_chapters = list(chapters_dir.glob("chapter-*.md"))
                if len(other_chapters) > 1:
                    this_fingerprint = _text_fingerprint(strip_scene_markers(content))
                    max_overlap = 0.0
                    for other in other_chapters:
                        if str(other) == str(pf):
                            continue
                        # F415-0815 (C28 R3b): memoized per (path, mtime_ns,
                        # size) — was a full re-read + re-hash of every other
                        # chapter on each per-chapter invocation (O(N^2)).
                        # Read failure yields an empty fingerprint (overlap 0),
                        # matching the previous except-branch semantics.
                        other_fp = _fingerprint_of(other)
                        overlap = len(this_fingerprint & other_fp) / max(len(this_fingerprint), 1)
                        max_overlap = max(max_overlap, overlap)
                    if max_overlap > 0.40:
                        mf.append(f"G4.cd.content_overlap:{fp}:{max_overlap:.0%}")
                    else:
                        c.append(
                            {
                                "id": "G4.cd.content_uniqueness",
                                "file": fp,
                                "s": GateStatus.PASS,
                                "max_overlap": f"{max_overlap:.0%}",
                            }
                        )

        # G4.cd.scene_concreteness: at least 1 paragraph of >=100 CJK chars of visual narrative
        # (Web novel style uses short paragraphs — lowered from 200 to 100)
        # Strip META blocks first (word_count_md's own口径): the trailing
        # POST_WRITE_SELF_CHECK checklist otherwise becomes the "last
        # paragraph" for the end-hook check below and pollutes both consumers
        # of this list (canary escalation #12, 2026-09-28).
        # HOOK-BEGIN/END ledger blocks are machine markup like META (probe
        # escalation #39): left in, the markup line became the "last
        # paragraph" and short-circuited the end-hook window.
        content_for_prose = re.sub(
            r"<!--HOOK-BEGIN-->.*?<!--HOOK-END-->", "", content, flags=re.DOTALL
        )
        content_for_prose = META_BLOCK_RE.sub("", content_for_prose)
        # spec #72: standalone SCENE marker lines are machine markup — keep
        # them out of the paragraph surface (else a trailing marker becomes
        # the "last paragraph" and pollutes the end-hook window).
        content_for_prose = strip_scene_markers(content_for_prose)
        paragraphs = [p.strip() for p in content_for_prose.split("\n\n") if p.strip()]
        # Visual-scene check is WINDOWED (canary escalation #13): web-novel
        # prose uses 50-100 CJK paragraphs, so a single-paragraph >=100
        # measure is a granularity mismatch with the very style the SKILL
        # teaches. A window of 1-3 consecutive body paragraphs counts when
        # its combined CJK >= 100 and at least 2 paragraphs in it carry
        # visual-narrative verbs or dialogue (size-1 windows keep the legacy
        # >=1 requirement — long-paragraph styles see no regression).
        body_paragraphs: list[tuple[bool, bool, int]] = []  # (has_vn, has_di, cjk)
        for p in paragraphs:
            if p.startswith("#") or p.startswith("##") or p.startswith(">") or p.startswith("---"):
                continue
            cjk_in_p = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", p))
            has_vn = bool(re.search(r"(走|跑|推|拉|抓|坐|站|躺|倒|看|听|触|发现|看到|听到)", p))
            has_di = bool(re.search(r"[「\u201c].*?[」\u201d]", p))
            body_paragraphs.append((has_vn, has_di, cjk_in_p))
        visual_windows = 0
        # Window sizes up to 8 (probe escalation #37): extreme micro-paragraph
        # web-novel prose averages ~13 CJK/paragraph — a 3-paragraph window
        # never reaches the 100-CJK threshold, so the check structurally
        # could not fire on that style. Larger windows keep the ≥100-CJK
        # mass requirement and scale the vn/dialogue density with size.
        for size in (1, 2, 3, 5, 8):
            for i in range(len(body_paragraphs) - size + 1):
                window = body_paragraphs[i : i + size]
                if sum(w[2] for w in window) < 100:
                    continue
                needed = {1: 1, 2: 2, 3: 2, 5: 3, 8: 4}[size]
                if sum(1 for w in window if w[0] or w[1]) >= needed:
                    visual_windows += 1
                    break  # one qualifying window per size is enough
        if visual_windows < 1:
            mf.append(f"G4.cd.no_visual_scene:{fp}")
        else:
            c.append(
                {
                    "id": "G4.cd.scene_concreteness",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "visual_windows": visual_windows,
                }
            )

        # G4.cd.chapter_end_hook: unresolved tension in the closing beat.
        # WINDOWED over the last 8 narrative paragraphs (probe escalation
        # #4 opened the window to 5 because tension lands a few paragraphs
        # before the final image beat; the merged-mass rewrite below needs
        # the scene check's 8-cap (escalation #37) so stylistic closers at
        # -6 stay inside). The >=30 CJK mass threshold lives on the MERGED
        # window, not per paragraph (probe13, 2026-10-02): micro-paragraph
        # closers put every tension beat below a per-paragraph floor
        # (keyword paragraph at 29, real hook at 24 CJK) while the only
        # checked paragraph was a neutral image — escalation #37 gave the
        # visual-scene check the same windowed-mass treatment for this
        # style. A window lighter than 30 CJK total stays unchecked.
        # 没答 joins the 没说/瞒/藏 concealment family (escalation #38):
        # asked-and-not-answered is unresolved tension.
        if paragraphs:
            hook_window = [
                p for p in paragraphs[-8:] if not p.startswith(("#", "##", ">", "---", "- [ ]"))
            ]
            window_text = "".join(hook_window)
            window_cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", window_text))
            if window_cjk >= 30:
                has_q = bool(re.search(r"[？?]", window_text))
                has_t = bool(
                    re.search(
                        r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)",
                        window_text,
                    )
                )
                # 账目钩 (P1-3, 2026-10-23): a cold ledger closer — two
                # separate arabic digit runs in the merged window (伤亡 41
                # 人…82 户…) — is a legal hook form from the seed's 章末钩
                # 七型; the digits themselves are the unresolved tension.
                # Runs, not bare chars: one stray "3" or a lone "4173" is
                # not a ledger line (review calibration #5).
                has_ledger = len(re.findall(r"\d+", window_text)) >= 2
                if has_q or has_t or has_ledger:
                    c.append(
                        {
                            "id": "G4.cd.chapter_end_hook",
                            "file": fp,
                            "s": GateStatus.PASS,
                            "window_cjk": window_cjk,
                        }
                    )
                else:
                    excerpt = window_text[:30]
                    mf.append(
                        f"G4.cd.no_hook:{fp}:{window_cjk}字合并窗口未检出疑问句/张力词/账目行；"
                        f"窗口开头「{excerpt}」"
                    )

        # G4.cd.protagonist_presence: protagonist appears >= threshold times
        protagonist_names = _load_protagonist_names(str(project_root)) if project_dir else []
        if not protagonist_names:
            c.append(
                {
                    "id": "G4.cd.protagonist_presence",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": "no protagonist data",
                }
            )
        else:
            protagonist_issues = _check_protagonist_presence(content, protagonist_names)
            if protagonist_issues:
                mf.extend(protagonist_issues)
            else:
                c.append({"id": "G4.cd.protagonist_presence", "file": fp, "s": GateStatus.PASS})

        # spec #71 prose-excellence WARN predicates (WARN-level: recorded in
        # checks for the pipeline manifest, never in must_fix).
        narrative = strip_narrative_body(content)
        sents = segment_sentences(narrative)
        narrative_surge = sum(
            1 for sent, slen in sents if slen >= 35 and dialogue_char_ratio(sent) < 0.5
        )
        surge_quota = max(1, total // 3000)
        if narrative_surge < surge_quota:
            c.append(
                {
                    "id": "G4.cd.surge",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": f"narrative surge sentences {narrative_surge} < quota {surge_quota}",
                }
            )
        else:
            c.append(
                {
                    "id": "G4.cd.surge",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "surge": narrative_surge,
                    "quota": surge_quota,
                }
            )

        simile_stats = count_similes(content)
        if 2.0 <= simile_stats["per_1000"] <= 4.0:
            c.append(
                {
                    "id": "G4.cd.simile_band",
                    "file": fp,
                    "s": GateStatus.PASS,
                    "per_1000": simile_stats["per_1000"],
                }
            )
        else:
            c.append(
                {
                    "id": "G4.cd.simile_band",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": (
                        f"simile density {simile_stats['per_1000']}/千字 outside "
                        "[2,4] (low = dry, high = pile-up; 俗套喻体抽检归审计)"
                    ),
                    "per_1000": simile_stats["per_1000"],
                }
            )

        pre_block = re.search(r"## PRE_WRITE_CHECK.*?(?=## |# |<!--META|\Z)", content, re.DOTALL)
        post_block = re.search(
            r"## POST_WRITE_SELF_CHECK.*?(?=## |# |<!--META|\Z)", content, re.DOTALL
        )

        # ── spec #76: plan_format v2 版本条件化（密度 + 金句位类型三点同步）──
        # v2 判据 = memo plans/chapter-N-plan.md 段1 令牌；v1 旧路径持续可跑
        # （#75 回归集/CI fixtures 全为 v1——密度 WARN、金句位旧格式 PASS）。
        _memo_v2 = False
        _mp: Path | None = None
        _memo_text = ""
        if project_dir:
            _cn = re.search(r"chapter-(\d+)", pf.name)
            if _cn:
                _mp = Path(project_dir) / "plans" / f"chapter-{_cn.group(1)}-plan.md"
                if _mp.is_file():
                    _memo_text = _mp.read_text(encoding="utf-8")
                    _pfv = re.search(r"^plan_format[：:]\s*v2\s*$", _memo_text, re.MULTILINE)
                    _memo_v2 = _pfv is not None
        _body = narrative
        _cps: list[str] = []
        if project_dir:
            _pcard = Path(project_dir) / "characters" / "protagonist.md"
            if _pcard.is_file():
                _cps = catchphrases_from_card(_pcard.read_text(encoding="utf-8"))
        _signals = distinct_voice_signals(_body, _cps)
        _vdm = (
            (read_genre_config(project_dir or str(pf.parent)) or {})
            .get("market_params", {})
            .get("voice_density_min", {})
        )
        _vmin = (
            int(_vdm.get("min_per_chapter", DEFAULT_VOICE_DENSITY_MIN))
            if _vdm
            else DEFAULT_VOICE_DENSITY_MIN
        )
        if _memo_v2 and _signals < _vmin:
            mf.append(
                f"G4.cd.voice_density:{fp}:{_signals}<{_vmin} "
                "(v2 章——备忘声口要求行未兑现；修复者: drafting)"
            )
        else:
            c.append(
                {
                    "id": "G4.cd.voice_density",
                    "file": fp,
                    "s": GateStatus.PASS if _memo_v2 else GateStatus.WARN,
                    "r": f"signals={_signals}/{_vmin}"
                    + ("" if _memo_v2 else " (v1 章——dispatch 域外，WARN 口径)"),
                }
            )
        golden_issues: list[str] = []
        pre_val: str | None = None
        if pre_block:
            m = _GOLDEN_PRE_RE.search(pre_block.group(0))
            if m:
                pre_val = m.group(1)
        if pre_val is None or pre_val.strip().strip("[]").strip() in _EMPTY_VALUES:
            golden_issues.append("PRE lacks non-empty 金句位 line")
        post_ok = False
        if post_block:
            if _GOLDEN_POST_RE.search(post_block.group(0)):
                post_ok = True
        if not post_ok:
            golden_issues.append("POST lacks 金句 excerpt line")
        _quote_type_ok = True
        if _memo_v2:
            # 三点同步：memo 段1 金句位行 → PRE 本章金句位行 → 章尾钩行 [?] 金句位行
            _types: set[str] = set()
            if _mp is not None and _mp.is_file():
                _mm = re.search(
                    r"^金句位[：:]\s*(静|燃)｜.*$",
                    _memo_text,
                    re.MULTILINE,
                )
                if _mm:
                    _types.add(_mm.group(1))
                else:
                    # spec §1(4) 三点同步——memo 点缺席即断链（v2 备忘必含类型金句位行）
                    _quote_type_ok = False
            if pre_val is None or pre_val.strip() in ("", "无", "N/A", "待定"):
                _quote_type_ok = False
            else:
                _qt = re.match(r"(静|燃)｜", pre_val.strip())
                if _qt:
                    _types.add(_qt.group(1))
                else:
                    _quote_type_ok = False
            _post_m = _GOLDEN_POST_RE.search(post_block.group(0)) if post_block else None
            if _post_m:
                _qt2 = re.match(r"(静|燃)｜", _post_m.group(1).strip())
                if _qt2:
                    _types.add(_qt2.group(1))
                else:
                    _quote_type_ok = False
            if not _types or len(_types) > 1 or not _quote_type_ok:
                mf.append(
                    f"G4.cd.quote_type:{fp}:v2 金句位须「静/燃｜写法｜落点」三点同型"
                    f"（观测类型集={sorted(_types) or '∅'}；修复者: drafting）"
                )
        if golden_issues:
            c.append(
                {
                    "id": "G4.cd.golden_slot",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "; ".join(golden_issues),
                }
            )
        else:
            c.append({"id": "G4.cd.golden_slot", "file": fp, "s": GateStatus.PASS})

    if mf:
        return fail("G4-chapter-drafting", c, "scoring", mf)
    return passed("G4-chapter-drafting", c)
