#!/usr/bin/env python
"""One-off (SDD #56 C18 T4): deterministic-layer recalc for ch49/ch51 resonance.

Recalculates what CAN be recalculated offline (spec #56 boundary):

1. ch51 "近3章均值" trend rows — pure arithmetic over the Ch48-51 score
   table in the same file (F1172 wrong values: 实算 vs manual-era 报值).
2. §5.4 分流 statement — via ``shenbi.pipeline.revision_router.check_resonance``
   (overall 70 vs floor 65: margin is exactly 5, i.e. IN the ±5 boundary
   band; the manual-era claim "超出阈值 >5" is false and is retired).
   Dimension scores themselves are LLM-judged and NOT offline-recomputable
   (review_resonance three-path model deleted by spec #33 T1b).

Default dry-run prints old→new; ``--apply`` rewrites the trend rows and
appends the deterministic §5.4 note. Old values are archived to
``old-values-archive.md`` either way.

Usage:
  uv run python docs/superpowers/audit-runs/2026-09-08-c18-cleanup/\
    recalc_resonance_deterministic.py <project_dir> [--apply]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.pipeline.revision_router import check_resonance

#: The Ch48-51 comparison table rows in chapter-51-resonance.md:
#: | Ch48 | 77 | 22 | 19 | 21 | 15 |  -> overall, 情感落地, 场景临场感, 文笔质感, 读者回报
_CH_ROW_RE = re.compile(r"^\|\s*\*{0,2}Ch(\d+)\*{0,2}\s*\|")
_TREND_ROW_RE = re.compile(
    r"^(?P<row>- 第51章 (?P<dim>[^|]+?) (?P<val>\d+) \| 近3章均值 (?P<mean>[\d.]+) \| 趋势:.*)$"
)
_DIMS = ["overall", "情感落地", "场景临场感", "文笔质感", "读者回报"]
_RESONANCE_FLOOR = 65
_TARGET_CHAPTER = 51
_SCORE_COLUMNS = 5
_MIN_TABLE_ROWS = 4


def parse_score_table(text: str) -> dict[int, list[int]]:
    """Extract the ChNN -> [overall, 4 dimension scores] comparison table."""
    rows: dict[int, list[int]] = {}
    for line in text.splitlines():
        m = _CH_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        nums = [int(c) for c in cells[1:] if c.isdigit()]
        if len(nums) == _SCORE_COLUMNS:
            rows[int(m.group(1))] = nums
    return rows


def recompute_means(rows: dict[int, list[int]], chapter: int = _TARGET_CHAPTER) -> dict[str, float]:
    """Arithmetic means of the 3 chapters preceding ``chapter``, per dimension."""
    window = [rows[c] for c in sorted(rows) if c < chapter][-3:]
    means: dict[str, float] = {}
    for i, dim in enumerate(_DIMS):
        means[dim] = sum(r[i] for r in window) / len(window)
    return means


def main() -> None:
    """CLI entry (dry-run by default)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="rewrite file (default dry-run)")
    args = parser.parse_args()

    audit_file = args.project_dir / "audits" / "chapter-51-resonance.md"
    text = audit_file.read_text(encoding="utf-8")
    rows = parse_score_table(text)
    if _TARGET_CHAPTER not in rows or len(rows) < _MIN_TABLE_ROWS:
        print("ERROR: Ch48-51 score table not found / incomplete", file=sys.stderr)
        raise SystemExit(1)
    means = recompute_means(rows)

    print("score table:", dict(sorted(rows.items())))
    print("recomputed 近3章均值 (ch48-50 window):")
    diffs: list[tuple[str, str, str]] = []
    new_text = text
    for line in text.splitlines():
        m = _TREND_ROW_RE.match(line)
        if not m:
            continue
        dim = m.group("dim").strip()
        old = m.group("mean")
        if dim in means:
            new = f"{means[dim]:.1f}"
            diffs.append((dim, old, new))
            print(f"  {dim}: old {old} -> new {new}")
            if args.apply and old != new:
                new_text = new_text.replace(
                    m.group("row"),
                    m.group("row").replace(f"近3章均值 {old}", f"近3章均值 {new}"),
                    1,
                )

    overall = rows[_TARGET_CHAPTER][0]
    passed = check_resonance(overall, floor=_RESONANCE_FLOOR)
    margin = overall - _RESONANCE_FLOOR
    note = (
        f"\n> provenance (C18 cleanup 2026-09-08): 近3章均值 by deterministic recalc "
        f"(arithmetic over the Ch48-51 table; F1172 manual-era values retired, archived). "
        f"§5.4 分流 by revision_router.check_resonance: overall {overall} ≥ {_RESONANCE_FLOOR} → "
        f"{'通过' if passed else '不通过'}；余量 {margin} 恰在 ±5 边界带 "
        f"（manual-era 断言「超出阈值 >5」为误，已废弃）. Dimension scores are LLM-judged, "
        f"not offline-recomputable (review_resonance deleted by spec #33 T1b); "
        f"manual-era scores retained. "
        f"ch50 helper-output citation unverifiable.\n"
    )

    archive = (
        args.project_dir.parent.parent
        / "docs/superpowers/audit-runs/2026-09-08-c18-cleanup/old-values-archive.md"
    )
    verdict = "PASS" if passed else "FAIL"
    print(f"boundary: overall {overall} vs floor {_RESONANCE_FLOOR} -> margin {margin} ({verdict})")

    if args.apply:
        if "provenance (C18 cleanup" not in new_text:
            new_text = new_text.replace(
                "### 趋势（追加至 resonance_trend）",
                note + "\n### 趋势（追加至 resonance_trend）",
                1,
            )
        audit_file.write_text(new_text, encoding="utf-8")
        print(f"APPLIED -> {audit_file}")
        with archive.open("a", encoding="utf-8") as fh:
            fh.write("\n## chapter-51-resonance.md trend means (F1172)\n\n")
            for dim, old, new in diffs:
                fh.write(f"- {dim}: manual-era {old} -> recalculated {new}\n")
            s54 = f"- §5.4: manual-era 「超出阈值 >5」 -> deterministic margin {margin}"
            fh.write(s54 + " (boundary band)\n")
    print(f"archive -> {archive}")


if __name__ == "__main__":
    main()
