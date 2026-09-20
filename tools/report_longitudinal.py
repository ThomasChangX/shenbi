"""Longitudinal acceptance report for a pipeline project dir (spec #68).

Read-only verdict layer over already-persisted artifacts: novel.json targets,
truth/resonance_trend.md authoritative per-chapter scores, pipeline-state.json
chapter terminal health, audits/ raw reviewer reports, cost/token-ledger.jsonl.
Zero LLM, zero dispatch, zero src/shenbi/ mutation (pure-function imports only).
Exit codes: 0 pass / 1 fail / 2 data error (fail-closed — never pass silently
on missing data).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SCHEMA_ID = "shenbi-longitudinal-verdict-v1"
TREND_FILENAME = "resonance_trend.md"
STATE_FILENAME = "pipeline-state.json"
MIN_SEGMENTS = 3  # 前/中/后三段各至少 1 章（canary N=3 为退化下界）


class LongitudinalDataError(Exception):
    """Verdict-critical input missing/malformed → exit 2 (fail-closed)."""

    def __init__(self, reason: str) -> None:
        """Carry the machine-readable reason alongside the message."""
        super().__init__(reason)
        self.reason = reason


def parse_novel_targets(novel_json: object) -> tuple[int, int]:
    """Return (target_word_count, total_chapters); raise on missing/zero keys."""
    if not isinstance(novel_json, dict):
        raise LongitudinalDataError("novel.json: not a JSON object")
    twc = novel_json.get("target_word_count")
    tc = novel_json.get("total_chapters")
    if not isinstance(twc, int) or twc <= 0:
        raise LongitudinalDataError("novel.json: target_word_count missing/zero")
    if not isinstance(tc, int) or tc <= 0:
        raise LongitudinalDataError("novel.json: total_chapters missing/zero")
    return twc, tc


@dataclass(frozen=True)
class ResonanceRow:
    """One parsed trend row: overall score + human-override exclusion flag."""

    overall: float
    excluded: bool


def parse_resonance_trend(path: Path) -> dict[int, ResonanceRow]:
    """Parse truth/resonance_trend.md rows keyed by bare {N} chapter cell.

    Column binding is by header name (chapter/overall/human_overridden), never
    by fixed index — a future skill-side column reorder must fail loud, not
    silently misread a numeric neighbour. The contract header is written only
    by the skill; a file without it is a data error (parse_trend would
    silently return an empty series — forbidden).
    """
    if not path.exists():
        raise LongitudinalDataError(f"{path}: resonance_trend.md missing")
    lines = path.read_text(encoding="utf-8").splitlines()
    header_idx, col = -1, {}
    for idx, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if "chapter" in cells and "overall" in cells:
            header_idx = idx
            col = {name: i for i, name in enumerate(cells)}
            break
    if header_idx < 0:
        raise LongitudinalDataError(f"{path}: contract header row missing")
    rows: dict[int, ResonanceRow] = {}
    for line in lines[header_idx + 1 :]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells or all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
            continue  # markdown separator row
        try:
            ch = int(cells[col["chapter"]])
        except (ValueError, IndexError, KeyError):
            continue  # non-data row
        if ch in rows:
            raise LongitudinalDataError(f"{path}: duplicate chapter key {ch}")
        try:
            overall = float(cells[col["overall"]])
        except (ValueError, IndexError, KeyError):
            continue  # pending/- cell: chapter absent → fail-closed at verdict layer
        override_col = col.get("human_overridden")
        excluded = (
            cells[override_col].strip().lower() == "true"
            if override_col is not None and override_col < len(cells)
            else False
        )
        rows[ch] = ResonanceRow(overall=overall, excluded=excluded)
    if not rows:
        raise LongitudinalDataError(f"{path}: zero data rows")
    return rows


def segment_chapters(n_done: int) -> dict[str, list[int]]:
    """Enumerated partition: r=0→(f,f,f), r=1→(f,f,c), r=2→(f,c,c)."""
    if n_done < MIN_SEGMENTS:
        raise LongitudinalDataError(f"insufficient chapters: {n_done}")
    f, r = divmod(n_done, 3)
    c = f + (1 if r else 0)
    lengths = [(f, f, f), (f, f, c), (f, c, c), (c, c, c)][r]
    out: dict[str, list[int]] = {"front": [], "mid": [], "back": []}
    start = 1
    for name, ln in zip(("front", "mid", "back"), lengths, strict=True):
        out[name] = list(range(start, start + ln))
        start += ln
    return out
