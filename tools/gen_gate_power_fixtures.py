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
from shenbi.gates.g4.chapter_drafting import (
    _text_fingerprint,  # 门指纹单源复用（测量面=执法面，C3）
)
from shenbi.gates.shared import strip_scene_markers
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
# surge 计数面句长阈（chapter_drafting.py:1265：slen>=35 且对白占比<0.5）
_SURGE_SENT_LEN = 35
# 指纹段 CJK 下限（chapter_drafting.py:443 _text_fingerprint min_len=50 同值）
_FINGERPRINT_MIN_CJK = 50
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


def _raw_paras(text: str) -> list[str]:
    return text.split("\n\n")


def _drop_meta_block(text: str, heading: str) -> str:
    """删含 *heading* 的整个 META 块（H2 段→其后首个 <!--META-END--> 段，闭区间）."""
    paras = _raw_paras(text)
    start = next(i for i, p in enumerate(paras) if heading in p)
    end = next(i for i in range(start, len(paras)) if "<!--META-END-->" in paras[i])
    return "\n\n".join([*paras[:start], *paras[end + 1 :]])


def word_count_truncated(text: str) -> str:
    """正文截断（保 PRE/POST 结构块＋首 3 叙事段）→ total < floor → word_count.

    NB6：--full 面——截断是块级手术，裁片本身已 < floor，红须来自变异非裁片。
    POST 块跨多 raw 段（H2 标题段与清单段分离）——尾部保留自 POST 标题段起整段。
    """
    paras = _raw_paras(text)
    post_start = max(i for i, p in enumerate(paras) if "## POST_WRITE_SELF_CHECK" in p)
    return "\n\n".join([*paras[:8], *paras[post_start:]])


def post_removed(text: str) -> str:
    """删 POST 整块（H2 段→META-END 段）→ post_check（NB6：--full 面）."""
    return _drop_meta_block(text, "## POST_WRITE_SELF_CHECK")


def pre_removed(text: str) -> str:
    """删 PRE 整块（H2 段→META-END 段）→ pre_check（NB6：--full 面）."""
    return _drop_meta_block(text, "## PRE_WRITE_CHECK")


def voice_stripped(text: str) -> str:
    """口癖短语（真实卡 voice_profile.catchphrases 原串）→中性语 → voice_density<min."""
    for phrase, neutral in _VOICE_NEUTRAL:
        text = text.replace(phrase, neutral)
    return text


_PLAN_V3_FMT = re.compile(r"^plan_format[：:]\s*v3\s*$", re.M)
# 段6「必填一行（章尾张力拍）」形：首个？后的章尾句 → v4 引句锚定形态
_PLAN_TIER_LINE = re.compile(r"^-\s*章尾张力拍[：:]\s*[^？]*？(.+)$", re.M)


def plan_v4_upgrade(text: str) -> str:
    """v3→v4 形升（plan_format v4＋张力拍『』引句锚定＋章尾钩型七型行）.

    引句取自真实 plan 段6 原句（该句与章尾实拍本就不同文——真实病理，
    quote_verbatim 臂的负例载荷即此）。基线形（无收束钩改写）供因果三查。
    """
    out = _PLAN_V3_FMT.sub("plan_format: v4", text, count=1)
    out = _PLAN_TIER_LINE.sub(r"- 章尾张力拍: [微]｜『\1』", out, count=1)
    return out.replace("plan_format: v4\n", "plan_format: v4\n\n章尾钩型: 悬念钩\n", 1)


def hookdecl_mismatched(text: str) -> str:
    """v4 升级＋场景2 收束钩声明改「悬念」形（章尾实拍不含）→ scene_hook_match."""
    out = plan_v4_upgrade(text)
    return re.sub(
        r"(场景2: \d+字｜(?:独立型|配对型)｜收束钩：).+$",
        r"\1悬念——城破那夜，他仍未参透老驼留下的切口。",
        out,
        count=1,
        flags=re.M,
    )


def post_quote_broken(text: str) -> str:
    """POST 金句位引句改一字（通行通→通行不通）→ 子句缺席 FAIL 臂."""
    return text.replace("场景2＝「灯在人在，路通行通。」", "场景2＝「灯在人在，路通行不通。」", 1)


def post_transition_lied(text: str) -> str:
    """章中段注入计数面连接词而 POST 仍报 0 → post_transition_cross."""
    paras = _raw_paras(text)
    out, done = [], False
    for p in paras:
        q = p
        if not done and "「差三文？」小满挤进来" in p:
            q, done = "不过，" + p, True
        out.append(q)
    return "\n\n".join(out)


def golden_emptied(text: str) -> str:
    """PRE 本章金句位值→无 → golden_slot WARN（值空集臂）."""
    return re.sub(r"^(- 本章金句位: ).+$", r"\1无", text, count=1, flags=re.M)


def post_wordcount_lied(text: str) -> str:
    """POST 总计字数改半（3625→1812）→ post_wordcount_precision WARN."""
    return re.sub(r"(正文字数（逐段计数合计）: .*总计 )3625", r"\g<1>1812", text, count=1)


def _shorten_sent(m: re.Match[str]) -> str:
    """≥35 字句内逗号→句号（surge 计数面＝segment_sentences ≥35 字句）."""
    sent = m.group(0)
    core, delim = sent[:-1], sent[-1]
    if not delim or len(core) < _SURGE_SENT_LEN:
        return sent
    return core.replace("，", "。") + delim


def surge_killed(text: str) -> str:
    """尾窗长句（≥35 字）切短 → surge 配额缺口（WARN-only 臂）."""
    paras = narrative_window(text)
    new_tail = [re.sub(r"[^。！？；]+[。！？；]", _shorten_sent, p) for p in paras[-11:]]
    return _with_tail(text, new_tail)


def simile_flooded(text: str) -> str:
    """尾窗追加 6 个闭集喻体句（SIMILE_MARKERS「像」面）→ per_1000>4 堆叠侧 WARN."""
    paras = narrative_window(text)
    return _with_tail(text, [*paras[-11:], *_SIMILE_PARAS])


def ending_ledgered(text: str) -> str:
    """末段追记账目收束句（≥2 阿拉伯数字串）→ ending_archetype_of=账目形态."""
    paras = narrative_window(text)
    tail = paras[-11:]
    tail[-1] += _LEDGER_CLOSER
    return _with_tail(text, tail)


def verbatim_copy(text: str) -> str:
    """无变异整本拷贝——比对章/基线章前置物（G0.9 real-output copy 面）."""
    return text


def content_duplicated(text: str, donor_text: str = "") -> str:
    """从比对章复制 k 段 append 章尾（k/(m+k)>0.40 指纹占比）→ content_overlap.

    I3 三条件：跨章复制＋集合指纹＋基数门槛 len(project-output/chapters/*.md)>1
    （比对章 fixture 同目录落盘）。k 按本章 m 动态取：k=2m//3+1（>2/3·m）。
    指纹口径=执法面（C3）：比对章按门侧 `_fingerprint_of` 无 strip 的 raw 形入
    集合——复制候选须 raw 指纹成员（场景标记邻接段在裁片面被拆分、raw 面
    合并，非成员段复制后不计交集；成员判定=同进程 hash 集合包含，语义等于
    字符串等值，跨进程确定）。
    """
    m = len(_text_fingerprint(strip_scene_markers(text)))
    k = 2 * m // 3 + 1
    donor_raw_fp = _text_fingerprint(donor_text)
    donor_paras = [
        p
        for p in narrative_window(donor_text)
        if len(re.findall(r"[一-鿿]", p)) >= _FINGERPRINT_MIN_CJK and hash(p) in donor_raw_fp
    ]
    copies = donor_paras[:k]
    if len(copies) < k:
        raise ValueError(f"donor raw-fp-member paras {len(copies)} < required k={k}")
    return text.rstrip("\n") + "\n\n" + "\n\n".join(copies) + "\n"


def payoff_axis_stripped(text: str) -> str:
    r"""删 **payoff 拍** 行的轴登记段（轴(债|名声|名字数|进度)→无轴）→ payoff_density WARN.

    变异源=plan 文件（先例 hookdecl_mismatched）；门侧正则锚
    chapter_drafting.py:1374-1375（\*\*payoff 拍\*\*[：:].*轴[（(]?(债|名声|名字数|进度)）。
    spec #118 T8（r2/I-7 收窄后唯一必建变异）。
    """
    return re.sub(
        r"(\*\*payoff 拍\*\*[：:][^｜\n]*?)｜轴[（(](?:债|名声|名字数|进度)[)）]",
        r"\1",
        text,
    )


MUTATIONS: dict[str, Callable[..., str]] = {
    "hook_killed": hook_killed,
    "protagonist_vanished": protagonist_vanished,
    "transition_flooded": transition_flooded,
    "scene_visuals_stripped": scene_visuals_stripped,
    "scene_markers_removed": scene_markers_removed,
    "fatigue_flooded": fatigue_flooded,
    "meta_injected": meta_injected,
    "word_count_truncated": word_count_truncated,
    "post_removed": post_removed,
    "pre_removed": pre_removed,
    "voice_stripped": voice_stripped,
    "hookdecl_mismatched": hookdecl_mismatched,
    "post_quote_broken": post_quote_broken,
    "post_transition_lied": post_transition_lied,
    "golden_emptied": golden_emptied,
    "post_wordcount_lied": post_wordcount_lied,
    "surge_killed": surge_killed,
    "simile_flooded": simile_flooded,
    "ending_ledgered": ending_ledgered,
    "verbatim_copy": verbatim_copy,
    "content_duplicated": content_duplicated,
    "payoff_axis_stripped": payoff_axis_stripped,
}


def main() -> int:
    """Generate one deterministic mutated fixture from a real chapter (CLI)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--mutation", required=True, choices=sorted(MUTATIONS))
    parser.add_argument("--full", action="store_true", help="不裁片（默认裁片 M4）")
    parser.add_argument(
        "--donor", type=Path, default=None, help="比对章源（content_duplicated 必填）"
    )
    args = parser.parse_args()
    src = args.source.read_text(encoding="utf-8")
    if args.mutation == "content_duplicated":
        if args.donor is None:
            parser.error("--donor required for content_duplicated")
        mutated = content_duplicated(src, args.donor.read_text(encoding="utf-8"))
    else:
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
