"""Deterministic chapter-corpus expansion for C28 scale tests (G0.9).

Expands real fixture chapters to N files: the H1 line is rewritten per index
to `# 第{i}章 · {original title}(变体 {i})`; body bytes are preserved
verbatim. Sources are real skill outputs — no hand-written prose.
"""

from __future__ import annotations

import re
from pathlib import Path

_H1 = re.compile(r"^#\s+(.+?)$", re.MULTILINE)


def expand_chapter_corpus(src_dir: Path, dst: Path, n: int) -> None:
    """Copy real fixture chapters into ``dst/chapters`` with per-index H1 rewrite."""
    srcs = sorted(src_dir.glob("chapter-*.md"))
    if not srcs:
        raise ValueError(f"no chapter fixtures under {src_dir}")
    chapters = dst / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        text = srcs[i % len(srcs)].read_text(encoding="utf-8")
        m = _H1.search(text)
        new_title = f"# 第{i}章 · {m.group(1).strip()}（变体 {i}）" if m else f"# 第{i}章"
        out = _H1.sub(new_title, text, count=1)
        (chapters / f"chapter-{i}.md").write_text(out, encoding="utf-8")
