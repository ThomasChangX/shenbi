"""One-off: insert contract chapter headers into existing novel-output chapters.

z11 SDD #20 R1c (F1301). Deterministic, no LLM. Kept under tools/oneoff/ as
immutable history — never wire into CI/just.
"""

import sys
from pathlib import Path

from shenbi.pipeline.dispatch_helper import ensure_chapter_header

ROOT = Path("novel-output/xinghuo-ranqiong/chapters")


def main() -> int:
    """Insert missing contract headers into all 56 chapters; idempotent."""
    changed = 0
    for f in sorted(ROOT.glob("chapter-*.md")):
        if not f.stem.removeprefix("chapter-").isdigit():
            continue
        num = int(f.stem.removeprefix("chapter-"))
        text = f.read_text(encoding="utf-8")
        new = ensure_chapter_header(text, num)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
            print(f"inserted: {f.name}")
    print(f"total changed: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
