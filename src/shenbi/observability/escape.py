"""Escape-hatch drift counter (spec #81 §3).

The fields escape hatch (spec #9 R3 / F218) keeps generation alive when a
declared field is missing — full file + WARN. This module turns three
CONSECUTIVE misses of the same ``(path, fields)`` key into a checkable
condition: ``escape_hatch_drift_check`` returns the drifted keys and the
chapter loop (T7) escalates them — drift is not retry-healable.

Keying is ``(path, fields)`` — the drift unit O-1 actually exhibited.
``(project, path)`` alone would let interleaved reads from two skills with
different ``fields:`` declarations on the same file reset each other's
streaks (masking real drift) or pool unrelated misses into a false FAIL.

The counter is ALWAYS-ON (independent of ``SHENBI_ARCHIVE_DISPATCH`` —
zero blob cost, this is the O-3 fix itself). Writer = the shared prompt
builder (API/IDE faces both count); reader = the loop-phase check (pure
read). State file: ``observability/escape-hatch-state.json`` under the
``truth_io`` flock discipline (parallel audit waves share the counter).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.truth_io import truth_file_flock
from shenbi.safe_write import safe_write

log = get_logger(__name__)

_OBS = "observability"
_STATE_FILE = "escape-hatch-state.json"
ESCAPE_STREAK_THRESHOLD = 3


def _state_path(project_dir: Path) -> Path:
    return project_dir / _OBS / _STATE_FILE


def _entry_key(path: str, fields: list[str]) -> str:
    return f"{path}|{'|'.join(fields)}"


def update_escape_hatch_state(project_dir: Path, reads_manifest: list[dict[str, Any]]) -> None:
    """Record fields-mode read outcomes; a matched read resets its key's streak.

    Fail-safe: never raises into the prompt builder (the builder wraps the
    call, but the lock/IO layer guards as well). Only ``mode == "fields"``
    entries participate — full-mode reads have no fields contract to drift.
    """
    fields_entries = [e for e in reads_manifest if e.get("mode") == "fields" and e.get("fields")]
    if not fields_entries:
        return
    try:
        with truth_file_flock(_state_path(project_dir)):
            state = _read_state(project_dir)
            streaks: dict[str, Any] = state.setdefault("streaks", {})
            now = datetime.now(UTC).isoformat()
            mutated = False
            for entry in fields_entries:
                key = _entry_key(str(entry["path"]), list(entry["fields"]))
                if entry.get("matched_all"):
                    mutated = mutated or streaks.pop(key, None) is not None  # matched resets
                    continue
                current = streaks.setdefault(key, {"streak": 0, "first_ts": now, "last_ts": now})
                current["streak"] = int(current.get("streak", 0)) + 1
                current["last_ts"] = now
                mutated = True
            if mutated:  # all-matched steady state: skip the flock RMW write
                safe_write(_state_path(project_dir), json.dumps(state, ensure_ascii=False))
    except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch — counter must never break the builder, spec #81 §3)
        log.warning("escape_hatch_state_update_failed", exc_info=True)


def _read_state(project_dir: Path) -> dict[str, Any]:
    try:
        loaded: dict[str, Any] = json.loads(_state_path(project_dir).read_text(encoding="utf-8"))
        return loaded
    except (OSError, ValueError):
        return {}


def escape_hatch_drift_check(project_dir: Path) -> list[dict[str, Any]]:
    """Pure read: keys whose consecutive-miss streak reached ESCAPE_STREAK_THRESHOLD.

    Absent state file → ``[]`` (absent PASS — pre-feature projects and
    pre-feature history never retro-fail). Torn/partial JSON → ``[]`` + WARN
    (skip this round rather than fail on a half-written file) — the WARN is
    load-bearing: a silent ``[]`` would mask drift as absent-PASS.
    """
    path = _state_path(project_dir)
    if not path.exists():
        return []
    try:
        loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("escape_hatch_state_read_failed", path=str(path))
        return []
    if not isinstance(loaded, dict):
        log.warning("escape_hatch_state_malformed")
        return []
    streaks: Any = loaded.get("streaks", {})
    if not isinstance(streaks, dict):
        log.warning("escape_hatch_state_malformed")
        return []
    drifted: list[dict[str, Any]] = []
    for key, entry in streaks.items():
        try:
            streak = int(entry.get("streak", 0))
        except (AttributeError, TypeError, ValueError):
            continue
        if streak >= ESCAPE_STREAK_THRESHOLD:
            path, _, fields_joined = key.partition("|")
            drifted.append(
                {
                    "key": key,
                    "path": path,
                    "fields": fields_joined.split("|") if fields_joined else [],
                    "streak": streak,
                    "first_ts": entry.get("first_ts"),
                    "last_ts": entry.get("last_ts"),
                }
            )
    return drifted
