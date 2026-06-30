"""replay：逐行读 trace.jsonl，校验签名链。首条（JSON 解析失败 或 签名不匹配）
即视为撕裂/篡改边界，截断其后所有内容（判据 7 I6b torn-line 恢复）。
"""

from __future__ import annotations

from pathlib import Path

from shenbi.safe_write import safe_write
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign

_TRACE_NAME = "trace.jsonl"


def _verify(event: TraceEvent, prev_sig: str) -> bool:
    expected = sign(prev_sig, canonical_payload(event), event.schema_version)
    return expected == event.signature


def replay(round_dir: Path) -> list[TraceEvent]:
    path = Path(round_dir) / _TRACE_NAME
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    # keepends=True preserves the exact line separators (\n or \r\n), so
    # the cumulative char count is exact regardless of platform. This avoids
    # the off-by-N truncation that the old len(ln)+1 heuristic caused on
    # Windows (CRLF), which could cut a valid event mid-line.
    lines = raw.splitlines(keepends=True)
    out: list[TraceEvent] = []
    prev = GENESIS_PREV
    keep_chars = 0
    for ln in lines:
        content = ln.rstrip("\r\n")
        if not content.strip():
            keep_chars += len(ln)
            continue
        try:
            event = TraceEvent.model_validate_json(content)
        except Exception:
            break  # torn line: truncate
        if not _verify(event, prev):
            break  # signature gap: truncate
        out.append(event)
        prev = event.signature
        keep_chars += len(ln)
    if keep_chars < len(raw):
        safe_write(path, raw[:keep_chars])
    return out
