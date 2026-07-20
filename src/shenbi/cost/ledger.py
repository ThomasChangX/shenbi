"""Append-only JSONL token usage ledger (spec §3.2).

Each API dispatch appends one self-contained record. Aggregation reads all
lines; a partial/corrupt line is skipped, never crashing the report.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from collections.abc import Iterator

from shenbi.cost.pricing import estimate_cost, resolve_model
from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class TokenUsageRecord:
    timestamp: str
    skill: str
    chapter: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class TokenLedger:
    """Persistent append-only token usage ledger."""

    def __init__(self, project_dir: Path | str) -> None:
        """Create a ledger rooted at project_dir/cost/token-ledger.jsonl."""
        self.project_dir = Path(project_dir)
        self.ledger_path = self.project_dir / "cost" / "token-ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def record(
        self,
        skill: str,
        chapter: int,
        usage: dict[str, Any],
        model: str | None = None,
    ) -> TokenUsageRecord:
        """Append a usage record. Returns the record written."""
        resolved = resolve_model(model)
        rec = TokenUsageRecord(
            timestamp=datetime.now(UTC).isoformat(),
            skill=skill,
            chapter=chapter,
            model=resolved,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            estimated_cost_usd=estimate_cost(usage, resolved),
        )
        with self._write_lock, self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def iter_records(self) -> Iterator[TokenUsageRecord]:
        """Yield records, skipping blank/corrupt lines."""
        if not self.ledger_path.exists():
            return
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                log.warning("ledger_skipped_corrupt_line", line_preview=line[:80])
                continue
            try:
                yield TokenUsageRecord(**data)
            except TypeError:
                log.warning("ledger_skipped_malformed_record", line_preview=line[:80])
                continue

    def summarize(self) -> dict[str, Any]:
        """Aggregate token usage by skill, by chapter, and total."""
        by_skill: dict[str, dict[str, int | float]] = {}
        by_chapter: dict[str, dict[str, int | float]] = {}
        totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "estimated_cost_usd": 0.0,
        }

        def _bump(
            bucket: dict[str, dict[str, int | float]], key: str, rec: TokenUsageRecord
        ) -> None:
            entry = bucket.setdefault(
                key,
                {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "calls": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            entry["prompt_tokens"] += rec.prompt_tokens
            entry["completion_tokens"] += rec.completion_tokens
            entry["total_tokens"] += rec.total_tokens
            entry["calls"] += 1
            entry["estimated_cost_usd"] += rec.estimated_cost_usd

        for rec in self.iter_records():
            _bump(by_skill, rec.skill, rec)
            _bump(by_chapter, str(rec.chapter), rec)
            totals["prompt_tokens"] += rec.prompt_tokens
            totals["completion_tokens"] += rec.completion_tokens
            totals["total_tokens"] += rec.total_tokens
            totals["calls"] += 1
            totals["estimated_cost_usd"] += rec.estimated_cost_usd

        return {"total": totals, "by_skill": by_skill, "by_chapter": by_chapter}
