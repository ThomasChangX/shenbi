#!/usr/bin/env python3
"""Backfill craft-contract declaration lines into legacy chapter plans.

G4.cp (2026-10-23 craft batch, commits a4b0bbf5/558ca52e) hard-requires
three declaration lines that plans written before the batch lack:

- §1  ``emotion_tone: 悲/喜/怒/惧/平``
- §1  ``**payoff 拍**: [类型｜强度]``  (「无＋理由」 legal)
- §2  ``**留存锚**: [锚类型｜非锚章]``  (chapters 1-30 only; 31+ SKIP by gate)

Old memos are inert history — the declarations only bear weight for new
production (planning/drafting/review of chapters yet to be written) — so the
migration is a one-shot honest backfill marked 「历史补录」, not a re-dispatch.
Idempotent: fields already present are left untouched.

Usage: uv run python tools/plan_craft_backfill.py <project_dir> [--apply]

Default is dry-run (report only); ``--apply`` writes files in place.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EMOTION_RE = re.compile(r"emotion_tone\s*[:：]\s*(悲|喜|怒|惧|平)")
PAYOFF_RE = re.compile(r"\*{0,2}payoff\s*拍\*{0,2}\s*[:：]\s*\S")
ANCHOR_RE = re.compile(r"\*{0,2}留存锚\*{0,2}\s*[:：]\s*\S")
SECTION1_RE = re.compile(r"^## 1\.[^\n]*", re.MULTILINE)
SECTION2_RE = re.compile(r"^## 2\.[^\n]*", re.MULTILINE)
CHAPTER_NO_RE = re.compile(r"-(\d+)-plan")

TONE_LINE = "emotion_tone: 平（历史补录）"
PAYOFF_LINE = "**payoff 拍**: 无（历史补录）"
ANCHOR_LINE = "**留存锚**: 非锚章（历史补录）"

RETENTION_WINDOW = 30  # mirrors g4_chapter_planning's fixed window


def _chapter_no(fp: Path) -> int:
    m = CHAPTER_NO_RE.search(fp.name)
    return int(m.group(1)) if m else 0


def backfill_text(content: str, n: int) -> tuple[str, list[str]]:
    """Return (new_content, actions); actions empty when nothing to do."""
    s1_lines: list[str] = []
    s2_lines: list[str] = []
    actions: list[str] = []

    if not EMOTION_RE.search(content):
        s1_lines.append(TONE_LINE)
        actions.append("§1 emotion_tone")
    if not PAYOFF_RE.search(content):
        s1_lines.append(PAYOFF_LINE)
        actions.append("§1 payoff 拍")
    if 1 <= n <= RETENTION_WINDOW and not ANCHOR_RE.search(content):
        s2_lines.append(ANCHOR_LINE)
        actions.append(f"§2 留存锚 (N={n})")

    if not actions:
        return content, []

    new_content = content
    if s2_lines:
        m = SECTION2_RE.search(new_content)
        if not m:
            return content, ["SKIP: §2 heading not found (non-standard memo)"]
        block = "\n".join(s2_lines)
        new_content = new_content[: m.end()] + "\n\n" + block + new_content[m.end() :]
    if s1_lines:
        m = SECTION1_RE.search(new_content)
        if not m:
            return content, ["SKIP: §1 heading not found (non-standard memo)"]
        block = "\n".join(s1_lines)
        new_content = new_content[: m.end()] + "\n\n" + block + new_content[m.end() :]
    return new_content, actions


def main() -> int:
    """CLI entry: scan plans/, report (or apply) missing craft declarations."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path, help="pipeline project directory")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write files in place (default: dry-run report only)",
    )
    args = parser.parse_args()

    plans_dir = args.project_dir / "plans"
    if not plans_dir.is_dir():
        print(f"error: {plans_dir} not found — is this a pipeline project dir?")
        return 1

    scanned = patched = 0
    for fp in sorted(plans_dir.glob("chapter-*-plan.md")):
        scanned += 1
        content = fp.read_text(encoding="utf-8")
        new_content, actions = backfill_text(content, _chapter_no(fp))
        if not actions:
            continue
        if actions[0].startswith("SKIP"):
            print(f"SKIP {fp.name}: {actions[0]}")
            continue
        if args.apply:
            fp.write_text(new_content, encoding="utf-8")
            patched += 1
        tag = "PATCHED" if args.apply else "DRY-RUN"
        print(f"{tag} {fp.name}: {'; '.join(actions)}")

    mode = "applied" if args.apply else "dry-run (pass --apply to write)"
    print(f"\n{scanned} plans scanned, {patched} patched — {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
