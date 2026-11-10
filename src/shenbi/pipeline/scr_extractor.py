"""Recent location terms for the world-freshness check (spec #86 T1).

The old 17-field StructuredChapterRepresentation had one live consumer:
world freshness reading world_refs filtered to category=="location". The
per-chapter disk cache existed only to serve the full extraction; with the
single-function face there is nothing worth caching.
"""

from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.shared import META_BLOCK_RE

_LOCATION_RE = re.compile(r"(山|河|城|镇|村|谷|林|海|原)")


def recent_location_terms(project_dir: Path, chapter: int, lookback: int = 10) -> set[str]:
    """Location terms referenced in chapters ``[max(1, chapter-lookback), chapter)``.

    Mirrors the pre-#86 consumption shape verbatim: window excludes the
    current chapter; a missing/incomplete chapter is tolerated (its absence
    contributes nothing) — the old loop's per-chapter ``except: continue``.
    """
    terms: set[str] = set()
    for ch in range(max(1, chapter - lookback), chapter):
        path = project_dir / "chapters" / f"chapter-{ch}.md"
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch — per-chapter tolerance pinned by spec #86 T1)
            continue
        prose = META_BLOCK_RE.sub("", text)
        prose = re.sub(r"^(#\s+.+?\n\s*)+", "", prose)
        terms.update(_LOCATION_RE.findall(prose))
    return terms
