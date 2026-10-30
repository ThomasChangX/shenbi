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


#: 币值量词族——实体的末两字若落在该族（交易名实体「灯油四文」「灯油三文」
#: 的「四文」「三文」），不构成「短称」：金额尾与正文计数散文（馍四文半）
#: 无实体指称关系，短称匹配在此类后缀上必然伪命中（2026-10-29 ch25 实弹）
_CURRENCY_SUFFIX_CHARS = "文钱两银吊贯"


def entity_in_text(entity: str, text: str) -> bool:
    """Three-form entity matcher (spec #80 T5 / plan R3-M2).

    Full key / the pre-``·`` stem of a disambiguated copy key / the last
    two chars of a >=3-char key (短称「骨哨」form, ch20 L230). A currency-
    amount suffix (四文/三文 family) is NOT a short form — transaction-
    named entities would otherwise collide with money-counting prose.
    """
    if entity in text:
        return True
    stem = entity.split("·", 1)[0]
    if stem != entity and stem in text:
        return True
    suffix = entity[-2:]
    if any(ch in _CURRENCY_SUFFIX_CHARS for ch in suffix):
        return False
    return len(entity) >= 3 and suffix in text


def _handoff_paragraphs(text: str) -> list[str]:
    return [para for para in text.split("\n\n") if para.strip()]


#: 句切分（。！？；）——、与，为句内从句边界，不切（伤口用例「从灯座下抽出
#: 骨哨、这个你揣着」须保持一句）
_SENTENCE_SPLIT_RE = re.compile(r"[。！？；]")


def check_prop_handoffs(
    text: str,
    memo_text: str,
    props: dict[str, dict[str, str]],
    known_names: set[str] | None = None,
    owner_aliases: dict[str, set[str]] | None = None,
) -> list[str]:
    """F16 G4.cd — un-declared hand-off co-occurrence scan (spec #80 §4).

    Spec trigger is a THREE-part co-occurrence: 「非 owner 人名」+ facts 实体名
    + 交接动词（spec #80 plan R3/T5 wording）——a pronoun-only self-handling
    paragraph (POV-tight narration, 2026-10-29 ch25 live fire: 他从枕下抽出
    《鉴录》) carries no person-name element and must NOT trigger; the hard
    no-source rejection lives in the F16s settle state machine (T8).
    Paragraph-wide co-occurrence (audit-T5 M4): entity and verb may sit in
    different sentences of one paragraph. A paragraph naming the current
    owner (identity aliases count — same person) is owner-mediated (legal).
    The ``·``-stem memo exemption is family-wide (audit-T5 M5): a declared
    copy acquire also exempts the main-line key — inherent to the
    three-form matcher, accepted by plan R3-M2. ``known_names`` is the
    roster against which「非 owner 人名」is judged (production wires
    owners ∪ identity names ∪ name_registry 名列; owners-only when absent
    — degradation visible, settle F16s remains the hard line).
    """
    from shenbi.gates.g4.chapter_planning import parse_prop_declarations
    from shenbi.gates.shared import TRANSFER_VERBS

    declared_stems: set[str] = {
        prop.split("·", 1)[0]
        for prop, op, _frm, _to in parse_prop_declarations(memo_text)
        if op in ("transfer", "acquire", "lose")
    }
    owners = {info.get("owner", "") for info in props.values()} - {""}
    roster = (known_names or set()) | owners
    alias_map = owner_aliases or {}
    issues: list[str] = []
    paragraphs = _handoff_paragraphs(text)
    for prop, info in props.items():
        owner = info.get("owner", "")
        stem = prop.split("·", 1)[0]
        owner_side = {owner} | alias_map.get(owner, set())
        non_owner_names = roster - owner_side
        for para in paragraphs:
            if not entity_in_text(prop, para):
                continue
            if not any(v in para for v in TRANSFER_VERBS):
                continue
            if any(n in para for n in owner_side):
                continue  # owner-mediated paragraph — legal
            if stem in declared_stems:
                continue  # declared (or copy-key family declared)
            if not any(n in para for n in non_owner_names):
                continue  # 人名要件不满足（纯代词/未入册行为人）——settle F16s 兜底
            # 句级实体+动词共现（2026-10-29 ch25 实弹二撞校准）：段落级合并把
            # 「他在私账上写下。…二十二文半还了老周」这类跨句付钱误判成交账
            # ——交接动词的宾语必须是实体本身（同句），人名要件仍为段级
            _sentence_hit = False
            for _sent in _SENTENCE_SPLIT_RE.split(para):
                if entity_in_text(prop, _sent) and any(v in _sent for v in TRANSFER_VERBS):
                    _sentence_hit = True
                    break
            if not _sentence_hit:
                continue
            issues.append(
                f"cd.prop_handoff:「{prop}」交接语境（物象+交接动词共现，"
                f"owner「{owner}」不在场）无备忘声明——正文为唯一真值源，"
                "核实后补声明或修正 facts（修复者: planning+settling）"
            )
            break  # one report per entity
    return issues


_COUNTER_DECL_RE = re.compile(r"^[-*]\s*计数[：:]\s*(\S+)\s+(\d+)\s*\+\s*1\s*$", re.MULTILINE)


def _re_total(word: str) -> re.Pattern[str]:
    # audit-T11 I1: 自然 prose 总数形是「N个名字」——正则须含 个；
    # 个? 可选形兼容无 个 变体（与 ordinal 工厂一致，spec rev2 M2）
    return re.compile(rf"([一二两三四五六七八九十百千\d]{{1,5}})个?{word}")


def _re_ordinal(word: str) -> re.Pattern[str]:
    return re.compile(rf"第([一二两三四五六七八九十百千\d]{{1,5}})个?{word}")


_ORDINAL_RE = re.compile(r"第([一二两三四五六七八九十百千\d]{1,5})个名字")


def parse_counter_declarations(memo_text: str) -> list[tuple[str, int]]:
    """Parse ``- 计数: <名> N+1`` lines (spec #80 F17).

    Returns ``(name, declared_value)`` where declared_value = the parsed
    N+1 (plan R4-M4: the declared NEW value, not the base N).
    """
    out: list[tuple[str, int]] = []
    for m in _COUNTER_DECL_RE.finditer(memo_text):
        try:
            out.append((m.group(1), int(m.group(2)) + 1))
        except ValueError:
            continue
    return out


def check_counter_reconciliation(
    text: str, memo_text: str, counters: dict[str, dict[str, int]]
) -> list[str]:
    """F17 — three-way counter reconciliation (spec #80 §4, rev4 R3-M11).

    Activated only for counters the memo declares (R2-I4b — the WARN
    judgment lives at the g4.cd call site, R3-M1). Reconciles:
    (1) prose totals「N个名字」≡ facts value or declared new value
        (page qualifiers ignored — R5-M3);
    (2) memo declared N+1 ≡ facts+1;
    (3) prose ordinals「第N个名字」≡ declared new value.
    """
    from shenbi.gates.g4.cross_chapter import cn_amount

    def _amount(raw: str) -> int | None:
        # 两 (colloquial 2) is outside cn_amount's vocabulary — normalize
        return cn_amount("二" + raw[1:] if raw.startswith("两") else raw)

    # M1 (audit-T7): counter name -> prose word family; unmapped counters
    # skip the prose faces (no cross-counter interference). P1 registers
    # the single 鉴录名数 counter.
    _WORD_FAMILY: dict[str, tuple[str, ...]] = {
        "鉴录名数": ("名字",),
    }
    issues: list[str] = []
    declared = dict(parse_counter_declarations(memo_text))
    for name, declared_val in declared.items():
        info = counters.get(name)
        if info is None:
            continue  # unknown counter — flagged at the call site (C1 wiring)
        family = _WORD_FAMILY.get(name)
        if not family:
            continue  # no word family mapped — prose faces skip (M1)
        facts_val = int(info.get("value", 0))
        if declared_val != facts_val + 1:
            issues.append(
                f"cd.counter:「{name}」备忘声明 {declared_val - 1}+1={declared_val}"
                f" ≠ facts 现值 {facts_val}+1={facts_val + 1}"
                "——计数链单调断裂（修复者: planning+settling）"
            )
        for word in family:
            for m in _re_total(word).finditer(text):
                amount = _amount(m.group(1))
                if amount is None:
                    continue
                if amount not in (facts_val, declared_val):
                    issues.append(
                        f"cd.counter:「{name}」正文总数「{m.group(0)}」={amount}"
                        f" ∉ {{facts {facts_val}, 声明 {declared_val}}}"
                        "——总数与计数链互斥（修复者: drafting）"
                    )
        for word in family:
            for m in _re_ordinal(word).finditer(text):
                amount = _amount(m.group(1))
                if amount is None:
                    continue
                if amount != declared_val:
                    issues.append(
                        f"cd.counter:「{name}」正文序数「{m.group(0)}」={amount}"
                        f" ≠ 备忘声明值 {declared_val}"
                        "——序数与声明错位（修复者: drafting）"
                    )
    return issues


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

    # ── spec #80 T5 F16 G4.cd — 物象交接共现（挂 facts oracle）──
    # facts 缺席/空 ⇒ WARN 可见 skip（rev4 R3-I2 三律；audit-T4 I3 先例：
    # 损坏文件 raise 保持响亮）。备忘路径 = plans/chapter-N-plan.md。
    _props_facts: dict[str, dict[str, str]] | None = None
    _counters_facts: dict[str, dict[str, int]] | None = None
    _known_names: set[str] | None = None
    _owner_aliases: dict[str, set[str]] = {}
    if project_dir:
        from shenbi.facts.enums import FactsDim
        from shenbi.facts.store import load_facts

        _loaded = load_facts(Path(project_dir), FactsDim.PROPS)
        if _loaded is not None and not _loaded.is_empty:
            _props_facts = {k: {"owner": v.owner} for k, v in _loaded.props().items()}
        # spec #80 T7 F17: counters oracle（空种子≡缺席，R4-M2）
        _cn_loaded = load_facts(Path(project_dir), FactsDim.COUNTERS)
        if _cn_loaded is not None and not _cn_loaded.is_empty:
            _counters_facts = {k: {"value": v.value} for k, v in _cn_loaded.counters().items()}
        # F16「非 owner 人名」roster（2026-10-29 实弹校准）：owners ∪ identity
        # 叙事名+别名 ∪ name_registry 名列；主角别名同时计入 owner-side
        _known_names = {info.get("owner", "") for info in (_props_facts or {}).values()} - {""}
        _id_loaded = load_facts(Path(project_dir), FactsDim.IDENTITY)
        if _id_loaded is not None and not _id_loaded.is_empty:
            _id = _id_loaded.identity()
            if _id is not None:
                _known_names |= {_id.narration_name, *_id.aliases}
                _owner_aliases[_id.narration_name] = set(_id.aliases)
        _nr = Path(project_dir) / "truth" / "name_registry.md"
        if _nr.is_file():
            for _line in _nr.read_text(encoding="utf-8").splitlines():
                _m = re.match(r"^\|([^|]+)\|\s*([^|]+?)\s*\|", _line)
                if not _m:
                    continue
                _cat, _name = _m.group(1).strip(), _m.group(2)
                if _cat in ("类别", "---", ":---") or _name in ("名", "---"):
                    continue
                # 控制行不是角色注册（2026-10-29 实弹：代词白名单的「他」入 roster
                # 后人名要件被代词恒满足；禁用名的「灯」同理）＋裸代词永不入册
                if _cat in ("代词白名单", "禁用名") or _name in ("他", "她", "它", "我", "你"):
                    continue
                _known_names.add(_name)

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.file_not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")
        wc = word_count_md(str(pf))

        # per-file memo join (F16/F17 share)
        _memo: str | None = None
        _ch_m = re.search(r"chapter-(\d+)", Path(fp).name)
        if project_dir and _ch_m:
            _memo_path = Path(project_dir) / "plans" / f"chapter-{_ch_m.group(1)}-plan.md"
            if _memo_path.is_file():
                _memo = _memo_path.read_text(encoding="utf-8")

        # ── spec #80 T5 F16 G4.cd — 正文无源交付拍（per-chapter）──
        if _props_facts is None:
            c.append(
                {
                    "id": "cd.prop_handoff",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "no_facts — props facts absent/empty; hand-off scan skipped (degradation visible)",
                }
            )
        else:
            for issue in check_prop_handoffs(
                content, _memo or "", _props_facts, _known_names, _owner_aliases
            ):
                mf.append(f"{fp}:{issue}")

        # ── spec #80 T7 F17 — 计数器三方对账（激活判定在调用点，R3-M1）──
        # M1（audit-T7）：计数名→prose 词族映射（未映射计数器跳过 prose 面，
        # 多计数器不串扰）；M2：鉴录名数=那罕添加名口径（R2-I4a）——ch17 全书
        # 口径靠 no_decl 跳过，backfill 范围钉 ch9-only（T13）
        if _counters_facts is None:
            c.append(
                {
                    "id": "cd.counter",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "no_facts — counters facts absent/empty; reconciliation skipped (degradation visible)",
                }
            )
        else:
            _memo_decls = parse_counter_declarations(_memo) if _memo else []
            if not _memo_decls:
                c.append(
                    {
                        "id": "cd.counter",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no_decl — memo declares no counters this chapter; reconciliation not activated (legacy-memo compat, ch17-class false-red guard)",
                    }
                )
            else:
                _unknown = {n for n, _v in _memo_decls} - set(_counters_facts)
                for _u in sorted(_unknown):
                    mf.append(
                        f"cd.counter:{fp}:「{_u}」备忘声明了 facts 未种子的计数器"
                        "——先补 facts 种子（修复者: settling）"
                    )
                for issue in check_counter_reconciliation(content, _memo or "", _counters_facts):
                    mf.append(f"{fp}:{issue}")

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
                # spec #82 T1: quote anchoring (v4 张力拍引句回查本章正文——
                # 与 #83 T1 verbatim 判定器共基，先落地者建；只验存在性，
                # 温度语义归 audit 判温 blocking finding）
                from shenbi.gates.g4.quote_verbatim import extract_anchor_quotes, quote_in_chapter

                _cn82 = re.search(r"chapter-(\d+)", pf.name)
                _mp82 = (
                    Path(project_dir) / "plans" / f"chapter-{int(_cn82.group(1))}-plan.md"
                    if _cn82 and project_dir
                    else None
                )
                if _mp82 is not None and _mp82.is_file():
                    _anchors = extract_anchor_quotes(_mp82.read_text(encoding="utf-8"))
                    if _anchors:
                        _prose = ""
                        if fp:
                            _ch_path = Path(fp)
                            if _ch_path.is_file():
                                _prose = _ch_path.read_text(encoding="utf-8")
                        for _tier, _q in _anchors:
                            if not quote_in_chapter(_q, _prose):
                                mf.append(
                                    f"G4.cd.quote_verbatim:{fp}:『{_q[:24]}…』不在本章正文"
                                    f"（引句锚定——v4 张力拍引句须逐字取自章尾句原文；修复者: drafting 或 planning 同步改）"
                                )
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
                    _pfv = re.search(
                        r"^plan_format[：:]\s*v[2-9]\s*$", _memo_text, re.MULTILINE
                    )  # v2 门（v3 ⊇ v2, #78；v4 ⊇ v3, spec #82）——不得 v[3-9] 误伤 v2
                    _memo_v2 = _pfv is not None  # v3 ⊇ v2（#78）
        # ── spec #78: plan_format v3（回触/分级/重量）──
        _memo_v3 = False
        if _memo_v2:
            _memo_v3 = bool(re.search(r"^plan_format[：:]\s*v[3-9]\s*$", _memo_text, re.MULTILINE))
        _proj78 = Path(project_dir) if project_dir else None
        if _memo_v3 and _proj78 is not None:
            # 连续微钩（读前章声明——spec #82 T1/I4：优先完成时快照（L-D 铁律），
            # 快照缺席章（卷一 pre-T0 历史）回退 plan memo 解析——纯读幂等）
            _cn78 = re.search(r"chapter-(\d+)", pf.name)
            if _cn78:
                from shenbi.gates.g4.chapter_planning import _declared_history  # pyright: ignore[reportPrivateUsage]

                _hist78 = _declared_history(str(project_dir)) if _proj78 else {}
                _tiers: list[str] = []
                for _k in range(max(1, int(_cn78.group(1)) - 3), int(_cn78.group(1)) + 1):
                    _snap78 = (_hist78.get(_k) or {}).get("张力拍档位")
                    if isinstance(_snap78, str) and _snap78 in ("微", "章", "大"):
                        _tiers.append(_snap78)
                        continue
                    _mk = _proj78 / "plans" / f"chapter-{_k}-plan.md"
                    if not _mk.is_file():
                        continue
                    _tm = re.search(
                        r"章尾张力拍[：:]\s*\[?(微|章|大)", _mk.read_text(encoding="utf-8")
                    )
                    if _tm:
                        _tiers.append(_tm.group(1))
                _micro_cap = (
                    (read_genre_config(str(project_dir)) or {})
                    .get("market_params", {})
                    .get("hook_grading", {})
                    .get("max_consecutive_micro", 2)
                )
                _run78 = 0
                for _x in reversed(_tiers):
                    if _x == "微":
                        _run78 += 1
                    else:
                        break
                if _run78 > _micro_cap:
                    mf.append(
                        f"G4.cd.micro_hook_run:{fp}:{_run78}>{_micro_cap} "
                        f"(v3 连续微钩超限——章/大钩轮换；修复者: planning)"
                    )
            # payoff 密度窗：window 内 v3 memo 无轴登记 payoff = WARN
            _pdw = (
                (read_genre_config(str(project_dir)) or {})
                .get("market_params", {})
                .get("payoff_density", {})
            )
            _win = int(_pdw.get("window", 3)) if _pdw else 3
            _has_axis = False
            if _cn78:
                for _k in range(max(1, int(_cn78.group(1)) - _win + 1), int(_cn78.group(1)) + 1):
                    _mk = _proj78 / "plans" / f"chapter-{_k}-plan.md"
                    if _mk.is_file() and re.search(
                        r"\*\*payoff 拍\*\*[：:].*轴[（(]?(债|名声|名字数|进度)",
                        _mk.read_text(encoding="utf-8"),
                    ):
                        _has_axis = True
                        break
            if not _has_axis:
                c.append(
                    {
                        "id": "G4.cd.payoff_density",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": f"v3 近{_win}章无轴登记 payoff（payoff_density 窗）",
                    }
                )

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
