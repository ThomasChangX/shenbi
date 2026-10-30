#!/usr/bin/env python3
"""Volume-level node-table lint (spec #74 T4).

Checks one volume's KR node tables against the #74 rearrange acceptance:
density (no 2 consecutive blank chapters in the front window), total
(max node chapter == volume span end), ◆ slots (FIRST-OCCURRENCE deadlines:
智力爽◆ ≤5 / 变现◆ ≤8; zero rows of a slot = FAIL; 智识小胜◆ is a
classification label, deadline-exempt), 萤回触 chain (consecutive
touchpoint gaps ≤8), and node monotonicity per KR.

Read-only; exit 0 = all checks pass, exit 1 = findings printed.

Usage: lint_volume_nodes.py <project_dir> [--volume 1] [--window 12]
"""

from __future__ import annotations

import argparse
import re
import sys
from itertools import pairwise
from pathlib import Path

_CN = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]

_SLOT_DEADLINES = {"智力爽◆": 5, "变现◆": 8, "灰烬◆": 12}
_TOUCH_GAP_MAX = 8
_MIN_TOUCHES = 2


def parse_volume(volume_map: Path, volume: int) -> tuple[str, int, int, list[tuple[int, str, str]]]:
    """Return (title, span_start, span_end, [(chapter, role, detail)])."""
    text = volume_map.read_text(encoding="utf-8")
    cn = _CN[volume - 1]
    head = re.search(rf"## 第{cn}卷：[^\n]*?（第\s*(\d+)\s*[-–—]\s*(\d+)\s*章）", text)
    if not head:
        raise SystemExit("volume heading not found for requested volume")
    start, end = int(head.group(1)), int(head.group(2))
    body = text[head.end() :]
    nxt = re.search(r"\n## 第[一二三四五六七八九十]+卷：", body)
    if nxt:
        body = body[: nxt.start()]
    nodes: list[tuple[int, str, str]] = []
    for m in re.finditer(r"^[ \t]*\|\s*第(\d+)章\s*\|\s*([^|]+)\|\s*([^|]*)\|", body, re.MULTILINE):
        nodes.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    return cn, start, end, nodes


def _check_shape(chapters: list[int], end: int) -> list[str]:
    """Monotonic file order + max node == span end."""
    out = []
    for a, b in pairwise(chapters):
        if b <= a:
            out.append(f"monotonicity: 第{a}章 row followed by 第{b}章 (must ascend)")
    if chapters[-1] != end:
        out.append(f"total: max node 第{chapters[-1]}章 != span end 第{end}章")
    return out


def _check_density(chapters: list[int], start: int, end: int, window: int) -> list[str]:
    """No 2 consecutive blank chapters in the front window."""
    present = set(chapters)
    return [
        f"density: 第{c}-{c + 1}章 consecutive blanks in front-{window} window"
        for c in range(start, min(start + window, end + 1) - 1)
        if c not in present and c + 1 not in present
    ]


def _check_slots(nodes: list[tuple[int, str, str]], start: int) -> list[str]:
    """First-occurrence deadlines; a slot with zero rows is non-compliant."""
    out = []
    for slot, deadline in _SLOT_DEADLINES.items():
        hits = [c for c, _r, d in nodes if slot in d or slot in _r]
        if not hits:
            out.append(f"slot: {slot} no rows (deadline <= {deadline} unmet)")
        elif min(hits) > deadline + start - 1:
            out.append(
                f"slot: {slot} first at 第{min(hits)}章 > deadline 第{deadline + start - 1}章"
            )
    return out


def _check_touches(nodes: list[tuple[int, str, str]], start: int, end: int) -> list[str]:
    """Touchpoint chain checks — PER MARKER TYPE (spec #82 T6/r4②).

    萤回触 chain (回触 rows or 萤回触◆ markers) keeps the legacy shape;
    the 轮回触点◆ chain runs its own gap/span checks — a union of all ◆
    markers lets 萤回触 mask a broken 轮回 chain (vol-1's ch20-36 drought
    passed with union gaps ≤7).
    """
    out: list[str] = []
    for label, pred in (
        ("萤回触", lambda r, d: r == "回触" or "萤回触" in d),
        ("轮回触点◆", lambda r, d: "轮回触点◆" in d),
    ):
        out.extend(_touch_chain(nodes, start, end, label, pred))
    return out


def _touch_chain(
    nodes: list[tuple[int, str, str]],
    start: int,
    end: int,
    label: str,
    pred,
) -> list[str]:
    """One marker-type chain: pairwise gaps + span coverage."""
    touches = [c for c, r, d in nodes if pred(r, d)]
    if len(touches) < _MIN_TOUCHES:
        return [f"touch[{label}]: fewer than {_MIN_TOUCHES} touchpoint rows"]
    out = [
        f"touch[{label}]: gap 第{a}章->第{b}章 = {b - a} > {_TOUCH_GAP_MAX}"
        for a, b in pairwise(touches)
        if b - a > _TOUCH_GAP_MAX
    ]
    if touches[0] - start > _TOUCH_GAP_MAX:
        out.append(f"touch[{label}]: first touch 第{touches[0]}章 > {start}+{_TOUCH_GAP_MAX}")
    if end - touches[-1] > _TOUCH_GAP_MAX:
        out.append(
            f"touch[{label}]: last touch 第{touches[-1]}章 leaves "
            f"{end - touches[-1]} chapters uncovered to span end"
        )
    return out


_MAX_NO_GAIN_STREAK = 2  # 允许连续无获得承接章上限（spec #82 T3）


def _check_gains(
    vm_text: str, nodes: list[tuple[int, str, str]], start: int, end: int
) -> list[str]:
    """Spec #82 T3: KR gains column + victory budget + no-gain streak."""
    out: list[str] = []
    if "本章主角获得" not in vm_text:
        out.append("获得槽: KR 节点表缺「本章主角获得」列 [spec #82 T3——欲望/回报阶梯的规划源头]")
    if "胜利预算" not in vm_text:
        out.append(
            "胜利预算: 卷头缺「胜利预算：本卷 N 次实质获得（≥1 大），量级递增」行（spec #82 T3）"
        )
    if "主角自选目标" not in vm_text:
        out.append(
            "主角自选目标: 卷 Objective 缺主角自选目标子句"
            "（spec #82 T3——卷一教训：全部变更由外力文书驱动）"
        )
    if "本章主角获得" in vm_text:
        # 直扫表行取第 4 列（获得槽列）——parse_volume 的 nodes 元组只捕前三列；
        # 扫描域限本卷节（audit 修正：全文件扫会把无获得列的邻卷表算进来）
        rows = (
            m
            for m in re.finditer(
                r"^\s*\|\s*第(\d+)章\s*\|[^|]*\|[^|]*\|\s*([^|]*)\|", vm_text, re.M
            )
            if start <= int(m.group(1)) <= end  # 本卷节（lint() 已解析的 span）
        )
        streak = 0
        for m in rows:
            gains = m.group(2).strip()
            no_gain = ("无获得" in gains) or gains == ""
            streak = streak + 1 if no_gain else 0
            if streak > _MAX_NO_GAIN_STREAK:
                out.append(
                    f"连续无获得: 第{m.group(1)}章止连续 {streak} 章无获得"
                    f"（允许连续 ≤{_MAX_NO_GAIN_STREAK}——spec #82 T3）"
                )
                break
    return out


def lint(project_dir: Path, volume: int, window: int) -> list[str]:
    """Run all node-table checks for one volume; returns finding strings."""
    vm_path = project_dir / "outline" / "volume_map.md"
    cn, start, end, nodes = parse_volume(vm_path, volume)
    if not nodes:
        return [f"{cn}: no node rows found"]
    chapters = [c for c, _r, _d in nodes]
    full_text = vm_path.read_text(encoding="utf-8")
    # 本卷节文本（spec #82 T3 修正：获得槽/预算检查按卷判定——邻卷表列形态
    # 互异，全文件扫会把无该列的邻卷算成 streak）
    head_m = re.search(rf"## 第{cn}卷：[^\n]*?（第\s*\d+\s*[-–—]\s*\d+\s*章）", full_text)
    sect_text = ""
    if head_m:
        tail = full_text[head_m.end() :]
        nxt = re.search(r"\n## 第[一二三四五六七八九十]+卷：", tail)
        sect_text = tail[: nxt.start()] if nxt else tail
    return (
        _check_shape(chapters, end)
        + _check_density(chapters, start, end, window)
        + _check_slots(nodes, start)
        + _check_touches(nodes, start, end)
        + _check_gains(sect_text, nodes, start, end)
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: print findings, exit 1 when any."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--volume", type=int, default=1)
    parser.add_argument("--window", type=int, default=12)
    args = parser.parse_args(argv)
    findings = lint(args.project_dir, args.volume, args.window)
    for f in findings:
        print(f"FAIL [{f}]")
    print(f"nodes lint: volume={args.volume} findings={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
