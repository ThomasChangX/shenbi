#!/usr/bin/env python3
"""Spec #105 T2/T3: replay G4.av.vocab (+dispatch_integrity) over a project's audits.

判据与 _is_audit_file 完全对齐(r2-I1): audits/ 域 + chapter-NN-<dim> 形 +
仅排除 .aggregate.md, 不排除 -resonance.md(生产 is_audit 块对 resonance
同样生效——shadow 闸门完整性)。回放只出报告, 不自动改写(用户裁定)。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.pipeline.llm_output_integrity import check_audit_severity_vocab

_CHAPTER_NUM_RE = re.compile(r"^chapter-(\d+)")


def _is_replay_target(stem: str) -> bool:
    """Return True when the stem matches the _is_audit_file criteria."""
    if stem.endswith(".aggregate"):
        return False
    m = _CHAPTER_NUM_RE.match(stem)
    if not m:
        return False
    return len(stem) > len(m.group(0))


def main() -> int:
    """Replay the vocab checker (and optional dispatch-integrity) over audits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="report path (default stdout)")
    parser.add_argument(
        "--dispatch-integrity",
        action="store_true",
        help="also replay check_audit_dispatch_integrity (spec #105 T5)",
    )
    args = parser.parse_args()

    di_check = None
    if args.dispatch_integrity:
        from shenbi.pipeline.llm_output_integrity import (  # noqa: PLC0415
            check_audit_dispatch_integrity,
        )

        di_check = check_audit_dispatch_integrity

    audits = args.project_dir / "audits"
    files = sorted(p for p in audits.glob("*.md") if _is_replay_target(p.stem))
    total_files = sorted(audits.glob("*.md")) if audits.is_dir() else []
    aggregates = [p for p in total_files if p.stem.endswith(".aggregate")]
    others = [p for p in total_files if p not in files and p not in aggregates]

    lines = [
        "# spec #105 severity-vocab replay report",
        "",
        f"- 分母（生产触达口径=_is_audit_file 同判据）: {len(files)} 章审计形（含 resonance）",
        f"- aggregate 差集: {len(aggregates)}",
        f"- 其他差集（escalation/arc/volume/stratum 等）: {len(others)}",
        "",
    ]
    vocab_hits = 0
    di_hits = 0
    for p in files:
        issues = check_audit_severity_vocab(p)
        if di_check is not None:
            issues = issues + di_check(p)
        for issue in issues:
            vocab_hits += 1 if issue.startswith("G4.av.vocab") else 0
            di_hits += 1 if issue.startswith("G4.av.dispatch_integrity") else 0
            lines.append(f"- {issue}")
    lines += [
        "",
        f"- G4.av.vocab 命中: {vocab_hits}",
    ]
    if di_check is not None:
        lines.append(f"- G4.av.dispatch_integrity 命中: {di_hits}")
    report = "\n".join(lines) + "\n"
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"report -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
