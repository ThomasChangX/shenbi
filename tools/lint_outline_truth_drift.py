"""Outline↔truth canon drift reconciliation lint (spec #83 T3).

驱动侧对账工具（只报不写）：正文运行期立起来的 canon（truth 持有物/来历/
承诺件/欠账）与卷纲（``outline/volume_map.md``）之间的漂移清单。finding 一律
交人工裁定双择一——volume_map 节点行就地更新，或行内 ``※canon-vN`` 引注——
不许悬空。对账器只对结构化可判定子集动手（清单枚举/词集交集/grep 缺件），
语义级留评审，不造 NLP 假象（铁律 L-C）。

四个对账面（spec §3）：

1. 物象清单对账——卷纲节点行「A、B、C——N件」枚举 vs
   ``truth/facts/props.json`` 持有集：同族持有物（名含节点项或节点项含名）
   缺席节点清单 → finding（P1-2 类：第二把哨在 truth 持有、节点清单只一把）。
2. 来历短语对账——卷纲跨卷桥接（物品/信息行）描述 vs
   ``truth/prop_registry.md`` 经手事件：双方 2+ 字中文词集（连续汉字段，最粗
   粒度）交集为空 → finding；``--strict`` 收紧为需 ≥2 个共享词才 pass。
3. 承诺件对账——卷纲「金句出场点/卷末彩蛋」引号句＋「梗位复用」逐项 grep
   全卷正文，缺件 → finding（渡鸦局档案卡实证）。
4. 欠账对账——正文「欠」「还之日」句式行 vs
   ``genesis-context/chapter_outline.md`` 还账进度表（私账打卡）：词集零交集
   （运行期新账不在排期）→ finding；该文件缺失或无该节 → 本面 SKIP（不硬崩）。

``--declarations`` 子命令面（spec #83 T7 声明面漂移清单：scene_hook 11 行 +
voice_density + 无 META 块）为预留骨架，未实装（Task 13 落地），显式报错 exit 2。

CLI: ``uv run python tools/lint_outline_truth_drift.py <dir> [--volume N]``；
exit 0 = 零悬空 finding / 1 = 有 finding / 2 = 用法或输入错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

#: 中文词集提取——最粗粒度连续汉字段（≥2 字），不造分词假象（spec r5.2 钉）。
_CJK_RUN_RE = re.compile(r"[一-龥]{2,}")

_VOLUME_HEAD_RE = re.compile(r"^##\s*第([一二两三四五六七八九十]{1,3}|\d+)卷[^\n]*", re.M)
_VOLUME_RANGE_RE = re.compile(r"[（(]\s*第\s*(\d+)\s*[–—\-~～]\s*(\d+)\s*章\s*[）)]")
_VOLUME_RANGE_FALLBACK_RE = re.compile(
    r"章节范围\**\s*[：:]\s*第\s*(\d+)\s*章\s*[-–—~～]\s*第\s*(\d+)\s*章"
)
#: 节点行内「…：A、B、C、D——N件…」道具枚举（volume_map.md:88 实锚形）。
_ENUM_RE = re.compile(r"[：:]([^：:｜|—]+?)——[一二两三四五六七八九十\d]+\s*件")
_NODE_ROW_RE = re.compile(r"^\|\s*第\s*(\d+)\s*章\s*\|")
#: 跨卷桥接表行：| # | 实体：描述 | 类型 | 带入卷 | …（volume_map.md:102-109 实锚形）。
_HOOK_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*([^|：:]+)[：:]\s*([^|]+?)\s*\|\s*(物品|信息|人物)\s*\|"
)
_QUOTE_RE = re.compile(r"「([^「」]+)」")
_PROMISE_LABEL_RE = re.compile(r"^\s*(金句出场点|母题物象|梗位复用|卷末彩蛋)\s*[：:]\s*(.*)$")
_PROMISE_LINE_KEY = "金句、母题物象与梗位"
#: 欠账对账数据源锚：种子 chapter_outline.md:370「还账进度表（私账打卡）」行。
_SCHEDULE_KEY = "还账进度表"
_CHAPTER_FILE_RE = re.compile(r"chapter-(\d+)\.md")

#: 来历短语对账收紧阈值（--strict）：共享词 ≥2 才 pass（默认任一共享词即 pass）。
_STRICT_MIN_SHARED = 2
#: 结构长度下限（节点枚举项/梗位项最短 2 字；registry 表行最少 3 列）。
_MIN_ITEM_LEN = 2
_MIN_REGISTRY_CELLS = 3
#: finding 摘录长度（来历描述/欠账句截断）。
_DESC_EXCERPT_LEN = 32
_DEBT_EXCERPT_LEN = 60

_CN_DIGITS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


@dataclass
class Finding:
    """一条 canon 漂移 finding（只报不写，人工裁定面）."""

    face: str
    detail: str


@dataclass
class _Ctx:
    """一次对账运行的取数上下文（卷 section＋章节范围＋在档正文）."""

    project: Path
    section: str
    lo: int
    hi: int
    chapter_texts: dict[int, str]
    strict: bool


def _cn_to_int(s: str) -> int:
    """中文卷号（一～十二）/阿拉伯数字 → int."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    if "十" in s:
        head, _, tail = s.partition("十")
        return _CN_DIGITS.get(head, 1) * 10 + _CN_DIGITS.get(tail, 0)
    return _CN_DIGITS.get(s, 0)


def cjk_words(text: str) -> set[str]:
    """2+ 字连续汉字词集（最粗粒度，spec r5.2 钉——不造分词假象）."""
    return set(_CJK_RUN_RE.findall(text))


def _shared_shingles(a: str, b: str) -> bool:
    """两实体名是否共享任一 2 字汉字子串（同族配对用，最粗粒度）."""

    def shingles(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(len(s) - 1) if _CJK_RUN_RE.fullmatch(s[i : i + 2])}

    return bool(shingles(a) & shingles(b))


def volume_section(vm_text: str, volume: int) -> tuple[str, int, int]:
    """取第 N 卷 section 文本与章节范围（标题行「（第 a–b 章）」优先）.

    Raises:
        ValueError: 卷标题缺席或章节范围不可解析。
    """
    heads = list(_VOLUME_HEAD_RE.finditer(vm_text))
    target = next((m for m in heads if _cn_to_int(m.group(1)) == volume), None)
    if target is None:
        raise ValueError(f"outline/volume_map.md 未找到第{volume}卷标题（## 第N卷…）")
    sec_start = target.start()
    later = [m.start() for m in heads if m.start() > sec_start]
    section = vm_text[sec_start : later[0] if later else len(vm_text)]
    rm = _VOLUME_RANGE_RE.search(target.group(0))
    if rm:
        return section, int(rm.group(1)), int(rm.group(2))
    fm = _VOLUME_RANGE_FALLBACK_RE.search(section)
    if fm:
        return section, int(fm.group(1)), int(fm.group(2))
    raise ValueError(f"第{volume}卷标题不带章节范围且卷内无「章节范围」行")


def _chapter_texts(project: Path, lo: int, hi: int) -> dict[int, str]:
    """卷范围（lo–hi）内在档正文：chapters/chapter-N.md → {N: 文本}."""
    out: dict[int, str] = {}
    d = project / "chapters"
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        m = _CHAPTER_FILE_RE.fullmatch(p.name)
        if m and p.is_file() and lo <= int(m.group(1)) <= hi:
            out[int(m.group(1))] = p.read_text(encoding="utf-8")
    return out


def _registry_rows(registry_text: str) -> list[tuple[str, str]]:
    """prop_registry.md 三列表 → [(实体名, 经手事件)]（表头/分隔行跳过）."""
    rows: list[tuple[str, str]] = []
    for line in registry_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < _MIN_REGISTRY_CELLS or not cells[0] or cells[0] == "实体名":
            continue
        if set(cells[0]) <= set("-— "):
            continue
        rows.append((cells[0], cells[2]))
    return rows


def _face_props(ctx: _Ctx) -> tuple[list[Finding], str | None]:
    """面 1 物象清单对账：节点行枚举道具集 vs props.json 持有集.

    持有物（与节点枚举项同族——名含项或项含名）缺席节点清单 → finding。
    """
    props_path = ctx.project / "truth" / "facts" / "props.json"
    if not props_path.is_file():
        return [], "truth/facts/props.json 缺席 → 物象清单对账 SKIP"
    try:
        data = json.loads(props_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], "truth/facts/props.json 解析失败 → 物象清单对账 SKIP"
    props = data.get("facts", {}) if isinstance(data, dict) else {}
    holdings = {str(k): str(v.get("owner", "")) for k, v in props.items() if isinstance(v, dict)}

    findings: list[Finding] = []
    for line in ctx.section.splitlines():
        row = _NODE_ROW_RE.match(line)
        if not row:
            continue
        ch = int(row.group(1))
        if not ctx.lo <= ch <= ctx.hi:
            continue
        for enum in _ENUM_RE.finditer(line):
            for item in (it.strip() for it in enum.group(1).split("、")):
                if len(item) < _MIN_ITEM_LEN:
                    continue
                for name, owner in holdings.items():
                    if name == item or not (item in name or name in item):
                        continue
                    findings.append(
                        Finding(
                            "物象清单对账",
                            f"第{ch}章节点清单枚举『{item}』：truth 持有『{name}』"
                            f"（owner={owner}）缺席节点清单——双择一"
                            "（节点行就地更新 or ※canon-vN 引注）",
                        )
                    )
    return findings, None


def _face_provenance(ctx: _Ctx) -> tuple[list[Finding], str | None]:
    """面 2 来历短语对账：跨卷桥接描述 vs prop_registry 经手事件（词集交集）."""
    reg_path = ctx.project / "truth" / "prop_registry.md"
    if not reg_path.is_file():
        return [], "truth/prop_registry.md 缺席 → 来历短语对账 SKIP"
    reg_rows = _registry_rows(reg_path.read_text(encoding="utf-8"))
    min_shared = _STRICT_MIN_SHARED if ctx.strict else 1

    findings: list[Finding] = []
    in_hook = False
    for line in ctx.section.splitlines():
        if "跨卷桥接" in line:
            in_hook = True
            continue
        if in_hook and line.startswith("#"):
            in_hook = False
            continue
        if not in_hook:
            continue
        hook = _HOOK_ROW_RE.match(line)
        if not hook or hook.group(3) == "人物":  # prop_registry 只对物/信息
            continue
        entity, desc = hook.group(1).strip(), hook.group(2).strip()
        desc_words = cjk_words(desc)
        for name, event in reg_rows:
            if not _shared_shingles(entity, name):
                continue
            shared = desc_words & cjk_words(event)
            if len(shared) >= min_shared:
                continue
            ell = "…" if len(desc) > _DESC_EXCERPT_LEN else ""
            findings.append(
                Finding(
                    "来历短语对账",
                    f"卷纲『{entity}：{desc[:_DESC_EXCERPT_LEN]}{ell}』"
                    f"与 prop_registry『{name}』经手事件 2+ 字词集交集为空"
                    f"（共享 {len(shared)} 词 < {min_shared}）——来历短语漂移，"
                    "人工裁定（改大纲 or ※canon-vN 引注）",
                )
            )
    return findings, None


def _face_promise(ctx: _Ctx) -> tuple[list[Finding], str | None]:
    """面 3 承诺件对账：金句/彩蛋引号句＋梗位复用项 grep 全卷正文缺件."""
    if not ctx.chapter_texts:
        return [], f"chapters/ 无第{ctx.lo}-{ctx.hi}章在档文件 → 承诺件对账 SKIP"
    promise_line = next((ln for ln in ctx.section.splitlines() if _PROMISE_LINE_KEY in ln), None)
    if promise_line is None:
        return [], None
    # 去掉「**金句、母题物象与梗位**:」头（冒号半/全角两形）
    body = promise_line[promise_line.find(_PROMISE_LINE_KEY) + len(_PROMISE_LINE_KEY) :]
    body = re.sub(r"^\**\s*[：:]\s*", "", body)

    terms: list[tuple[str, str]] = []
    for seg in body.split("｜"):
        m = _PROMISE_LABEL_RE.match(seg)
        if not m:
            continue
        label, content = m.group(1), m.group(2).strip()
        if label in ("金句出场点", "卷末彩蛋"):
            terms.extend((label, q) for q in _QUOTE_RE.findall(content))
        elif label == "梗位复用":
            for raw in content.split("、"):
                item = _QUOTE_RE.sub(r"\1", raw.strip()).split("（")[0].strip()
                if len(item) >= _MIN_ITEM_LEN:
                    terms.append((label, item))
    prose = "\n".join(ctx.chapter_texts.values())
    findings = [
        Finding(
            "承诺件对账",
            f"卷纲『{label}』承诺件『{term}』grep 全卷正文零命中"
            f"（卷内在档 {len(ctx.chapter_texts)} 章）——承诺缺件，人工裁定"
            "（正文补兑现 or 卷纲调整）",
        )
        for label, term in terms
        if term not in prose
    ]
    return findings, None


def _schedule_words(outline_text: str) -> set[str] | None:
    """种子 chapter_outline.md「还账进度表（私账打卡）」行词集；无该行 → None."""
    for line in outline_text.splitlines():
        if _SCHEDULE_KEY in line:
            return cjk_words(line)
    return None


def _face_debt(ctx: _Ctx) -> tuple[list[Finding], str | None]:
    """面 4 欠账对账：正文「欠」「还之日」句式行 vs 还账进度表词集.

    schedule 缺席（种子文件/进度表节缺失）时本面 SKIP。
    """
    seed_path = ctx.project / "genesis-context" / "chapter_outline.md"
    if not seed_path.is_file():
        return [], "genesis-context/chapter_outline.md 缺席 → 欠账对账 SKIP"
    words = _schedule_words(seed_path.read_text(encoding="utf-8"))
    if words is None:
        return [], "genesis-context/chapter_outline.md 无还账进度表节 → 欠账对账 SKIP"

    findings: list[Finding] = []
    for ch in sorted(ctx.chapter_texts):
        for ln, line in enumerate(ctx.chapter_texts[ch].splitlines(), 1):
            if "欠" not in line and "还之日" not in line:
                continue
            if cjk_words(line) & words:
                continue
            excerpt = line.strip()
            if len(excerpt) > _DEBT_EXCERPT_LEN:
                excerpt = excerpt[:_DEBT_EXCERPT_LEN] + "…"
            findings.append(
                Finding(
                    "欠账对账",
                    f"ch{ch}:L{ln} 欠账句『{excerpt}』与还账进度表词集零交集——"
                    "运行期立账不在排期，人工裁定（排期补行 or ※canon-vN 引注）",
                )
            )
    return findings, None


def _lint_all(
    project_dir: Path, *, volume: int, strict: bool
) -> tuple[list[Finding], list[str], _Ctx]:
    """只读运行四对账面：返回 (findings, skip 说明, 运行上下文)."""
    project = Path(project_dir)
    vm_path = project / "outline" / "volume_map.md"
    if not vm_path.is_file():
        raise ValueError(f"缺少 outline/volume_map.md：{vm_path}")
    section, lo, hi = volume_section(vm_path.read_text(encoding="utf-8"), volume)
    ctx = _Ctx(project, section, lo, hi, _chapter_texts(project, lo, hi), strict)

    findings: list[Finding] = []
    skips: list[str] = []
    for face in (_face_props, _face_provenance, _face_promise, _face_debt):
        face_findings, note = face(ctx)
        findings.extend(face_findings)
        if note:
            skips.append(note)
    return findings, skips, ctx


def run_lint(project_dir: Path, *, volume: int = 1, strict: bool = False) -> list[Finding]:
    """只读运行四对账面，返回全部 finding（SKIP 面不入 finding 集）."""
    return _lint_all(Path(project_dir), volume=volume, strict=strict)[0]


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：stdout 报告 + exit code（0=零 finding / 1=有 / 2=用法错误）."""
    parser = argparse.ArgumentParser(
        description="卷纲↔truth canon 漂移对账（spec #83 T3，只报不写）"
    )
    parser.add_argument("dir", type=Path, help="项目目录（含 outline/ truth/ chapters/）")
    parser.add_argument("--volume", type=int, default=1, help="卷号（默认 1）")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="来历短语对账收紧：需 ≥2 个共享 2+ 字词才 pass（默认任一共享词即 pass）",
    )
    parser.add_argument(
        "--declarations",
        action="store_true",
        help="声明面漂移清单（scene_hook/voice_density/无 META 块）——未实装（Task 13）",
    )
    args = parser.parse_args(argv)

    if args.declarations:
        print(
            "错误: --declarations 子命令未实装（spec #83 T7 声明面漂移清单，Task 13 落地）；"
            "本版本只预留参数骨架",
            file=sys.stderr,
        )
        return 2

    try:
        findings, skips, ctx = _lint_all(args.dir, volume=args.volume, strict=args.strict)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    print("卷纲↔truth canon 漂移对账（spec #83 T3，只报不写）")
    print(
        f"目录: {args.dir}　卷: {args.volume}"
        f"（第 {ctx.lo}-{ctx.hi} 章；在档正文 {len(ctx.chapter_texts)} 章）"
    )
    for note in skips:
        print(f"SKIP: {note}")
    faces: dict[str, list[Finding]] = {}
    for f in findings:
        faces.setdefault(f.face, []).append(f)
    for face in ("物象清单对账", "来历短语对账", "承诺件对账", "欠账对账"):
        if face not in faces:
            continue
        print(f"[{face}] {len(faces[face])} finding")
        for f in faces[face]:
            print(f"  - {f.detail}")
    if findings:
        print(f"合计: {len(findings)} finding → exit 1（人工裁定：改大纲 or ※canon-vN 引注）")
        return 1
    print("零悬空 finding → exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
