"""replay：逐行读 trace.jsonl，校验签名链。首条（JSON 解析失败 或 签名不匹配）
即视为撕裂/篡改边界，截断其后所有内容（判据 7 I6b torn-line 恢复）。
"""

from __future__ import annotations

from pathlib import Path

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
    lines = raw.splitlines()
    out: list[TraceEvent] = []
    prev = GENESIS_PREV
    keep_chars = 0
    for ln in lines:
        if not ln.strip():
            keep_chars += len(ln) + 1
            continue
        try:
            event = TraceEvent.model_validate_json(ln)
        except Exception:
            break  # 撕裂行：截断
        if not _verify(event, prev):
            break  # 签名断裂：截断
        out.append(event)
        prev = event.signature
        keep_chars += len(ln) + 1
    if keep_chars < len(raw):
        path.write_text(raw[:keep_chars], encoding="utf-8")
    return out
