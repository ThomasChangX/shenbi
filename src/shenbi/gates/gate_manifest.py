import json
import threading
import structlog
from pathlib import Path
from typing import Any, cast

log = structlog.get_logger()
GATE_MANIFEST_FILENAME = "pipeline-manifest.json"

# Thread safety: the manifest read-modify-write is NOT atomic. Concurrent
# gate-marker writes (e.g. parallel audits) would race and clobber each
# other's updates. Guard the whole read-merge-write with a per-path lock.
# See Spec 12 §3.2 for the locking pattern.
_MANIFEST_LOCKS: dict[str, threading.Lock] = {}
_MANIFEST_LOCKS_GUARD = threading.Lock()


def _manifest_lock(manifest_dir: Path) -> threading.Lock:
    """Return (creating if needed) a per-path lock for manifest writes."""
    key = str(manifest_dir / GATE_MANIFEST_FILENAME)
    with _MANIFEST_LOCKS_GUARD:
        if key not in _MANIFEST_LOCKS:
            _MANIFEST_LOCKS[key] = threading.Lock()
        return _MANIFEST_LOCKS[key]


def _load_gate_manifest(manifest_dir: Path) -> dict[str, Any]:
    """Load or initialize the pipeline manifest."""
    manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
    if manifest_file.exists():
        try:
            return cast(dict[str, Any], json.loads(manifest_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            log.warning("manifest_corrupt_reinitializing")
    return {"version": "1.0", "gates": {}}


def _save_gate_manifest(manifest_dir: Path, data: dict[str, Any]) -> None:
    """Atomically save the manifest using safe_write."""
    from shenbi.safe_write import safe_write

    manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
    manifest_dir.mkdir(parents=True, exist_ok=True)
    safe_write(manifest_file, json.dumps(data, indent=2, ensure_ascii=False))


def record_gate_result(
    gate_manifest_dir: Path,
    phase: str,
    chapter: int,
    skill: str,
    gate: str,
    result: dict[str, Any],
) -> None:
    """Record a gate check result into the pipeline manifest.

    The read-merge-write sequence MUST be guarded by _manifest_lock() so
    concurrent gate-marker writes do not race.
    """
    with _manifest_lock(gate_manifest_dir):
        data = _load_gate_manifest(gate_manifest_dir)

        # Navigate: gates -> {phase} -> {chapter} -> {skill} -> {gate}
        phases = data.setdefault("gates", {})
        phase_data = phases.setdefault(phase, {})
        chapter_key = str(chapter)
        chapter_data = phase_data.setdefault(chapter_key, {})
        skill_data = chapter_data.setdefault(skill, {})

        # Record timestamped entry
        import datetime

        entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "gate": gate,
            "result": result,
        }

        # Store as list for historical tracking (not overwrite)
        if gate in skill_data:
            existing = skill_data[gate]
            if isinstance(existing, list):
                existing.append(entry)
            else:
                skill_data[gate] = [existing, entry]
        else:
            skill_data[gate] = entry

        _save_gate_manifest(gate_manifest_dir, data)
    log.debug("gate_result_recorded", phase=phase, chapter=chapter, skill=skill, gate=gate)


def get_gate_result(
    manifest_dir: Path,
    phase: str,
    chapter: int,
    skill: str,
    gate: str,
) -> dict[str, Any] | None:
    """Retrieve the most recent gate result. Returns None if not found."""
    data = _load_gate_manifest(manifest_dir)
    try:
        entry = data["gates"][phase][str(chapter)][skill][gate]
        if isinstance(entry, list):
            return cast(dict[str, Any], entry[-1]["result"])  # Most recent
        return cast(dict[str, Any], entry.get("result", entry)) if isinstance(entry, dict) else None
    except (KeyError, TypeError, IndexError):
        return None
