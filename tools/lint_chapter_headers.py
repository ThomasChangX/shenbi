r"""Chapter-header form assertion for a novel project (spec #84 T0-14).

Per ``chapters/chapter-<N>.md`` (stem fullmatch ``chapter-\\d+`` — ``-pre-rev``
backups and ``-decisions.json`` sidecars are naturally excluded):

1. exactly one  ``^# 第[0-9]+章$``            (Arabic chapter-number line)
2. zero         ``^# 第[一二三四五六七八九十百千零〇]+章$``  (CJK-numeral line)
3. zero         English-contract header line   (``^# Chapter N:``)
4. exactly two  ``^# `` H1 lines in total      (number line + single title line)

Exit 0 = all green (``OK: ...``); exit 1 = one ``FAIL`` line per violating
file; exit 2 = the project dir / chapters dir is missing. Regexes are
single-sourced from ``shenbi.pipeline.dispatch_helper`` (plan M-1 — never
copy the patterns here or the tool and the write-path normalizer drift
apart).

CLI: ``uv run python tools/lint_chapter_headers.py <project_dir>``
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from shenbi.pipeline.dispatch_helper import (
    EN_CHAPTER_HEADER_LINE_RE,
    ZH_CHAPTER_LINE_CJK_RE,
    ZH_CHAPTER_LINE_RE,
)

_CHAPTER_STEM_RE = re.compile(r"chapter-\d+")
_H1_RE = re.compile(r"^# ", re.MULTILINE)
# Canonical two-line form: one chapter-number line + one title line.
_EXPECTED_H1_TOTAL = 2


def check_chapter_file(path: Path) -> list[str]:
    """Return the list of form violations in one chapter file (empty = clean)."""
    text = path.read_text(encoding="utf-8")
    arabic = len(ZH_CHAPTER_LINE_RE.findall(text))
    cjk = len(ZH_CHAPTER_LINE_CJK_RE.findall(text))
    english = len(EN_CHAPTER_HEADER_LINE_RE.findall(text))
    h1_total = len(_H1_RE.findall(text))
    issues: list[str] = []
    if arabic != 1:
        issues.append(f"阿码章号行 x{arabic} (须恰一行 `# 第N章`)")
    if cjk:
        issues.append(f"中文数字形章号行 x{cjk} (零容忍——否则双章号可蒙混)")
    if english:
        issues.append(f"英文契约头残留 x{english} (零容忍)")
    if h1_total != _EXPECTED_H1_TOTAL:
        issues.append(f"H1 总数 x{h1_total} (须恰两行: 章号行+章题行, 恰一行非章号 H1)")
    return issues


def main(argv: list[str]) -> int:
    """Run the assertion over <project_dir>/chapters; 0 clean / 1 violations / 2 usage."""
    if len(argv) != 1:
        sys.stdout.write("usage: lint_chapter_headers.py <project_dir>\n")
        return 2
    project = Path(argv[0])
    chapters = project / "chapters"
    if not chapters.is_dir():
        sys.stdout.write(f"FAIL: {chapters} not found\n")
        return 2
    files = sorted(p for p in chapters.iterdir() if _CHAPTER_STEM_RE.fullmatch(p.stem))
    if not files:
        sys.stdout.write(f"FAIL: no chapter-<N>.md under {chapters}\n")
        return 2
    failed = 0
    for path in files:
        for issue in check_chapter_file(path):
            sys.stdout.write(f"FAIL {path.name}: {issue}\n")
            failed += 1
    if failed:
        return 1
    sys.stdout.write(f"OK: chapter-header form clean ({len(files)} files)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
