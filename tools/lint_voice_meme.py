#!/usr/bin/env python3
"""Voice, meme and quote lints (spec #76).

Modes:
  chapter <dir> --chapter N   voice density report (v2 = memo plan_format token)
  volume  <dir> --volume N    meme quota / burning-quote quota / appearance-
                              conditioned catchphrase window
  blind                        deterministic blind attribution (constructed
                              five-character corpus + marker classifier)

File predicate (volume mode): only chapter-N.md — excludes *pre-rev*/snapshots
(G2 snapshot-exemption rule). F947: zero LLM dispatch; blind corpus is
constructed (G0.9 structural exemption).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from shenbi.gates.shared import strip_narrative_body
from shenbi.text.voice_lexicon import (
    DEFAULT_VOICE_DENSITY_MIN,
    catchphrases_from_card,
    distinct_voice_signals,
)

_CN = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
_QUOTE_SPAN_RE = re.compile(r"「([^」]+)」")
_BLIND_MIN_CORRECT = 4
_MEME_SEG_RE = re.compile(r"梗位复用[：:]")


def _chapter_files(project: Path, vol_start: int, vol_end: int) -> list[Path]:
    out = []
    for n in range(vol_start, vol_end + 1):
        f = project / "chapters" / f"chapter-{n}.md"
        if f.is_file():
            out.append(f)
    return out


def _volume_section(volume_map: Path, volume: int) -> str:
    """The volume's own map section (node rows scoped per-volume)."""
    cn = _CN[volume - 1]
    text = volume_map.read_text(encoding="utf-8")
    head = re.search(rf"## 第{cn}卷：", text)
    if not head:
        return ""
    body = text[head.end() :]
    nxt = re.search(r"\n## 第[一二三四五六七八九十]+卷：", body)
    return body[: nxt.start()] if nxt else body


def _volume_span(volume_map: Path, volume: int) -> tuple[int, int]:
    cn = _CN[volume - 1]
    m = re.search(
        rf"## 第{cn}卷：[^\n]*?（第\s*(\d+)\s*[-–—]\s*(\d+)\s*章）",
        volume_map.read_text(encoding="utf-8"),
    )
    if not m:
        raise SystemExit(f"volume heading not found: 第{cn}卷")
    return int(m.group(1)), int(m.group(2))


def _meme_list(volume_map: Path, volume: int) -> list[str]:
    """Extract every quoted span inside the meme segment.

    段边界 = 至下一 ｜ 或行尾（覆盖 第N章「X」 带章号形态）。
    """
    cn = _CN[volume - 1]
    text = volume_map.read_text(encoding="utf-8")
    head = re.search(rf"## 第{cn}卷：", text)
    if not head:
        return []
    body = text[head.end() :]
    nxt = re.search(r"\n## 第[一二三四五六七八九十]+卷：", body)
    if nxt:
        body = body[: nxt.start()]
    memes: list[str] = []
    for line in body.split("\n"):
        if not _MEME_SEG_RE.search(line):
            continue
        seg = _MEME_SEG_RE.split(line, 1)[1]
        seg = re.split(r"[｜|]", seg, maxsplit=1)[0]
        memes.extend(_QUOTE_SPAN_RE.findall(seg))
    return memes


def _genre_params(project: Path) -> dict:
    gc = project / "genre-config.json"
    if not gc.is_file():
        return {}
    try:
        return json.loads(gc.read_text(encoding="utf-8")).get("market_params", {})
    except ValueError:
        return {}


def lint_chapter(project: Path, chapter: int) -> list[str]:
    """Voice density report (the v2 FAIL verdict lives in G4.cd)."""
    memo = project / "plans" / f"chapter-{chapter}-plan.md"
    v2 = False
    if memo.is_file():
        v2 = (
            re.search(
                r"^plan_format[：:]\s*v[2-9]\s*$", memo.read_text(encoding="utf-8"), re.MULTILINE
            )
            is not None
        )
    ch = project / "chapters" / f"chapter-{chapter}.md"
    if not ch.is_file():
        return [f"chapter-{chapter}.md not found"]
    body = ch.read_text(encoding="utf-8")
    cps: list[str] = []
    pcard = project / "characters" / "protagonist.md"
    if pcard.is_file():
        cps = catchphrases_from_card(pcard.read_text(encoding="utf-8"))
    signals = distinct_voice_signals(strip_narrative_body(body), cps)
    vmin = int(
        _genre_params(project)
        .get("voice_density_min", {})
        .get("min_per_chapter", DEFAULT_VOICE_DENSITY_MIN)
    )
    tag = "v2" if v2 else "v1"
    if signals < vmin:
        domain = "FAIL 域(v2)" if v2 else "WARN 域(v1)"
        return [f"[声口] ch{chapter}({tag}) 密度 {signals}/{vmin} 缺——{domain}"]
    return [f"[声口] ch{chapter}({tag}) 密度 {signals}/{vmin} 达标"]


def _is_v2(project: Path, f: Path) -> bool:
    """Chapter is plan_format v2 (memo token)."""
    m = re.search(r"chapter-(\d+)", f.stem)
    if not m:
        return False
    mp = project / "plans" / f"chapter-{m.group(1)}-plan.md"
    return mp.is_file() and bool(
        re.search(r"^plan_format[：:]\s*v[2-9]\s*$", mp.read_text(encoding="utf-8"), re.MULTILINE)
    )


def lint_volume(project: Path, volume: int) -> list[str]:
    """Meme quota, burning-quote quota and catchphrase window (all WARN)."""
    vm = project / "outline" / "volume_map.md"
    start, end = _volume_span(vm, volume)
    files = _chapter_files(project, start, end)
    corpus = "\n".join(f.read_text(encoding="utf-8") for f in files)
    params = _genre_params(project)
    out: list[str] = []
    # 梗位配额（缺额 WARN——#79 循环卷末 FAIL 消费）
    quota = int(params.get("meme_quota", {}).get("per_volume", 3))
    for meme in _meme_list(vm, volume):
        hits = corpus.count(meme)
        if hits < quota:
            out.append(f"[梗位] {meme} 卷内 {hits}/{quota}——下章 PRE_WRITE_CHECK 补触")
    # 燃句配额（v2 章分母）
    burn_min = int(params.get("quote_type_quota", {}).get("burning_per_volume", 2))
    v2_files = [f for f in files if _is_v2(project, f)]

    if v2_files:
        burns = sum(
            1
            for f in v2_files
            if re.search(
                r"^-\s*\[.\]\s*金句位[：:]\s*燃｜", f.read_text(encoding="utf-8"), re.MULTILINE
            )
        )
        if burns < burn_min:
            out.append(f"[金句] 燃句卷内 {burns}/{burn_min}（v2 分母 {len(v2_files)} 章）")
    # 登场条件化 catchphrase 窗（登场集 = 卷纲节点表名集）
    node_rows = [
        ln for ln in _volume_section(vm, volume).split("\n") if re.match(r"\s*\|\s*第\d+章", ln)
    ]
    vol_text = corpus
    for card in sorted((project / "characters" / "major").glob("*.md")):
        card_text = card.read_text(encoding="utf-8")
        cps = catchphrases_from_card(card_text)
        if not cps:
            continue
        # 登场判据：卡 name: 域显示名在本卷节点行（stem 回退），或任一口癖在卷正文
        nm = re.search(r"^name[：:]\s*(\S+)", card_text, re.MULTILINE)
        display = nm.group(1) if nm else card.stem
        present = any(display in ln for ln in node_rows) or any(cp in vol_text for cp in cps)
        if present and not any(cp in vol_text for cp in cps):
            out.append(f"[配角声口] {display} 卷内登场但口癖 0 次")
    # spec #82 T4: per-catchphrase 卷配额（超用帽——默认每 3 章 ≤1；
    # 「这笔我先记下」卷一 26 处 vs 建议值 12 的教训。超配 → FAIL 面，
    # 由 regen-accept 判据 4 消费（既有调用面自动获得））
    chapters_in_vol = max(1, len(files))
    cap_scale = chapters_in_vol // 3 or 1
    for card in sorted((project / "characters" / "major").glob("*.md")):
        for cp in catchphrases_from_card(card.read_text(encoding="utf-8")):
            hits = vol_text.count(cp)
            if hits > cap_scale:
                out.append(
                    f"[口癖帽] {cp} 卷内 {hits} 次 > 建议 {cap_scale}（每 3 章 ≤1——spec #82 T4）"
                )
    return out


_BLIND_CORPUS = [
    ("小满", "他说：先活下来再说吧。", {"小满": 1}),
    ("老驼", "记住的事，别烂在肚里。", {"老驼": 1}),
    ("灯", "拿着。别问为什么。", {"灯": 1}),
    ("灰烬", "下辈子再见。", {"灰烬": 1}),
    ("帖木哥", "帝国的血管，一站一站。", {"帖木哥": 1}),
    ("小满", "无标记的普通句子。", {}),
    ("混淆", "他说：先活下来再说吧。下辈子再见。", {"小满": 1, "灰烬": 1}),
    ("灯", "又一无标记句。", {}),
    ("小满", "先活下来再说。先活下来再说。先活下来再说。下辈子再见。下辈子再见。", {}),
]
_BLIND_MARKERS = {
    "小满": ["先活下来再说"],
    "老驼": ["别烂在肚里"],
    "灯": ["拿着。", "别问为什么"],
    "灰烬": ["下辈子再见"],
    "帖木哥": ["帝国的血管"],
}


def lint_blind() -> tuple[int, int, list[str]]:
    """Deterministic blind attribution: marker argmax per line.

    角色口径 rollup（spec §3 五角色 ≥4/5）：有标记行的角色计对 = 其标记行
    归属正确且分离边际成立（次高 < 最高×0.6）；混淆行平票 → 无归属（压测
    披露，不入分母）；零标记行 → 无归属（压测披露）。
    """
    per_char: dict[str, list[bool]] = {}
    details: list[str] = []
    for true_speaker, line, _expect in _BLIND_CORPUS:
        scores = {sp: sum(line.count(m) for m in ms) for sp, ms in _BLIND_MARKERS.items()}
        top = max(scores.values())
        winners = [sp for sp, s in scores.items() if s == top]
        pred = winners[0] if top > 0 and len(winners) == 1 else None
        if pred is None:
            details.append(f"no-attribution: true={true_speaker} top={top} (平票/零标记)")
            continue
        second = sorted(scores.values())[-2]
        margin_ok = second < top * 0.6
        ok = pred == true_speaker and margin_ok
        per_char.setdefault(true_speaker, []).append(ok)
        if not ok:
            margin = "ok" if margin_ok else "bad"
            details.append(
                f"miss: true={true_speaker} pred={pred} top={top} second={second} margin={margin}"
            )
    correct = sum(1 for v in per_char.values() if all(v) and v)
    return correct, len(per_char), details


def main(argv: list[str] | None = None) -> int:
    """CLI entry: mode dispatch, findings printed, exit 1 on v2 FAIL rows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["chapter", "volume", "blind"])
    parser.add_argument("project_dir", nargs="?", type=Path)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--volume", type=int)
    args = parser.parse_args(argv)
    if args.mode == "blind":
        correct, total, details = lint_blind()
        print(f"blind: {correct}/{total} 归属正确")
        for d in details:
            print(d)
        return 0 if correct >= _BLIND_MIN_CORRECT else 1
    if args.project_dir is None:
        parser.error("project_dir required")
    if args.mode == "chapter":
        rows = lint_chapter(args.project_dir, args.chapter or 1)
    else:
        rows = lint_volume(args.project_dir, args.volume or 1)
    for r in rows:
        print(r)
    fails = [r for r in rows if "FAIL 域" in r]
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
