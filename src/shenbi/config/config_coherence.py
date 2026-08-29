"""Genre-config governance: rationale enforcement + audit trail.

Spec: 2026-07-19 configuration-coherence-and-threshold-governance-design §3.4
(revised by 2026-08-14-config-governance-design, SDD #13).

Two governance entry points:

* :func:`update_genre_config` — dotted-key library API. Validates all changes
  against the staged (all-applied) config before any side effect (two-phase,
  F614), blocking critical-audit-dimension disabling without a >=50-char
  rationale and non-numeric / too-low resonance floors.
* :func:`govern_genre_config_change` — whole-file diff governance for the
  production update path (the shenbi-genre-config TriggerStep; see
  pipeline/triggers.py).
"""

from __future__ import annotations

import copy
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.config.thresholds import (
    AUDIT_SAFETY_MATRIX,
    DEFAULT_THRESHOLDS,
    is_critical_audit_dimension,
    resolve_audit_dimensions,
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


_AUDIT_DIM_ROOTS = frozenset({"auditDimensions", "audit_dimensions"})


def _touches_audit_dimensions(key: str) -> bool:
    return key.split(".", maxsplit=1)[0] in _AUDIT_DIM_ROOTS


def _validate_changes(
    staged: dict[str, Any],
    changes: dict[str, Any],
    rationale: str,
) -> None:
    """Validate ALL changes against the staged (all-applied) config. Raises ConfigError.

    Note: when a snake_case key coexists with a camelCase key, the camel-wins
    merge makes the snake_case write a silent no-op (validation evaluates the
    camel value) -- declared merge semantics, no extra warning is emitted.
    """
    if any(_touches_audit_dimensions(k) for k in changes):
        merged, malformed = resolve_audit_dimensions(staged)
        if malformed:
            raise ConfigError(
                "auditDimensions must be an object mapping dimension -> bool, "
                "got a scalar/list value; refusing to apply."
            )
        for dim in AUDIT_SAFETY_MATRIX:
            if not is_critical_audit_dimension(dim):
                continue
            if dim in merged and merged[dim] is not True and len(rationale) < RATIONALE_MIN_CHARS:
                raise ConfigError(
                    f"Cannot disable critical audit '{dim}' without "
                    f">= {RATIONALE_MIN_CHARS} char rationale explaining the "
                    f"alternative detection mechanism. detects: "
                    f"{AUDIT_SAFETY_MATRIX[dim]['detects']}"
                )
    for key, new_value in changes.items():
        if key == "resonance_global_floor":
            if isinstance(new_value, bool) or not isinstance(new_value, (int, float)):
                raise ConfigError(
                    f"floor_not_numeric:resonance_global_floor={new_value!r} "
                    f"(expected int/float, got {type(new_value).__name__})"
                )
            if new_value < DEFAULT_THRESHOLDS.resonance_revision_trigger:
                raise ConfigError(
                    f"floor_too_low:resonance_global_floor={new_value} < revision trigger "
                    f"{DEFAULT_THRESHOLDS.resonance_revision_trigger}. Floors below the "
                    f"trigger allow degraded chapters to pass without revision."
                )


def update_genre_config(project_dir: Path, changes: dict[str, Any], rationale: str) -> None:
    """Apply *changes* (dotted keys) to genre-config.json with governance.

    Two-phase (F614): all changes are staged on a copy and validated first;
    only then are the config written and audit-trail entries appended — a
    mid-batch ConfigError leaves neither config change nor trail entry.

    Raises :class:`ConfigError` if a critical audit dimension is being disabled
    (any key shape: whole-key overwrite, dotted camelCase or snake_case, falsy
    value) without a >=50-char rationale, or if ``resonance_global_floor`` is
    non-numeric or below the revision trigger.
    """
    config = _load_config(project_dir)

    # Phase 1: stage all changes on a copy and validate — no side effects yet.
    staged = copy.deepcopy(config)
    for key, new_value in changes.items():
        _set_nested(staged, key, new_value)
    _validate_changes(staged, changes, rationale)

    # Phase 2: commit — write config, then append trail entries.
    entries = [(key, _get_nested(config, key), value) for key, value in changes.items()]
    safe_write(
        project_dir / "genre-config.json",
        json.dumps(staged, ensure_ascii=False, indent=2),
    )
    for key, old_value, new_value in entries:
        _append_audit_trail(project_dir, key, old_value, new_value, rationale)
        log.info(
            "config_changed",
            key=key,
            old=old_value,
            new=new_value,
            rationale=rationale,
        )
