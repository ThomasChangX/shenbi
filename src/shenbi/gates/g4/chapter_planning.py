"""G4 checker for shenbi-chapter-planning."""

from __future__ import annotations
from pathlib import Path
from shenbi.status import GateStatus
from typing import Any
import json
import re

from shenbi.logging import get_logger
from shenbi.contracts.enums import PF_GE_V2, PF_GE_V3, PF_LEGAL
from shenbi.gates.g4.cross_chapter import load_memo_declarations
from shenbi.gates.shared import (
    SCENE_INDEPENDENT_BAND,
    SCENE_PAIRED_BAND,
    chapter_word_min_max,
    fail,
    jload,
    pack_scenes,
    parse_scene_declarations,
    passed,
    resolve_input_path,
    split_scenes,
)

log = get_logger(__name__)


_PROP_DECL_RE = re.compile(
    r"^[-＊*]\s*([^@：:\n]+)@(hold|transfer|acquire|lose)[：:]"
    r"\s*([^→\n]+?)(?:→([^\n]+))?$",
    re.MULTILINE,
)


def parse_prop_declarations(memo_text: str) -> list[tuple[str, str, str, str]]:
    """Parse structured prop declaration lines ``物件@op: A→B`` (spec #80 F16).

    Returns ``(prop, op, from_, to)`` 4-tuples; the single-value ``@hold``
    form repeats the holder into both slots. Prose ``**母题物象**`` lines
    are NOT declarations (11/24 memos carry legacy ``- 物象:`` rows whose
    key forms get normalized by the T13 backfill — out of scope here).
    """
    out: list[tuple[str, str, str, str]] = []
    for m in _PROP_DECL_RE.finditer(memo_text):
        prop = m.group(1).strip()
        op = m.group(2)
        left = m.group(3).strip() if m.group(3) else ""
        right = m.group(4).strip() if m.group(4) else ""
        if right:
            out.append((prop, op, left, right))
        else:
            out.append((prop, op, left, left))
    return out


def _declared_history(project_dir: str | None) -> dict[int, dict[str, Any]]:
    """Read completion-time declared snapshots from pipeline-state.json."""
    if not project_dir:
        return {}
    sp = Path(project_dir) / "pipeline-state.json"
    if not sp.is_file():
        return {}
    try:
        data = json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for k, cs in (data.get("chapter_loop", {}).get("chapter_states", {}) or {}).items():
        if isinstance(cs, dict) and cs.get("declared"):
            try:
                out[int(k)] = dict(cs["declared"])
            except (TypeError, ValueError):
                continue
    return out


def _spec82_sequence_gates(
    content: str,
    n: int,
    project_dir: str | None,
    mf: list[str],
    c: list[dict[str, Any]],
) -> None:
    """Spec #82 T1: cold_streak / hot_hook / payoff_magnitude / temperature.

    History comes from the T0 completion snapshot (never the mutable plan);
    the current chapter's own declarations join the window tail. Config-
    absent keys degrade to WARN (scene_budget precedent). The first three
    chapters are exempt (golden-3 has its own constraints). Bootstrap: a
    window with fewer completed chapters than `window` skips floor checks.
    """
    if not project_dir or n <= 3:
        return
    from shenbi.gates.shared import read_genre_config
    from shenbi.text.recall_weight import cold_chapter

    mp = (read_genre_config(project_dir) or {}).get("market_params", {})
    hist = _declared_history(project_dir)

    # spec #82 T1: 回卷窗口跨卷界时只取本卷已生成章（audit-T4/C1）——
    # bundle_chapters 同源的 volume span 判定复用；无 volume_map 时全量。
    vol_start = 1
    _vm = Path(project_dir) / "outline" / "volume_map.md"
    if _vm.is_file():
        from shenbi.pipeline.volume_budget import parse_volume_spans

        for _span in parse_volume_spans(_vm.read_text(encoding="utf-8")):
            if _span.start <= n <= _span.end:
                vol_start = _span.start
                break

    def _cur(key: str, pat: str) -> Any:
        m = re.search(pat, content, re.MULTILINE)
        return m.group(1) if m else None

    tone = _cur("emotion_tone", r"^emotion_tone[：:]\s*(\S+)")
    golden_hot = bool(re.search(r"^金句位[：:]\s*燃", content, re.MULTILINE))
    tier = _cur("张力拍档位", r"^[-* ]*\*{0,2}章尾张力拍\*{0,2}[：:]\s*\[?(微|章|大)")
    payoff = _cur("payoff档", r"\*{0,2}payoff\s*拍\*{0,2}[：:].*?(小|中|大)兑现")

    # T1 cold_streak_window — trailing cold run ending at the current chapter
    cap_cfg = mp.get("cold_streak_cap")
    if not isinstance(cap_cfg, dict):
        c.append(
            {
                "id": "G4.cp.cold_streak_window",
                "s": GateStatus.WARN,
                "r": "market_params.cold_streak_cap 缺席——退 WARN（spec #82）",
            }
        )
    else:
        cap = int(cap_cfg.get("max", 3))
        run = 1 if cold_chapter(tone, golden_hot) else 0
        if run:
            for prev in range(n - 1, max(0, vol_start - 1), -1):
                d = hist.get(prev)
                if d is None:
                    break  # snapshot gap (volume start / pre-T0) stops the run
                if cold_chapter(d.get("emotion_tone"), bool(d.get("金句位燃"))):
                    run += 1
                else:
                    break
            if run > cap:
                mf.append(
                    f"G4.cp.cold_streak_window:ch{n}:{run}>{cap} "
                    f"(连续冷章超限——冷=悲/惧/平 且金句位非燃，词表外按冷；修复者: planning——本章须转暖或前置章补暖)"
                )

    def _window(field: str, current: Any, window: int) -> list[Any] | None:
        """Trailing window incl. current, clamped to the current volume
        (spec: 回卷窗口跨卷界只取本卷已生成章); None → bootstrap skip.
        """
        lo = max(vol_start, n - window + 1)
        vals = [v for m in range(lo, n) if (v := (hist.get(m) or {}).get(field)) is not None]
        vals.append(current)
        have = len([v for v in vals if v is not None])
        if have < window:
            return None  # bootstrap (r6/N6): window not full → no floor
        return vals

    # T1 hot_hook_floor — 大-level tension beats per window
    hhf = mp.get("hot_hook_floor")
    if not isinstance(hhf, dict):
        c.append(
            {
                "id": "G4.cp.hot_hook_window",
                "s": GateStatus.WARN,
                "r": "market_params.hot_hook_floor 缺席——退 WARN（spec #82）",
            }
        )
    else:
        w = int(hhf.get("window", 10))
        floor = int(hhf.get("min", 1))
        vals = _window("张力拍档位", tier, w)
        big = sum(1 for v in vals if v == "大") if vals is not None else 0
        if vals is not None and big < floor:
            mf.append(
                f"G4.cp.hot_hook_window:ch{n}:{w}章窗内大钩 {big}<{floor} "
                f"(热章尾钩频率下限；修复者: planning——窗尾章张力拍须上「大」)"
            )

    # T1 payoff_magnitude_floor — 中+ payoff per window (min key consumed)
    pmf = mp.get("payoff_magnitude_floor")
    if not isinstance(pmf, dict):
        c.append(
            {
                "id": "G4.cp.payoff_magnitude",
                "s": GateStatus.WARN,
                "r": "market_params.payoff_magnitude_floor 缺席——退 WARN（spec #82）",
            }
        )
    else:
        w = int(pmf.get("window", 6))
        rank = {"小": 0, "中": 1, "大": 2}
        min_key = pmf.get("min", "中")
        min_rank = rank.get(str(min_key), 1)
        vals = _window("payoff档", payoff, w)
        if vals is not None and not any(
            v is not None and rank.get(str(v), -1) >= min_rank for v in vals
        ):
            mf.append(
                f"G4.cp.payoff_magnitude:ch{n}:{w}章窗内无 {min_key} 级以上兑现 "
                f"(payoff 量级下限，min 键已消费；修复者: planning)"
            )

    # T1 temperature_profile — WARN-level hot-ratio profile
    tp = mp.get("temperature_profile")
    if not isinstance(tp, dict):
        c.append(
            {
                "id": "G4.cp.temperature_profile",
                "s": GateStatus.WARN,
                "r": "market_params.temperature_profile 缺席——退 WARN（spec #82）",
            }
        )
    else:
        w = int(tp.get("window", 10))
        tp_floor: float = float(tp.get("hot_ratio_min", 0.2))
        vals = _window("张力拍档位", tier, w)
        tones = _window("emotion_tone", tone, w)
        if vals is not None:
            # 热章 = 张力拍∈{章,大} 或 emotion_tone∈{怒,喜}（spec 原文双条件）
            hot = sum(
                1
                for v, t in zip(vals, tones if tones else vals, strict=False)
                if v in ("章", "大") or t in ("怒", "喜")
            )
            if hot / len(vals) < tp_floor:
                c.append(
                    {
                        "id": "G4.cp.temperature_profile",
                        "file": f"plans/chapter-{n}-plan.md",
                        "s": GateStatus.WARN,
                        "r": f"近{w}章热占比 {hot}/{len(vals)} < {tp_floor}——温粥循环风险（WARN 级）",
                    }
                )


def parse_last_reinforced(hooks_text: str) -> dict[str, int]:
    """Per-hook max last_reinforced chapter from truth detail blocks (T2).

    Real format tolerates spaces: ``last_reinforced: 第 35 章``.
    """
    out: dict[str, int] = {}
    hook = ""
    for line in hooks_text.splitlines():
        h = re.match(r"^##+\s+(MH\d+)", line)
        if h:
            hook = h.group(1)
            continue
        m = re.match(r"^-\s*last_reinforced[：:]\s*第\s*(\d+)\s*章", line)
        if m and hook:
            n = int(m.group(1))
            out[hook] = max(out.get(hook, 0), n)
    return out


def parse_relevant_hooks(hooks_text: str) -> set[str]:
    """RELEVANT hook ids (plus plant chapters) from the overview table."""
    out: set[str] = set()
    for line in hooks_text.splitlines():
        m = re.match(r"^\|\s*(MH\d+)（[^）]*）\s*\|\s*(\S+)\s*\|\s*(\d+)", line)
        if m and m.group(2) == "RELEVANT":
            out.add(m.group(1))
    return out


def _cn_to_int(v: str) -> int | None:
    """CN numeral -> int, composites included (十三=13, 二十=20, 四十二=42).

    Hundred-first ordering: 一百二十三 parses 123, not 13 via the 十 branch.
    """
    simple = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if "百" in v:
        left, _, right = v.partition("百")
        hundreds = simple.get(left, 1) if left else 1
        rest = _cn_to_int(right) if right else 0
        return hundreds * 100 + (rest or 0)
    if v == "十":
        return 10
    if "十" in v:
        left, _, right = v.partition("十")
        tens = simple.get(left, 1) if left else 1
        return tens * 10 + (simple.get(right, 0) if right else 0)
    return simple.get(v)


def _int_to_cn(n: int) -> str | None:
    """Int -> CN numeral, composites included (13=十三, 20=二十, 42=四十二)."""
    simple = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
    if n < 10:
        return simple.get(n)
    if n < 20:
        return "十" + simple.get(n - 10, "")
    if n < 100 and n % 10 == 0:
        return simple.get(n // 10, "") + "十"
    if n < 100:
        return simple.get(n // 10, "") + "十" + simple.get(n % 10, "")
    return None


def _defer_anchor_hits_volume(tail: str, vm_text: str) -> bool:
    """Defer-anchor existence (spec #82 T2/r3): the anchor's volume/KR
    reference must hit volume_map — both KR generations
    (``#### KR2:`` headings and ``2. KR2（第 X–Y 章完成）：`` list rows)
    plus Chinese numeral normalization (卷三 → 第三卷).
    """
    if not vm_text or not tail.strip():
        return False
    kr = re.search(r"KR\d+", tail)
    # 前缀形「第N卷/N卷」与后缀形「卷N」都在锚域（audit-T6/C1 终轮：
    # 后缀悬空卷此前不可见 → 复合检查被跳过 → 垃圾卷借 KR 腿混过）
    vol = re.search(r"(?:第?([一二三四五六七八九十百\d]+)卷|卷([一二三四五六七八九十百\d]+))", tail)
    # audit-T6/C1 复合语义：卷与 KR 双指定须双命中（「至第99卷·KR1」的
    # 垃圾卷不得借真实 KR 混过）；单指定单命中。CN 组合数（十三/二十/四十二）
    # 与后缀形「至卷三」都在解析域（复审：原子 1-12 只覆盖前 12 卷）。
    vol_n = None
    if vol:
        v = vol.group(1) or vol.group(2)  # 前缀形或后缀形
        vol_n = _cn_to_int(v) if not v.isdigit() else int(v)
    kr_hit = False
    if kr:
        kid = kr.group(0)
        heading = re.search(rf"^####+\s*{kid}[：:]", vm_text, re.M)
        row = re.search(rf"^\d+\.\s*{kid}（", vm_text, re.M)
        kr_hit = bool(heading or row)
    # audit-T6/C1: 卷腿双向归一——锚侧中文（卷三）转 arabic 后，标题侧也要
    # CN 形态回查（真实卷纲 12/12 全用「第三卷：」中文数字标题，arabic 直搜
    # 零命中）；组合数由 _int_to_cn 反查；垃圾卷号两头都不命中。
    vol_hit = False
    if vol_n:
        for form in (str(vol_n), _int_to_cn(vol_n) or ""):
            if form and re.search(rf"^##+\s*第{form}卷", vm_text, re.M):
                vol_hit = True
                break
    if vol_n and kr:
        return vol_hit and kr_hit  # 双指定双命中
    return vol_hit or kr_hit  # 单指定单命中


def _spec82_hook_age(
    content: str, n: int, project_dir: str | None, mf: list[str], c: list[dict[str, Any]]
) -> None:
    """Spec #82 T2: RELEVANT hook aging + defer budget (truth-block source)."""
    if not project_dir:
        return
    from shenbi.gates.shared import read_genre_config

    mp = (read_genre_config(project_dir) or {}).get("market_params", {})
    hma = mp.get("hook_max_age")
    hp = (
        (Path(project_dir) / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        if (Path(project_dir) / "truth" / "pending_hooks.md").is_file()
        else ""
    )
    if not isinstance(hma, dict) or not hp:
        # audit-T6/I3: 缺席可见性（与 T1 三门同纪律——键缺席/真相面缺席
        # 发 WARN 行而非静默暗门）
        if not isinstance(hma, dict):
            c.append(
                {
                    "id": "G4.cp.hook_age",
                    "s": GateStatus.WARN,
                    "r": "market_params.hook_max_age 缺席——退 WARN（spec #82）",
                }
            )
        return
    max_age = int(hma.get("max", 8))
    last = parse_last_reinforced(hp)
    relevant = parse_relevant_hooks(hp)
    plant = {
        m.group(1): int(m.group(3))
        for m in re.finditer(r"^\|\s*(MH\d+)（[^）]*）\s*\|\s*(\S+)\s*\|\s*(\d+)", hp, re.M)
    }
    defer_lines = re.findall(r"^[-*]\s*挂起[：:]\s*(MH\d+)[^\n]*$", content, re.M)
    vm_text = ""
    vm_path = Path(project_dir) / "outline" / "volume_map.md"
    if vm_path.is_file():
        vm_text = vm_path.read_text(encoding="utf-8")
    for hook in sorted(relevant):
        anchor = last.get(hook, plant.get(hook, 1))
        age = n - anchor
        if age <= max_age:
            continue
        # audit-T6/I2 + 阶段8/I1: 提及≠触达——须在钩账/推进语境内；v4 段 7
        # EXACT 表格（| ID | 操作 | 推进方式 | 沉默章数 |）的 advance/touch 行
        # 与 bullet 形都认（真实 v4 plan 按契约产出表格——bullet-only 会对
        # 每个超龄钩确定性误报）。
        touched = bool(
            re.search(rf"{hook}[^\n]{{0,20}}(?:推进|touch|强化)", content)
            or re.search(rf"钩账[^\n]{{0,12}}{hook}", content)
            or re.search(rf"^\|\s*{hook}\s*\|\s*(?:advance|touch|强化)", content, re.M)
        )
        deferred = hook in defer_lines or bool(
            re.search(rf"^\|\s*{hook}\s*\|\s*defer\s*\|([^|\n]*)", content, re.M)
        )
        if not (touched or deferred):
            mf.append(
                f"G4.cp.hook_age:ch{n}:{hook} 距上次推进 {age}>{max_age} 章且本章未触达未挂起"
                f"（修复者: planning——钩账行 touch 或带清偿锚挂起）"
            )
    # 挂起行须带真实清偿锚（r3/r4：锚中卷/KR 引用须在 volume_map 命中——两代 KR 形态+卷号归一）；
    # v4 段 7 表格 defer 行的 推进方式 列同送锚校验（阶段8/I1：bullet-only 让表格形
    # defer 完全绕过锚校验与预算——「挂而不排」从表格通道复发）。
    defer_forms: list[tuple[str, str]] = [
        (m.group(1), m.group(2))
        for m in re.finditer(r"^[-*]\s*挂起[：:]\s*(MH\d+)\s*(.*)$", content, re.M)
    ]
    defer_forms.extend(
        (m.group(1), m.group(2))
        for m in re.finditer(r"^\|\s*(MH\d+)\s*\|\s*defer\s*\|([^|\n]*)", content, re.M)
    )
    for hook_id, tail in defer_forms:
        anchor_hit = _defer_anchor_hits_volume(tail, vm_text)
        if not anchor_hit:
            mf.append(
                f"G4.cp.hook_age:ch{n}:{hook_id} 挂起缺有效清偿锚（『{tail.strip()[:20]}』未命中 volume_map 卷/KR）"
                f"（修复者: planning——挂起行/表格 defer 行的推进方式列须带「至第N卷·KRn」且在卷纲在盘）"
            )
    budget = mp.get("hook_defer_budget", {})
    per_vol = int(budget.get("per_volume", 3)) if isinstance(budget, dict) else 3
    if len(defer_forms) > per_vol:
        mf.append(
            f"G4.cp.hook_age:ch{n}:挂起数 {len(defer_forms)}>{per_vol} 超卷预算"
            f"（hook_defer_budget；修复者: planning——收敛挂起或兑现）"
        )


def _spec82_core_motif_touch(
    n: int, project_dir: str | None, mf: list[str], c: list[dict[str, Any]]
) -> None:
    """Spec #82 T6: core-motif supply floor (轮回触点◆ single chain).

    Data base: the T0 snapshot's 节点标记集 (volume_map-derived, not a memo
    duty). The gate filters 轮回触点◆ out of every chapter's marker set
    BEFORE computing the gap — a union of all ◆ markers would let 萤回触◆
    mask a broken 轮回 chain (vol-1's 16-chapter drought passed with union
    gaps ≤7; plan R2/I1). Dual-path fixer: planning (touchpoint beat for a
    ◆-marked node) / volume-outlining (rearrange ◆, ungenerated chapters
    only). First marker before the current volume start is not counted.
    """
    if not project_dir or n <= 3:
        return
    from shenbi.gates.shared import read_genre_config

    cfg = read_genre_config(project_dir) or {}
    cmt = (cfg.get("pacing") or {}).get("core_motif_touch")
    if not isinstance(cmt, dict):
        c.append(
            {
                "id": "G4.cp.core_motif_touch",
                "s": GateStatus.WARN,
                "r": "pacing.core_motif_touch 缺席——退 WARN（spec #82 T6）",
            }
        )
        return
    max_gap = int(cmt.get("max_gap", 6))
    hist = _declared_history(project_dir)
    # spec r6/N2 (audit-T9/I2): same-volume scope as T1 — the back-walk stops
    # at the current volume's start (parse_volume_spans, bundle_chapters
    # source); a first marker before the window doesn't count (docstring
    # promised, wasn't implemented — vol-3 opening falsely failed).
    vol_start = 1
    _vm = Path(project_dir) / "outline" / "volume_map.md"
    if _vm.is_file():
        from shenbi.pipeline.volume_budget import parse_volume_spans

        for _span in parse_volume_spans(_vm.read_text(encoding="utf-8")):
            if _span.start <= n <= _span.end:
                vol_start = _span.start
                break
    last = None
    for k in range(n - 1, max(0, vol_start - 1), -1):
        if "轮回触点◆" in ((hist.get(k) or {}).get("节点标记集") or []):
            last = k
            break
    gap = (n - last) if last is not None else None
    if gap is not None and gap > max_gap:
        mf.append(
            f"G4.cp.core_motif_touch:ch{n}:距上次轮回触点◆ {gap}>{max_gap} 章"
            f"（金手指/母题供给下限——单一标记链，萤回触◆ 不抵轮回；修复者: planning 本章为◆节点补触点拍 / volume-outlining 重排◆（仅未生成章））"
        )


def g4_chapter_planning(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Chapter planning: 8 numbered sections (## 1. to ## 8.), golden-3 rules,
    section 4 has 关键抉择, section 5 has hook operation names.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    # #18-2 (probe23 adjudication #007): the ch3 memo invented MH11/MH12 —
    # book_spine caps at MH10, pending_hooks never registered them, two
    # human reject rounds with explicit delete instructions still shipped
    # MH11 in the approved memo. The machine gate owns hook authenticity:
    # MH-namespace IDs are genesis-owned (lifecycle assigns CP-NNN to new
    # plants), so every MH reference in §7 must exist in the spine or the
    # pool. Registry files absent (phase 1) → nothing to check against.
    registered_hooks: set[str] | None = None
    if project_dir:
        registry_parts: list[str] = []
        for rel in ("truth/book_spine.md", "truth/pending_hooks.md"):
            rf = Path(project_dir) / rel
            if rf.is_file():
                registry_parts.append(rf.read_text(encoding="utf-8"))
        # both registry files absent (phase 1) → nothing to check against
        if registry_parts:
            registered_hooks = set(re.findall(r"MH\d+", "\n".join(registry_parts)))

    # ── spec #72 G4.cp.scene_budget — 场景预算两型域/组合/可打包性预检 ──
    # planning 时点拦截不可打包的预算序列。打包窗口 = 前章全场景（实际值）+
    # 本备忘声明 + 邻章备忘声明（bundle 双备忘 staging 时点均在盘——R2 接缝
    # 联合）；尾组开埠（allow_open_tail）配下 bundle 首场景。
    _fanqie_band = (1800, 2800)
    if project_dir:
        try:
            _gc = jload(str(Path(project_dir) / "genre-config.json"))
            _fq = _gc.get("chapter_word", {}).get("fanqie_update", {})
            if isinstance(_fq, dict) and _fq.get("min") and _fq.get("max"):
                _fanqie_band = (int(_fq["min"]), int(_fq["max"]))
        except (OSError, ValueError):
            log.warning("cp_scene_budget_fanqie_band_fallback", band=_fanqie_band)
    _mn_cfg, _mx_cfg = chapter_word_min_max(project_dir)
    chapter_band = (_mn_cfg or 2800, _mx_cfg or 4000)

    def _memo_decl_sizes(plan_path: Path) -> list[int]:
        """Sibling memo's declared sizes (packing-window input)."""
        if not plan_path.is_file():
            return []
        return [
            size
            for (_num, size, _kind, _hook) in parse_scene_declarations(
                plan_path.read_text(encoding="utf-8")
            )
        ]

    for fp in fps or []:
        resolved = resolve_input_path(fp, rd)
        p_ = Path(resolved)
        if not p_.is_file():
            continue
        _plan_text = p_.read_text(encoding="utf-8")
        decls = parse_scene_declarations(_plan_text)
        if not decls:
            # 旧式备忘（无场景块）——存量兼容；但 v3 自称的备忘缺块=FAIL
            # （2026-10-29 续跑实弹：模型连续两束漏写预算节溜过兼容口，
            # 缺锚直接引发 drafting word_band 打摆与余额链失锚）
            if re.search(r"plan_format[：:]\s*v[3-9]\b", _plan_text):
                mf.append(
                    f"G4.cp.scene_budget:{fp}:场景预算节缺失——plan_format v3+ 备忘"
                    "必含「### 场景预算与收束钩（#72 粒度契约）」块（2-3 场景声明＋"
                    "时间锚/余额/POV/事件/物象行）"
                )
            continue
        n_match = re.search(r"chapter-(\d+)", p_.name)
        chapter_no = int(n_match.group(1)) if n_match else None
        issues: list[str] = []
        if not 2 <= len(decls) <= 3:
            issues.append(f"场景数 {len(decls)} 不在 2-3")
        for idx, (_num, size, kind, _hook) in enumerate(decls, 1):
            lo_i, hi_i = SCENE_INDEPENDENT_BAND
            lo_p, hi_p = SCENE_PAIRED_BAND
            in_ind = lo_i <= size <= hi_i
            in_pair = lo_p <= size <= hi_p
            if kind == "独立型" and not in_ind:
                issues.append(f"场景{idx} 声明独立型但 {size} 不落 [1800,2000]")
            if kind == "配对型" and not in_pair:
                issues.append(f"场景{idx} 声明配对型但 {size} 不落 [900,1400]")
            if not (in_ind or in_pair):
                issues.append(f"场景{idx}={size} 落灰域 [1400,1800)")
        sizes = [d[1] for d in decls]
        total = sum(sizes)
        indep_count = sum(1 for d in decls if d[2] == "独立型")
        if len(decls) == 2 and indep_count != 2:
            issues.append("2 场景章须两独立型（和 [3600,4000]）")
        if len(decls) == 3 and indep_count not in (0, 1):
            issues.append("3 场景章须三配对型或一独两配")
        if not chapter_band[0] <= total <= chapter_band[1]:
            issues.append(f"章和 {total} 不在 [{chapter_band[0]},{chapter_band[1]}]")
        # 打包窗口：前章全场景（实际）+ 本声明 + 邻章备忘声明（R2 接缝联合）
        seq: list[int] = []
        if chapter_no is not None and project_dir:
            prev = Path(project_dir) / "chapters" / f"chapter-{chapter_no - 1}.md"
            if prev.is_file():
                seq.extend(s for s, _ll in split_scenes(prev.read_text(encoding="utf-8")))
        seq.extend(sizes)
        if chapter_no is not None:
            for cand in (
                p_.parent / f"chapter-{chapter_no + 1}-plan.md",
                Path(project_dir or ".")
                / "staging"
                / "plans"
                / f"chapter-{chapter_no + 1}-plan.md",
                Path(project_dir or ".") / "plans" / f"chapter-{chapter_no + 1}-plan.md",
            ):
                sib = _memo_decl_sizes(cand)
                if sib:
                    seq.extend(sib)
                    break
        if pack_scenes(seq, _fanqie_band, allow_open_tail=True) is None:
            issues.append(
                f"贪心不可打包（序列 {seq}，更带 {_fanqie_band}）——请调整场景预算组合;"
                + _packing_hint()
            )
        if issues:
            mf.append(f"G4.cp.scene_budget:{fp}:" + ";".join(issues))
        else:
            c.append({"id": "G4.cp.scene_budget", "file": fp, "s": GateStatus.PASS})

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.cp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # ── spec #80 T4 F16 G4.cp — 物象声明对 facts 现态合法性 ──
        # 声明行 v3 内可选（v4 硬门化=P2 全量 backfill 后）；本检查只对
        # 在场声明行生效。facts 缺席/空 ⇒ WARN（skip 不 FAIL）；无声明行
        # 备忘 ⇒ WARN legacy_memo（13/24 静默死法禁令）。
        _props_facts = None
        if project_dir:
            from shenbi.facts.enums import FactsDim
            from shenbi.facts.store import load_facts

            _loaded = load_facts(Path(project_dir), FactsDim.PROPS)
            if _loaded is not None and not _loaded.is_empty:
                _props_facts = _loaded.props()
        _prop_decls = parse_prop_declarations(content)
        if _props_facts is None:
            c.append(
                {
                    "id": "cp.prop_decl",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "no_facts — props facts absent/empty; F16 cp legality skipped (degradation visible)",
                }
            )
        elif not _prop_decls:
            c.append(
                {
                    "id": "cp.prop_decl",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "legacy_memo — no 物件@op declaration lines; cp legality has nothing to verify (WARN-visible exemption, not silent)",
                }
            )
        else:
            for _prop, _op, _frm, _to in _prop_decls:
                if _prop not in _props_facts:
                    continue  # copy key / new entity first sighting = legal
                if _op == "transfer" and _frm and _frm != _props_facts[_prop].owner:
                    mf.append(
                        f"cp.prop_decl:{fp}:「{_prop}」声明经手起点「{_frm}」"
                        f"≠ facts 现态 owner「{_props_facts[_prop].owner}」"
                        "——正文为唯一真值源，核实后修正声明或 facts（修复者: settling）"
                    )
                elif _op == "hold" and _to and _to != _props_facts[_prop].owner:
                    mf.append(
                        f"cp.prop_decl:{fp}:「{_prop}」声明持有者「{_to}」"
                        f"≠ facts 现态 owner「{_props_facts[_prop].owner}」"
                        "（修复者: settling）"
                    )

        # ── spec #76/#78 G4.cp.plan_format — 版本令牌分立 ──
        # 缺席 = v1 默认（不 FAIL）；在场值 ∉ {v1,v2,v3,v4} = FAIL；
        # v2/v3/v4 ⇒ 声口要求行存在；v3 ⇒ 张力拍分级行 + payoff 轴量行。
        _pf_m = re.search(r"^plan_format[：:]\s*(\S+)\s*$", content, re.MULTILINE)
        if _pf_m:
            _pf_val = _pf_m.group(1)
            if _pf_val not in PF_LEGAL:
                mf.append(
                    f"G4.cp.plan_format:{fp}:invalid_token:{_pf_val} (合法值 v1/v2/v3/v4；缺席 = v1 默认)"
                )
            elif _pf_val in PF_GE_V2:
                if not re.search(r"^声口要求[：:].+$", content, re.MULTILINE):
                    mf.append(
                        f"G4.cp.voice_line:{fp}:{_pf_val}_requires_声口要求行 "
                        "(protagonist 口癖/句式要点——planning 从 protagonist.md voice_profile 生成)"
                    )
                else:
                    c.append({"id": "G4.cp.voice_line", "file": fp, "s": GateStatus.PASS})
            if _pf_val in PF_GE_V3:
                # spec #78 v3 义务：张力拍分级行 + payoff 轴量行
                if not re.search(r"章尾张力拍[：:]\s*\[?(微|章|大)", content):
                    mf.append(
                        f"G4.cp.tension_tier:{fp}:v3_requires_张力拍分级行 "
                        "（[微|章|大]+形态——分级声明制）"
                    )
                _payoff_m = re.search(r"\*\*payoff 拍\*\*[：:]\s*(.+)", content)
                if _payoff_m and not re.search(
                    r"轴[（(]?(债|名声|名字数|进度)", _payoff_m.group(1)
                ):
                    mf.append(
                        f"G4.cp.payoff_axis:{fp}:v3_requires_轴量声明 "
                        "（类型｜轴(债/名声/名字数/进度)｜量——四轴登记为兑现唯一口径）"
                    )

        # ── spec #75 G4.cp.declarations — 三声明行（时间锚/余额/POV）──
        # SKILL 承诺「新格式备忘缺任一行 = G4.cp FAIL」；旧格式（无场景预算
        # 块）= WARN 豁免（legacy 备忘只免声明行交叉核对，散文派生检查照跑）。
        _has_budget_block = re.search(r"#{2,4}\s*场景预算", content) is not None
        if _has_budget_block:
            _decls = load_memo_declarations(pf)
            _missing = [k for k in ("时间锚", "余额", "POV") if k not in _decls]
            if _missing:
                mf.append(
                    f"G4.cp.declarations:{fp}:missing_{'+'.join(_missing)} "
                    "(#75 三声明行——机器消费字段，缺行使跨章不变量门降级)"
                )
            else:
                c.append({"id": "G4.cp.declarations", "file": fp, "s": GateStatus.PASS})
        else:
            c.append(
                {
                    "id": "G4.cp.declarations",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "legacy memo (no scene-budget block) — declaration cross-check exempt, prose-derived checks still run",
                }
            )

        # 8 numbered sections (## N. / ## N、 / ## N： / ## N)
        sections_found = []
        for i in range(1, 9):
            if re.search(rf"## {i}[\.、：:\s]", content):
                sections_found.append(i)
        if len(sections_found) < 8:
            missing = [i for i in range(1, 9) if i not in sections_found]
            mf.append(f"G4.cp.sections:{len(sections_found)}/8_missing_{missing}")
        else:
            c.append({"id": "G4.cp.sections", "file": fp, "s": GateStatus.PASS})

        # chapter_role token — drives review-resonance threshold calibration (spec §5.1)
        if re.search(r"chapter_role\s*[:：]\s*(高潮|兑现|推进|转折|过渡|铺垫)", content):
            c.append({"id": "G4.cp.chapter_role", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_chapter_role:{fp}")

        # #27 (probe17 adjudications #003→#005): the '# Chapter N:' English
        # heading is contract-banned; the write-path injector kept re-adding
        # it after compliant model output (#28 scoped the injector), so the
        # gate now enforces the ban machine-side on the written artifact.
        _eng = re.search(r"^#\s*Chapter\s*\d+\s*:?", content, re.MULTILINE)
        if _eng:
            mf.append(
                f"G4.cp.english_heading:{fp}:「{_eng.group(0)}」"
                "（删除该英文标题行——文件必须以「# 第N章 章节备忘」中文标题行开头）"
            )
        else:
            c.append({"id": "G4.cp.english_heading", "file": fp, "s": GateStatus.PASS})

        # Golden-3 rules based on chapter number N — quality bonus, not hard gate.
        # Only fails if golden content is completely missing AND sections are also
        # incomplete. Warnings are more appropriate for automated pipelines.
        ch_num = re.search(r"-(\d+)-plan", str(fp))
        n = int(ch_num.group(1)) if ch_num else 0
        golden = {1: "三面墙", 2: "验证主角特殊性|对手", 3: "小高潮"}
        if n in golden:
            alternatives = golden[n].split("|")
            if not any(alt in content for alt in alternatives):
                # Don't fail — golden rules are aspirational quality targets
                c.append(
                    {
                        "id": f"G4.cp.golden_{n}",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": f"golden rule '{golden[n]}' not found in chapter {n}",
                    }
                )
            else:
                c.append({"id": f"G4.cp.golden_{n}", "file": fp, "s": GateStatus.PASS})
        else:
            c.append(
                {
                    "id": "G4.cp.golden",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": f"N={n}, golden-3 only for N=1,2,3",
                }
            )

        # P1 craft-declaration fields (2026-10-23, 诡秘/炮火 commercial-rhythm
        # audit): §1 must declare emotion_tone (抑扬排程 — five-value
        # vocabulary aligned with rhythm_principles monotony detection) and
        # a payoff 拍 (爽点兑现声明; review-highpoint audits 蓄压-释放比 against
        # it); chapters inside the retention window must declare a 留存锚
        # line (§2). The window mirrors golden-3's hardcode (fixed 30).
        if re.search(r"emotion_tone\s*[:：]\s*(悲|喜|怒|惧|平)", content):
            c.append({"id": "G4.cp.emotion_tone", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_emotion_tone:{fp}")

        # spec #82 r5/C1（阶段8/I2）：v4 章尾钩型行——存在性+七型词表检查
        # （镜像 emotion_tone 五值模式；词表外自造型 FAIL——种子七型的机器
        # 执法面，此前只有 rotation 消费值而无源头门）。
        _pf_val82 = re.search(r"^plan_format[：:]\s*(\S+)\s*$", content, re.M)
        _is_v4plus = (
            _pf_val82 and _pf_val82.group(1) in PF_LEGAL and int(_pf_val82.group(1)[1:]) >= 4
        )
        if _is_v4plus:
            _hook_type_m = re.search(r"^章尾钩型[：:]\s*(\S+)", content, re.M)
            if not _hook_type_m:
                mf.append(f"G4.cp.missing_hook_type:{fp}")
            elif _hook_type_m.group(1).strip() not in (
                "悬念钩",
                "危机钩",
                "情感钩",
                "反转钩",
                "账目钩",
                "信物钩",
                "对位钩",
            ):
                mf.append(
                    f"G4.cp.hook_type_wordlist:{fp}:{_hook_type_m.group(1)}"
                    f"（七型词表外自造型——悬念/危机/情感/反转/账目/信物/对位）"
                )

        if re.search(r"\*{0,2}payoff\s*拍\*{0,2}\s*[:：]\s*\S", content):
            c.append({"id": "G4.cp.payoff_beat", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_payoff_beat:{fp}")

        # spec #82 T7: retention window parameterized (was hardcoded 1-30 —
        # the retention gate self-extinguished past ch30 for every volume
        # after the first). market_params.retention_anchor {from_ch, to_ch};
        # absent config keeps the legacy hardcode (existing-project compat).
        _ra_from: int = 1
        _ra_to: int | None = 30
        if project_dir:
            from shenbi.gates.shared import read_genre_config as _rgc

            _ra = ((_rgc(project_dir) or {}).get("market_params", {}) or {}).get("retention_anchor")
            if isinstance(_ra, dict):
                _ra_from = int(_ra.get("from_ch", 1))
                _raw_to = _ra.get("to_ch")
                _ra_to = int(_raw_to) if _raw_to is not None else None  # None = 全卷
        _in_window = n >= _ra_from and (_ra_to is None or n <= _ra_to)
        if _in_window:
            if re.search(r"\*{0,2}留存锚\*{0,2}\s*[:：]\s*\S", content):
                c.append({"id": "G4.cp.retention_anchor", "file": fp, "s": GateStatus.PASS})
            else:
                mf.append(f"G4.cp.missing_retention_anchor:{fp}")
        else:
            c.append(
                {
                    "id": "G4.cp.retention_anchor",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": f"N={n}, retention window is chapters {_ra_from}-{_ra_to or '∞'}",
                }
            )

        # ── spec #82 T1: cross-chapter sequence gates (snapshot-sourced) ──
        _spec82_sequence_gates(content, n, project_dir, mf, c)
        # ── spec #82 T2: hook aging + defer budget (truth-block source) ──
        _spec82_hook_age(content, n, project_dir, mf, c)
        # ── spec #82 T6: core-motif supply floor (snapshot marker chain) ──
        _spec82_core_motif_touch(n, project_dir, mf, c)

        # Section 5: 关键抉择 — quality bonus, not hard gate
        s5_match = re.search(r"## 5\..*?\n(?=## 6\.|\Z)", content, re.DOTALL)
        s5_text = s5_match.group() if s5_match else ""
        if "关键抉择" not in s5_text:
            c.append(
                {
                    "id": "G4.cp.s5_choice",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "section 5 missing 关键抉择 keyword",
                }
            )
        else:
            c.append({"id": "G4.cp.s5_choice", "file": fp, "s": GateStatus.PASS})

        # Section 7: hook operation names (per SKILL.md, section 7 is 本章 hook 账)
        s7_match = re.search(r"## 7\..*?\n(?=## 8\.|\Z)", content, re.DOTALL)
        s7_text = s7_match.group() if s7_match else ""
        hook_ops = ["open", "advance", "resolve", "defer"]
        found_ops = [op for op in hook_ops if op in s7_text.lower()]
        if not found_ops:
            mf.append(f"G4.cp.s7_hook_ops:{fp}")
        else:
            c.append(
                {"id": "G4.cp.s7_hook_ops", "file": fp, "s": GateStatus.PASS, "ops": found_ops}
            )

        # #18-2: MH-namespace hook authenticity (registry read once above).
        if registered_hooks is None:
            c.append(
                {
                    "id": "G4.cp.hook_refs",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": "no book_spine/pending_hooks registry (phase 1)",
                }
            )
        else:
            refs = list(dict.fromkeys(re.findall(r"MH\d+", s7_text)))
            unknown = [r for r in refs if r not in registered_hooks]
            if unknown:
                mf.append(
                    f"G4.cp.hook_refs:{fp}:引用未注册钩子「{'、'.join(unknown)}」"
                    "（book_spine/pending_hooks 无此 MH 编号——新钩属 genesis/lifecycle "
                    "职权，memo 不得自造 MH 号；确需新钩请走 CP-NNN 或先注册再引用）"
                )
            else:
                c.append({"id": "G4.cp.hook_refs", "file": fp, "s": GateStatus.PASS})

        # Defer-silence rule (SKILL.md section 7 可自动检查规则; spec #9 R2):
        # rows with 操作=defer and 沉默章数 >= 4 require an 激活方案 or ABANDON
        # annotation in section 7. Only the EXACT-template column order
        # (ID | 操作 | 推进方式 | 沉默章数) is parsed; free-form tables
        # (e.g. Phase-1 placeholder prose) do not match and are not flagged.
        defer_silent = re.findall(r"\|\s*[^|]*\|\s*defer\s*\|[^|]*\|\s*(\d+)\s*\|", s7_text)
        if any(int(n) >= 4 for n in defer_silent) and not re.search(
            r"激活方案|ABANDON", s7_text, re.IGNORECASE
        ):
            mf.append(
                f"G4.cp.s7_defer_silence:{fp}: defer 行沉默章数 ≥4 须在段 7 附激活方案或 ABANDON 标注"
                "（如「激活方案：第N章以XX场景 advance」或「ABANDON：理由」）——沉默跨束不许无主"
            )
        else:
            c.append({"id": "G4.cp.s7_defer_silence", "file": fp, "s": GateStatus.PASS})

    if not fps:
        c.append({"id": "G4.cp", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-chapter-planning", c, "scoring", mf)
    return passed("G4-chapter-planning", c)


def _packing_hint() -> str:
    """Legalization routes for a failed cross-chapter pack (regen v3 F9).

    The packer sees the stream the model cannot (prev chapter's actual
    scenes + this declaration + the sibling memo); a bare 'adjust' sent
    dispatches into blind re-rolls. Two concrete routes always work.
    """
    return (
        "合法化最短路（二选一）：①本簇所有场景统一配对型 [900,1350]"
        "（任何相邻对和 ≤2700 必可打包，章和=3 场景×~1100 落带内）；"
        "②若保留独立型场景，首场景改配对型 [900,1400] 与前章末场配对"
        "（和须 ≤2800），独立型场景只出现在序列中部且两侧邻居和 ≤2800"
    )
