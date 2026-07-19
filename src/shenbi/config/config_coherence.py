"""Genre-config update helper with mandatory rationale for safety-critical changes.

Spec: 2026-07-19 configuration-coherence-and-threshold-governance-design §3.4.

Every change to ``genre-config.json`` (or the in-state resonance floor) flows
through :func:`update_genre_config`, which:

  1. Blocks disabling a critical audit dimension unless *rationale* is at least
     50 characters explaining the alternative detection mechanism.
  2. Blocks lowering ``resonance_global_floor`` below the single-source-of-truth
     revision trigger (60).
  3. Appends a JSONL audit-trail entry to ``config-change-log.jsonl`` recording
     key / old / new / rationale / timestamp for every accepted change.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
    is_critical_audit_dimension,
)
from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

#: Minimum rationale length for disabling a critical audit dimension.
RATIONALE_MIN_CHARS = 50

#: Audit-trail filename (one JSON object per line).
AUDIT_TRAIL_NAME = "config-change-log.jsonl"

#: In-process lock for the audit-trail file (append safety).
_AUDIT_TRAIL_LOCK = threading.Lock()


class ConfigError(ValueError):
    """Raised when a config change violates a governance rule."""


def _load_config(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "genre-config.json"
    if not path.exists():
        return {}
    result: Any = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def _get_nested(config: dict[str, Any], dotted_key: str) -> Any:
    cur: Any = config
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _set_nested(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    cur = config
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _append_audit_trail(
    project_dir: Path,
    key: str,
    old: Any,
    new: Any,
    rationale: str,
) -> None:
    trail_path = project_dir / AUDIT_TRAIL_NAME
    entry = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "key": key,
        "old": old,
        "new": new,
        "rationale": rationale,
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    # Append-only: do not use safe_write (which replaces); open in 'a' mode.
    with _AUDIT_TRAIL_LOCK, trail_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def update_genre_config(project_dir: Path, changes: dict[str, Any], rationale: str) -> None:
    """Apply *changes* (dotted keys) to genre-config.json with governance.

    Raises :class:`ConfigError` if a critical audit dimension is being disabled
    without a >=50-char rationale, or if ``resonance_global_floor`` is being
    lowered below the revision trigger. Otherwise writes the updated config and
    appends one JSONL audit-trail entry per change.
    """
    config = _load_config(project_dir)

    for key, new_value in changes.items():
        old_value = _get_nested(config, key)

        # Rule 1: critical audit dimension being disabled.
        if key.startswith("auditDimensions.") and new_value is False:
            dim = key.split(".")[-1]
            if is_critical_audit_dimension(dim):
                if not rationale or len(rationale) < RATIONALE_MIN_CHARS:
                    raise ConfigError(
                        f"Cannot disable critical audit '{dim}' without "
                        f">= {RATIONALE_MIN_CHARS} char rationale explaining the "
                        f"alternative detection mechanism. detects: "
                        f"{AUDIT_SAFETY_MATRIX[dim]['detects']}"
                    )

        # Rule 2: floor cannot drop below the revision trigger.
        if key == "resonance_global_floor":
            if (
                isinstance(new_value, int)
                and new_value < DEFAULT_THRESHOLDS.resonance_revision_trigger
            ):
                raise ConfigError(
                    f"floor_too_low:resonance_global_floor={new_value} < revision trigger "
                    f"{DEFAULT_THRESHOLDS.resonance_revision_trigger}. Floors below the "
                    f"trigger allow degraded chapters to pass without revision."
                )

        _set_nested(config, key, new_value)
        _append_audit_trail(project_dir, key, old_value, new_value, rationale)
        log.info(
            "config_changed",
            key=key,
            old=old_value,
            new=new_value,
            rationale=rationale,
        )

    safe_write(project_dir / "genre-config.json", json.dumps(config, ensure_ascii=False, indent=2))
