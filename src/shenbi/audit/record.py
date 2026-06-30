"""审计结果记录 seam（spec 支柱四 Tier B）。

诚实分层：自包含 write-audit.jsonl 账本（round_dir 内，append-only）始终写入，
是 Tier B 审计结果的真理之源。Tier A trace.jsonl（TraceWriter）已落地时，GATE_FAIL /
AUDIT_PASS 事件经 try-import seam 追加到 trace；trace 不可用或签名失败时回退账本 +
structlog，绝不静默丢弃审计结果。
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.write_audit import AuditResult
from shenbi.logging import get_logger

log = get_logger(__name__)


def record_audit_outcome(round_dir: Path, skill: str, result: AuditResult) -> bool:
    """记录审计结果。返回 True=通过（无 violations/drift），False=无法 ship。

    violations 或 drift 非空 → 写 GATE_FAIL 记录并返回 False。
    """
    blocked = bool(result.violations) or bool(result.drift)
    record: dict[str, object] = {
        "skill": skill,
        "blocked": blocked,
        "violations": list(result.violations),
        "drift": list(result.drift),
        "checked_files": list(result.checked_files),
    }
    ledger = Path(round_dir) / "write-audit.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    # trace seam：Tier A（trace/）落地时生效；不在/签名失败时回退账本 + log
    try:
        from shenbi.trace.writer import TraceWriter

        TraceWriter(round_dir).append(
            actor="write-audit",
            actor_role="GATE",
            action="GATE_FAIL" if blocked else "AUDIT_PASS",
            target="write-audit",
            skill=skill,
            payload=record,
        )
    except (OSError, ValueError, TypeError):
        log.warning("audit_recorded_ledger_only", skill=skill, blocked=blocked, exc_info=True)
    if blocked:
        log.error(
            "write_audit_gate_fail",
            skill=skill,
            violations=list(result.violations),
            drift=list(result.drift),
        )
    return not blocked
