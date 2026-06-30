# I6d: bootstrap LEGACY_MIGRATION from existing progress.json + file signature.
"""migrate_from_progress：从现有 progress.json 反推 LEGACY_MIGRATION 事件
（含文件签名快照），写入 trace.jsonl 作合法链首锚。判据 7 I6d 核心。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shenbi.trace.event import TraceEvent
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def migrate_from_progress(round_dir: Path) -> TraceEvent:
    events = replay(round_dir)
    if events:
        for e in events:
            if e.action == "LEGACY_MIGRATION":
                return e  # idempotent: already migrated
    progress_path = Path(round_dir) / "progress.json"
    raw = progress_path.read_text(encoding="utf-8") if progress_path.exists() else "{}"
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError:
        snapshot = {}
    w = TraceWriter(round_dir)
    return w.append(
        actor="system",
        actor_role="GATE",
        action="LEGACY_MIGRATION",
        target="progress.json",
        payload={
            "progress_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "progress_snapshot": {
                "tier": snapshot.get("tier"),
                "completed_skill_names": snapshot.get("completed_skill_names", []),
            },
        },
    )
