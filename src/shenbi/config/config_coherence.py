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
import math
import threading
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
        nxt: Any = cur.get(part)
        if nxt is None:
            nxt = {}
            cur[part] = nxt
        elif not isinstance(nxt, dict):
            raise ConfigError(
                f"cannot_set:{dotted_key} -- intermediate segment '{part}' is not "
                f"an object; refusing scalar-clobbering write"
            )
        cur = nxt
    cur[parts[-1]] = value


def _append_audit_trail(
    project_dir: Path,
    key: str,
    old: Any,
    new: Any,
    rationale: str,
) -> None:
    from shenbi.append_helper import append_jsonl

    entry = {
        "key": key,
        "old": old,
        "new": new,
        "rationale": rationale,
    }
    # Append-only with fsync + timestamp + directory lock (spec #37 F534);
    # the old bare open("a") under a mere threading.Lock had none.
    with _AUDIT_TRAIL_LOCK:
        append_jsonl(project_dir / AUDIT_TRAIL_NAME, entry)


_AUDIT_DIM_ROOTS = frozenset({"auditDimensions", "audit_dimensions"})


def _touches_audit_dimensions(key: str) -> bool:
    return key.split(".", maxsplit=1)[0] in _AUDIT_DIM_ROOTS


def _validate_changes(
    old_config: dict[str, Any],
    staged: dict[str, Any],
    changes: dict[str, Any],
    rationale: str,
) -> None:
    """Validate ALL changes against the staged (all-applied) config. Raises ConfigError.

    Rule 1 is delta-based: a critical dimension counts as a disable attempt
    when it was enabled (or absent = enabled, criticality-split semantics) in
    the old config and is absent-or-not-True in the staged config. A critical
    dim already disabled before this batch does not re-trigger (no coupling of
    unrelated changes to historical state).

    Note: when a snake_case key coexists with a camelCase key, the camel-wins
    merge makes the snake_case write a silent no-op (validation evaluates the
    camel value) -- declared merge semantics, no extra warning is emitted.
    """
    if any(_touches_audit_dimensions(k) for k in changes):
        old_dims, _old_bad = resolve_audit_dimensions(old_config)
        merged, malformed = resolve_audit_dimensions(staged)
        if malformed:
            raise ConfigError(
                "auditDimensions must be an object mapping dimension -> bool, "
                "got a scalar/list value; refusing to apply."
            )
        for dim in AUDIT_SAFETY_MATRIX:
            if not is_critical_audit_dimension(dim):
                continue
            was_enabled = old_dims.get(dim, True) is True
            # Disable attempt = explicit falsy value, or explicit removal of a
            # previously-declared key (whole-key overwrite omission). Absence in
            # both old and staged is no change (criticality-split: missing =
            # enabled, governed only on the whole-file diff path).
            explicit_falsy = dim in merged and merged[dim] is not True
            explicit_removal = dim in old_dims and dim not in merged
            if (
                was_enabled
                and (explicit_falsy or explicit_removal)
                and len(rationale.strip()) < RATIONALE_MIN_CHARS
            ):
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
            if math.isnan(new_value) or math.isinf(new_value):
                raise ConfigError(f"floor_not_finite:resonance_global_floor={new_value!r}")
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
    rationale = str(rationale or "")  # None/non-str safe (audit-T1 M)

    # Phase 1: stage all changes on a copy and validate — no side effects yet.
    staged = copy.deepcopy(config)
    for key, new_value in changes.items():
        _set_nested(staged, key, new_value)
    _validate_changes(config, staged, changes, rationale)

    # Phase 2: commit — write config, then append trail entries. A trail
    # failure mid-batch rolls the config back to the pre-batch parsed content
    # (covers both missing and existing files) and appends a compensating
    # ROLLBACK trail entry, then re-raises (spec #37 F605: config and audit
    # trail must not diverge in either direction).
    entries = [(key, _get_nested(config, key), value) for key, value in changes.items()]
    config_path = project_dir / "genre-config.json"
    rollback_content = json.dumps(config, ensure_ascii=False, indent=2)
    safe_write(config_path, json.dumps(staged, ensure_ascii=False, indent=2))
    try:
        for key, old_value, new_value in entries:
            _append_audit_trail(project_dir, key, old_value, new_value, rationale)
            log.info(
                "config_changed",
                key=key,
                old=old_value,
                new=new_value,
                rationale=rationale,
            )
    except BaseException:
        safe_write(config_path, rollback_content)
        try:
            from shenbi.append_helper import append_jsonl

            append_jsonl(
                project_dir / AUDIT_TRAIL_NAME,
                {
                    "key": "batch",
                    "old": "committed",
                    "new": "rolled_back",
                    "rationale": f"trail append failed mid-batch; batch reverted: {rationale}",
                },
            )
        except OSError:
            log.error("config_rollback_trail_entry_failed", exc_info=True)
        raise


_TRAIL_RATIONALE_MAX_CHARS = 500


def govern_genre_config_change(
    project_dir: Path,
    old_config: dict[str, Any],
    new_config: dict[str, Any],
    rationale: str,
) -> None:
    """Govern a whole-file genre-config overwrite (production update path).

    Compares resolved audit dimensions old vs new; any critical dimension
    disabled or deleted requires a >=RATIONALE_MIN_CHARS rationale (F635/F643).
    Appends one trail entry per governed dimension change on success. Raises
    ConfigError with no side effects on violation (two-phase, F614).
    """
    rationale = str(rationale or "")
    if len(rationale) > _TRAIL_RATIONALE_MAX_CHARS:
        raise ConfigError(
            f"rationale exceeds {_TRAIL_RATIONALE_MAX_CHARS} chars; produce one "
            f"merged 50-100 char rationale instead"
        )
    old_dims, _old_bad = resolve_audit_dimensions(old_config)
    new_dims, new_bad = resolve_audit_dimensions(new_config)
    if new_bad:
        raise ConfigError(
            "auditDimensions must be an object mapping dimension -> bool; "
            "refusing ungoverned overwrite."
        )
    changed: list[tuple[str, Any, Any]] = []
    for dim in AUDIT_SAFETY_MATRIX:
        if not is_critical_audit_dimension(dim):
            continue
        # Diff semantics (spec R2): a deleted critical key counts as a disable
        # attempt. Old side uses the runtime rule (missing = enabled); new side
        # treats missing as disabled. This is a deliberate semantics split:
        # the diff looks at explicit removal, the runtime at final protection.
        new_v = new_dims.get(dim, False)
        old_v = old_dims.get(dim, True)
        if new_v is not True and old_v is True:
            if len(rationale.strip()) < RATIONALE_MIN_CHARS:
                raise ConfigError(
                    f"Cannot disable critical audit '{dim}' without "
                    f">= {RATIONALE_MIN_CHARS} char rationale explaining the "
                    f"alternative detection mechanism."
                )
            changed.append((f"auditDimensions.{dim}", old_v, new_v))
    for key, old_v, new_v in changed:
        _append_audit_trail(project_dir, key, old_v, new_v, rationale)


def rollback_genre_config(project_dir: Path, snapshot: str | None) -> None:
    """Restore the pre-dispatch config; remove stale sidecar/bak artifacts (spec 13 R4c)."""
    gc_path = project_dir / "genre-config.json"
    if snapshot is not None:
        safe_write(gc_path, snapshot)
    else:
        # No pre-existing config: a rejected new config must not stay on disk either.
        gc_path.unlink(missing_ok=True)
    for stale in project_dir.glob("genre-config-decisions.json"):
        stale.unlink()
    baks = [
        *project_dir.glob("genre-config.json.bak.*"),
        *project_dir.glob("genre-config.json.bak"),
    ]
    for bak in baks:
        bak.unlink()
