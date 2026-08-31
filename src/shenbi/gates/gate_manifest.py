import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import structlog

from shenbi.exceptions import ShenbiError

log = structlog.get_logger()
GATE_MANIFEST_FILENAME = "pipeline-manifest.json"


class ManifestCorruptError(ShenbiError):
    """pipeline-manifest.json is unreadable/corrupt (fail-loud, spec #37 F416).

    The old behavior silently reinitialized to an empty manifest, erasing
    the audit history without any hard failure.
    """


# Thread safety: the manifest read-modify-write is NOT atomic. Concurrent
# gate-marker writes (e.g. parallel audits) would race and clobber each
# other's updates. Guard the whole read-merge-write with a per-path lock.
# Spec #37 F416: the lock must be CROSS-PROCESS — an in-process
# threading.Lock does not exclude the phase_runner/codex subprocess writers
# that share the same manifest directory.
_MANIFEST_LOCKS: dict[str, threading.Lock] = {}
_MANIFEST_LOCKS_GUARD = threading.Lock()
_MANIFEST_LOCKFILE_SUFFIX = ".lockfile"
_MANIFEST_LOCK_TIMEOUT = 30.0


@contextmanager
def _manifest_lock(manifest_dir: Path) -> Generator[None, None, None]:
    """Per-path cross-process lock (in-process registry + flock lockfile)."""
    lockfile = manifest_dir / (GATE_MANIFEST_FILENAME + _MANIFEST_LOCKFILE_SUFFIX)
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    key = str(lockfile)
    with _MANIFEST_LOCKS_GUARD:
        thread_lock = _MANIFEST_LOCKS.setdefault(key, threading.Lock())
    with thread_lock:
        fd: int | None = None
        if sys.platform != "win32":
            import fcntl

            fd = os.open(str(lockfile), os.O_CREAT | os.O_RDONLY)
            deadline = time.monotonic() + _MANIFEST_LOCK_TIMEOUT
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        os.close(fd)
                        raise TimeoutError(
                            f"manifest lock timed out after {_MANIFEST_LOCK_TIMEOUT}s on {lockfile}"
                        ) from None
                    time.sleep(0.05)
        try:
            yield
        finally:
            if fd is not None:
                os.close(fd)


def _load_gate_manifest(manifest_dir: Path) -> dict[str, Any]:
    """Load or initialize the pipeline manifest (fail-loud on corruption)."""
    manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
    if manifest_file.exists():
        try:
            return cast(dict[str, Any], json.loads(manifest_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            # F416 fail-loud: preserve a copy for forensics via safe_write
            # (the corrupt original stays in place — no uncoordinated move),
            # then surface a hard error instead of silently reinitializing.
            corrupt = manifest_dir / (GATE_MANIFEST_FILENAME + ".corrupt")
            try:
                from shenbi.safe_write import safe_write

                safe_write(corrupt, manifest_file.read_text(encoding="utf-8", errors="replace"))
                log.error("manifest_corrupt_preserved", corrupt_path=str(corrupt), error=str(e))
            except OSError:
                log.error("manifest_corrupt_preservation_failed", error=str(e))
            raise ManifestCorruptError(
                f"pipeline manifest corrupt at {manifest_file}: {e}; corrupt copy at {corrupt}"
            ) from e
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
