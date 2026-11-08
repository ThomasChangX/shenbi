#!/usr/bin/env python3
"""Spec #99 (1)(5) existence lint: anti-drift guard for increment teaching faces.

Three-file existence guard (green = all present; exit 1 with file:line hints
on any miss). Tamper-red cases live in
tests/unit/tools/test_lint_increment_teaching.py.

Faces:
  1. skills/shenbi-state-settling/SKILL.md -- iron-law 0 own-block exclusion
     clause + quote dual-line example (spec #99 item 1).
  2. src/shenbi/pipeline/chapter_loop.py -- counter-regression example uses the
     no-space canonical form (## 第2章状态增量 -- drift source sealed).
  3. src/shenbi/pipeline/dispatch_helper.py -- #23 injection dual-chapter
     wording + own-block replaceability (spec #99 item 5).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FACES: list[tuple[str, str, list[str]]] = [
    (
        "SKILL 铁律 0 排除条款+引语正例",
        "skills/shenbi-state-settling/SKILL.md",
        ["排除条款", "keyed-upsert 可整体替换单元", "自陈补全（第N章原句）"],
    ),
    (
        "chapter_loop 示例无空格规范形",
        "src/shenbi/pipeline/chapter_loop.py",
        ["## 第2章状态增量"],
    ),
    (
        "#23 注入双章口径+own-block 可替换",
        "src/shenbi/pipeline/dispatch_helper.py",
        ["block per chapter", "twin N+1", "OTHER chapter", "keyed-upsert replaceable unit"],
    ),
]

# Teaching-face seal: spaced heading forms must not return to any teaching face
# (chapter_loop's counter-regression example taught the spaced form -- the 束7
# H4 drift source; SKILL must stay on the no-space canonical form too).
# Regex matches ANY ``## 第 N 章状态增量`` with whitespace around the numeral.
_SPACED_HEADING_RE = re.compile(
    r"##\s*第\s+\d+\s*章状态增量|##\s*第\s*\d+\s+章状态增量|##\s*第\s*\d+\s*章\s+状态增量"
)
_FORBIDDEN_FILES: list[tuple[str, str]] = [
    ("chapter_loop", "src/shenbi/pipeline/chapter_loop.py"),
    ("SKILL", "skills/shenbi-state-settling/SKILL.md"),
]


def main() -> int:
    """Run the three-face existence guard; 0 = all present, 1 = drift."""
    failures: list[str] = []
    for label, rel, needles in FACES:
        path = REPO / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not path.is_file():
            failures.append(f"{label}: 文件缺失 {rel}")
            continue
        for needle in needles:
            if needle not in text:
                line = next(
                    (i + 1 for i, row in enumerate(text.splitlines()) if needle[:6] in row),
                    1,
                )
                failures.append(f"{label}: {rel}:{line} 缺 `{needle}`")
    for label, rel in _FORBIDDEN_FILES:
        path = REPO / rel
        if not path.is_file():
            continue
        for i, row in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if _SPACED_HEADING_RE.search(row):
                failures.append(f"{label} 空格形示例回流: {rel}:{i + 1} `{row.strip()[:40]}`")
    if failures:
        for f in failures:
            print(f"ERROR: {f}", file=sys.stderr)
        return 1
    print("increment-teaching lint: OK (3 faces, spec #99 ①⑤)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
