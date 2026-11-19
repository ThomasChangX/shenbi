#!/usr/bin/env python3
"""Spec #116 T4: deterministic real-chapter mutator → negative-example fixtures.

维护者侧一次性运行（源=gitignored 项目章）；产物提交 tests/fixtures/gate-power/。
确定性：同源同输出（无 RNG）；裁片（M4/I7）：frontmatter＋被测叙事尾窗段。
窗口面与门同序（import Task 1 narrative_window——测量面=执法面，C3）。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # repo 根——统一 tools. 包身份（NB 系）
from tools.gate_power_replay import (
    narrative_window,  # 同目录工具互引（E402 豁免 sys.path 修改）
)

PROVENANCE_TMPL = (
    "<!--\nprovenance: real-output-mutation (G0.9)\nsource: {source} (gitignored 项目真实产物)\n"
    "mutation: {name} (tools/gen_gate_power_fixtures.py, spec #116 T4)\n"
    "excerpt: {excerpt_note}\n"
    "generated: {today} (维护者侧一次性; 确定性: 同源同输出)\n-->\n\n"
)

_TENSION_RE = re.compile(
    r"(但|然而|却|不过|还|仍|依然|尚未|未解|不知|等待|没说|没答|瞒|藏|账|欠|谜|未完|代价)"
)
# I5：注入词必须取自 count_transition_words 计数面（shared.py:911 TRANSITION_SPECIFIC）
_TRANSITION_FILLERS = ["不过，", "此时，", "突然，", "终于，", "于是，"]

# 场景具体性门（chapter_drafting.py:1130）视觉动词面——多字词先替再换单字，
# 替换字「在」不在任何门词表（张力/疲劳/元叙事/转折）上，零副作用。
_VN_MULTI = ("发现", "看到", "听到")
_VN_SINGLE = frozenset("走跑推拉抓坐站躺倒看听触")
# I1：META_NARRATIVE 7 词闭集（shared.py:902-910）的子集注入——闭集内取词非生造
_META_PARA = "由此可见：这一切早有注定。综上所述，各人有各人的账。"
# 疲劳剂量：门阈 8（chapter_drafting.py:996），9 发必中且留 1 发余量
_FATIGUE_DOSE = 9
# 比喻堆叠（simile_band WARN 面）：SIMILE_MARKERS（shared.py:246）闭集内取「像」
_SIMILE_PARAS = [
    "火星像一粒算珠，飘到一半就灭了。",
    "灯影像一页翻旧的账，边角卷着。",
    "他的呼吸像账上挂着的利息，很轻，但没有停。",
    "盐包像一方压舱的秤砣，坠在袖子里。",
    "更鼓声像两笔记进红笔的账，一声一声。",
    "雪落得像纸页翻动，没有声音。",
]
# 收尾多样性（账目形态原型）：strip 后尾窗 ≥2 个阿拉伯数字串即归类
_LEDGER_CLOSER = "这一夜他合上册子，又数了一遍：外欠 30 文，袋底剩 17 文。"
# 口癖短语（真实 protagonist.md voice_profile.catchphrases 原串）→中性语
_VOICE_NEUTRAL = [
    ("这笔我先记下", "这笔先放在一旁"),
    ("折旧完了，人就自由了", "事情到此就过去了"),
    ("此账必有还之日", "这件事以后再提"),
    ("行，先算账", "行，先这样"),
]


def _frontmatter_end(paras: list[str]) -> int:
    if not paras or not paras[0].startswith("---"):
        return 0
    for i, p in enumerate(paras[1:], start=1):
        if p.strip() == "---":
            return i + 1
    return 0


def excerpt_tail(text: str, keep_after: int = 3) -> str:
    """I7 裁片：frontmatter＋叙事尾窗段（变异落点在尾窗内）."""
    paras = text.split("\n\n")
    fm = paras[: _frontmatter_end(paras)]
    narrative = narrative_window(text)
    tail = narrative[-(8 + keep_after) :]
    return "\n\n".join(fm + tail)


def hook_killed(text: str) -> str:
    """章尾窗口（narrative_window 尾 8 段）张力词→中性、删？与数字串."""
    paras = narrative_window(text)
    head, tail = paras[:-8], paras[-8:]
    out = []
    for p in tail:
        q = _TENSION_RE.sub("就", p)
        q = re.sub(r"[？?]", "。", q)
        q = re.sub(r"\d+", "数", q)
        out.append(q)
    return "\n\n".join(head + out)


def protagonist_vanished(text: str) -> str:
    """主角名→术赤；「他」全替换（含「」归属位）→ total < 3."""
    text = text.replace("那罕", "术赤")
    # C2：归属位一并替换（「他」单独即 ≥3）
    return text.replace("他", "此人")


def transition_flooded(text: str) -> str:
    """全章 narrative 段首注入计数面连接词（不过/此时/突然/终于/于是）."""
    paras = text.split("\n\n")
    out = []
    i = 0
    for p in paras:
        s = p.strip()
        if s and not s.startswith(("#", ">", "---", "- [", "<!--")):
            out.append(_TRANSITION_FILLERS[i % len(_TRANSITION_FILLERS)] + p)
            i += 1
        else:
            out.append(p)
    return "\n\n".join(out)


def _with_tail(text: str, new_tail: list[str], keep_after: int = 3) -> str:
    """叙事尾窗段替换后回拼（头段＋新尾段；窗口面=narrative_window 尾 8+keep_after）."""
    paras = narrative_window(text)
    head, _old = paras[: -(8 + keep_after)], paras[-(8 + keep_after) :]
    return "\n\n".join(head + new_tail)


def scene_visuals_stripped(text: str) -> str:
    """尾窗段视觉动词/对白标记剥除（→静态陈述）→ no_visual_scene."""
    paras = narrative_window(text)
    tail = paras[-11:]
    out = []
    for p in tail:
        q = p
        for w in _VN_MULTI:
            q = q.replace(w, "在")
        q = "".join("在" if ch in _VN_SINGLE else ch for ch in q)
        q = q.replace("「", "").replace("」", "")
        out.append(q)
    return _with_tail(text, out)


def scene_markers_removed(text: str) -> str:
    """删场景标记行（is_scene_marker_line 同形：strip()==<!--SCENE-->）→ scene_count<2."""
    return "\n".join(ln for ln in text.split("\n") if ln.strip() != "<!--SCENE-->")


def fatigue_flooded(text: str) -> str:
    """尾窗前 9 叙事段段尾追加「他心中暗道。」×9（FATIGUE_BASE「暗道」面）→ fatigue>8."""
    paras = narrative_window(text)
    tail = paras[-11:]
    out = []
    for i, p in enumerate(tail):
        out.append(p + "他心中暗道。" if i < _FATIGUE_DOSE else p)
    return _with_tail(text, out)


def meta_injected(text: str) -> str:
    """尾窗末段前插入 META_NARRATIVE 闭集词段（由此可见/综上所述）→ meta."""
    paras = narrative_window(text)
    tail = paras[-11:]
    return _with_tail(text, [*tail[:-1], _META_PARA, tail[-1]])


MUTATIONS: dict[str, Callable[..., str]] = {
    "hook_killed": hook_killed,
    "protagonist_vanished": protagonist_vanished,
    "transition_flooded": transition_flooded,
    "scene_visuals_stripped": scene_visuals_stripped,
    "scene_markers_removed": scene_markers_removed,
    "fatigue_flooded": fatigue_flooded,
    "meta_injected": meta_injected,
}


def main() -> int:
    """Generate one deterministic mutated fixture from a real chapter (CLI)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--mutation", required=True, choices=sorted(MUTATIONS))
    parser.add_argument("--full", action="store_true", help="不裁片（默认裁片 M4）")
    args = parser.parse_args()
    src = args.source.read_text(encoding="utf-8")
    mutated = MUTATIONS[args.mutation](src)
    note = (
        "全章（裁片不足以承载该变异——README 记裁定）"
        if args.full
        else "frontmatter + 叙事尾窗 (M4 裁片)"
    )
    if not args.full:
        mutated = excerpt_tail(mutated)
    header = PROVENANCE_TMPL.format(
        source=str(args.source),
        name=args.mutation,
        excerpt_note=note,
        today=date.today().isoformat(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(header + mutated, encoding="utf-8")
    print(f"{args.out} <- {args.source} [{args.mutation}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
