"""Spec #77 style fingerprints: four deterministic WARN metrics.

Computed post-hoc per chapter at the audit boundary (chapter_loop hook) and
offline via CLI. WARN rows land in truth/audit_drift as
``- [style-warn:<name>] chN <detail>`` (structurally excluded from
count_drift_alerts). Consecutive-state = stateless windowed recompute over
the last N chapter files. F947: zero LLM dispatch.
"""

from __future__ import annotations

import argparse
import re
import sys
from itertools import pairwise
from pathlib import Path

from shenbi.cli_utils import echo

from shenbi.gates.shared import SIMILE_MARKERS, strip_narrative_body
from shenbi.text.cjk import find_quote_spans
from shenbi.text.voice_lexicon import OPENING_VERB_FAMILIES, SIMILE_DOMAINS

#: 实测定档（spec #77 校准条款；2026-10-26 旧九章对白域实测：
#: 25.6/23.9/5.0/13.8/20.5/22.5/1.7/18.4/26.0——P50≈20，取 20 保
#: ch1/2/5/6/9 高密度章真阳性、ch4/8 事件章不误报；12 初档过紧致 7/9 超）。
DEFAULTS: dict[str, float] = {
    "question_per_k": 20,
    "simile_share": 0.70,
    "simile_min_n": 5,
    "opener_run": 3,
    "opener_share": 0.50,
    "dialogue_min_chars": 300,
}
_WINDOW = 3
_OPENER_MIN_CHAPTERS = 6

_CHAPTER_FILE_RE = re.compile(r"chapter-(\d+)\.md")


def _thresholds(project_dir: Path) -> dict[str, float]:
    """genre-config market_params.styleFingerprint overrides onto DEFAULTS."""
    out = dict(DEFAULTS)
    gc = project_dir / "genre-config.json"
    if not gc.is_file():
        return out
    import json

    try:
        block = (
            json.loads(gc.read_text(encoding="utf-8"))
            .get("market_params", {})
            .get("styleFingerprint", {})
        )
    except ValueError:
        return out
    for k in DEFAULTS:
        if k in block:
            try:
                out[k] = float(block[k])
            except (TypeError, ValueError):
                continue  # 非数值（pydantic 已拦合法 config；裸读容错）
    return out


def question_density(body: str) -> tuple[float, int]:
    """对白域每千字问号数（含半角 ?）与对白域字符数。"""
    spans = find_quote_spans(body)
    dialogue = "\n".join(body[s:e] for s, e in spans)
    n_chars = len(dialogue.replace("\n", ""))
    if n_chars == 0:
        return (0.0, 0)
    marks = dialogue.count("？") + dialogue.count("?")
    return (marks * 1000 / n_chars, n_chars)


def simile_domains(body: str) -> dict[str, int]:
    """喻体域计数：marker→句内名词窗（至句读标点止，实测形态「像+名词短语+。」）。

    词素防误：像 前接 好/影/画/录/想 等复合词素不计（好像/影像类）；
    似的 为后缀形态——取其前方名词窗。
    """
    counts: dict[str, int] = dict.fromkeys(SIMILE_DOMAINS, 0)
    counts["其他"] = 0

    def _classify(vehicle: str) -> None:
        for domain, words in SIMILE_DOMAINS.items():
            if any(w in vehicle for w in words):
                counts[domain] += 1
                return
        if vehicle.strip():
            counts["其他"] += 1

    for marker in SIMILE_MARKERS:
        start = 0
        while True:
            idx = body.find(marker, start)
            if idx < 0:
                break
            start = idx + len(marker)
            if marker == "似的":
                back = body[max(0, idx - 12) : idx]
                cut = max(back.rfind(p) for p in "。！？，、；") + 1
                _classify(back[cut:])
                continue
            if marker == "像" and idx > 0 and body[idx - 1] in "好影画录想声照闪雕塑图偶虚绣蜡":
                continue  # 复合词素（好像/影像/画像…）非比喻
            vehicle = body[idx + len(marker) : idx + len(marker) + 12]
            for i, ch in enumerate(vehicle):
                if ch in "。！？，、；":
                    vehicle = vehicle[:i]
                    break
            _classify(vehicle)
    return counts


def classify_opener(body: str) -> str | None:
    """Strip 后首条非对白句的动词族归类。"""
    text = strip_narrative_body(body)
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith(("#", "<!--")):
            continue
        if find_quote_spans(line) and line[0] in "「『“":
            continue
        for family, verbs in OPENING_VERB_FAMILIES.items():
            if any(v in line[:24] for v in verbs):
                return family
        return None
    return None


def fingerprints(project_dir: Path, chapter: int) -> list[str]:
    """近 N 章窗口重算四指标；返回 WARN/INFO 行（不含行首 dash）。"""
    th = _thresholds(project_dir)
    chapters_dir = project_dir / "chapters"
    window = [
        (n, chapters_dir / f"chapter-{n}.md")
        for n in range(max(1, chapter - _WINDOW + 1), chapter + 1)
    ]
    window = [(n, p) for n, p in window if p.is_file() and _CHAPTER_FILE_RE.fullmatch(p.name)]
    rows: list[str] = []
    if not window:
        return rows
    bodies = {n: strip_narrative_body(p.read_text(encoding="utf-8")) for n, p in window}

    # 1 问号密度：连续两章超限（对白域 ≥300 字才计）
    over = [
        n
        for n, b in bodies.items()
        if (per_k := question_density(b))[1] >= th["dialogue_min_chars"]
        and per_k[0] > th["question_per_k"]
    ]
    # 连续=章号相邻（spec §1.1——窗口内非相邻超限对不算连续）
    _sorted_over = sorted(over)
    _adjacent = any(b - a == 1 for a, b in pairwise(_sorted_over))
    if _adjacent:
        _names = ",".join(f"ch{n}" for n in _sorted_over)
        _limit = th["question_per_k"]
        rows.append(
            f"[style-warn:问号密度] ch{chapter} 问答体退行：连续超限"
            f"（{_names}；>{_limit:.0f}/千字）"
        )

    # 2 喻体域集中度：窗口合并样本 ≥5 且单域 >70%
    merged: dict[str, int] = {}
    for b in bodies.values():
        for d, c in simile_domains(b).items():
            merged[d] = merged.get(d, 0) + c
    total = sum(c for d, c in merged.items() if d != "其他")
    if total >= th["simile_min_n"]:
        for d, c in merged.items():
            if d == "其他":
                continue
            if c / total > th["simile_share"]:
                rows.append(
                    f"[style-warn:喻体域] ch{chapter} 比喻同域：{d} {c}/{total}"
                    f"（>{th['simile_share']:.0%}）"
                )
                break
    # 其他域样本自身足量且占比过高 → INFO（词表覆盖不足，非同域问题）
    others = merged.get("其他", 0)
    if others >= th["simile_min_n"] and others / (total + others) > th["simile_share"]:
        rows.append(f"[style-info:喻体域] ch{chapter} 其他域占比过高——词表需扩")

    # 3 开头同构：窗口内同族连续 ≥N（含本章）
    families = [classify_opener(b) for _n, b in sorted(bodies.items())]
    last = families[-1]
    if last is not None:
        run = 0
        for f in reversed(families):
            if f == last:
                run += 1
            else:
                break
        if run >= th["opener_run"]:
            rows.append(f"[style-warn:开头同构] ch{chapter} 开头模板：{last} 连续{run}章")

    # 4 数数开头频次（派生统计，卷内窗 ≥6 章才计）
    all_ch = sorted(
        int(m.group(1))
        for f in chapters_dir.glob("chapter-*.md")
        if (m := _CHAPTER_FILE_RE.fullmatch(f.name))
    )
    if len(all_ch) >= _OPENER_MIN_CHAPTERS:
        count_openers = 0
        for n in all_ch:
            body_n = strip_narrative_body(
                (chapters_dir / f"chapter-{n}.md").read_text(encoding="utf-8")
            )
            if classify_opener(body_n) in ("清点", "数数"):
                count_openers += 1
        share = count_openers / len(all_ch)
        if share > th["opener_share"]:
            rows.append(
                f"[style-warn:数数开头] ch{chapter} 计数开篇占比 {count_openers}/{len(all_ch)}"
                f"={share:.0%}>{th['opener_share']:.0%}"
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    """CLI: print fingerprint rows for one chapter (F947-offline)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--chapter", type=int, required=True)
    args = parser.parse_args(argv)
    rows = fingerprints(args.project_dir, args.chapter)
    for r in rows:
        echo(f"- {r}")
    echo(f"style-fingerprint: ch{args.chapter} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
