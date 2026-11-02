"""Dispatch archive layer (spec #81 §1).

Content-addressed blob store (``observability/blobs/<sha256>``) plus one
JSON record per dispatch (``observability/dispatches/``). The record carries
hash pointers; the blobs carry the bytes — byte-level reproduction of any
dispatch is a blob dereference, never a re-assembly from reads (the
assembled prompt embeds task instructions, banners, skeleton injection and
a per-dispatch timestamp line that no reads blob contains).

Fail-safe discipline: ``write_dispatch_archive`` swallows every failure
into WARN + ``archive-stats.json`` counters — an archive failure never
masks the dispatch outcome. The fail-safe BOUNDARY is
``write_dispatch_archive`` itself: ``put_blob`` and
``skill_contract_sha`` propagate their IO errors when called directly
(T4's frame construction wraps them accordingly).

Quota caliber: the breaker counts ``blobs/`` bytes only — dispatch
records are always written (档与哈希照写), so budgeting them is
meaningless; blobs are the dominant mass (spec §1 wording says the
``observability/`` directory; deviation recorded in the plan).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger
from shenbi.pipeline.truth_io import truth_file_flock
from shenbi.safe_write import safe_write

log = get_logger(__name__)

_OBS = "observability"
_BLOBS = "blobs"
_DISPATCHES = "dispatches"
_STATS = "archive-stats.json"
_DEFAULT_QUOTA_BYTES = 1024 * 1024 * 1024
# 抽样校准间隔：运行字节账每 N 次 put_blob 对目录实走一次 du 校准
_CALIBRATE_EVERY = 50

_STAT_KEYS = ("archive_write_failed", "archive_quota_skip", "archive_seq_collision")


def archive_enabled() -> bool:
    """Dispatch archiving default-on; ``SHENBI_ARCHIVE_DISPATCH=0`` opts out."""
    return os.environ.get("SHENBI_ARCHIVE_DISPATCH", "1") != "0"


def quota_bytes() -> int:
    raw = os.environ.get("SHENBI_ARCHIVE_QUOTA_BYTES", "")
    try:
        return int(raw) if raw else _DEFAULT_QUOTA_BYTES
    except ValueError:
        return _DEFAULT_QUOTA_BYTES


def sha256_of(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stats_path(project_dir: Path) -> Path:
    return project_dir / _OBS / _STATS


def _read_stats(project_dir: Path) -> dict[str, Any]:
    try:
        loaded: dict[str, Any] = json.loads(_stats_path(project_dir).read_text(encoding="utf-8"))
        return loaded
    except (OSError, ValueError):
        return {}


def _write_stats(project_dir: Path, stats: dict[str, Any]) -> None:
    _stats_path(project_dir).parent.mkdir(parents=True, exist_ok=True)
    safe_write(_stats_path(project_dir), json.dumps(stats, ensure_ascii=False))


def bump_stats(project_dir: Path, key: str) -> None:
    """Increment one archive-stats counter (best-effort, never raises)."""
    if key not in _STAT_KEYS:
        raise ValueError(f"unknown archive stat key: {key}")
    try:
        with truth_file_flock(_stats_path(project_dir)):
            stats = _read_stats(project_dir)
            for k in _STAT_KEYS:
                stats.setdefault(k, 0)
            stats[key] = int(stats[key]) + 1
            _write_stats(project_dir, stats)
    except Exception:
        log.warning("archive_stats_bump_failed", key=key, exc_info=True)


def _account_bytes(project_dir: Path, nbytes: int) -> None:
    try:
        with truth_file_flock(_stats_path(project_dir)):
            stats = _read_stats(project_dir)
            stats["_bytes"] = int(stats.get("_bytes", 0)) + nbytes
            stats["_puts"] = int(stats.get("_puts", 0)) + 1
            if stats["_puts"] % _CALIBRATE_EVERY == 0:
                stats["_bytes"] = _du_blobs(project_dir)
            _write_stats(project_dir, stats)
    except Exception:
        log.warning("archive_bytes_account_failed", exc_info=True)


def _du_blobs(project_dir: Path) -> int:
    blob_dir = project_dir / _OBS / _BLOBS
    if not blob_dir.exists():
        return 0
    total = 0
    for p in blob_dir.iterdir():
        if p.suffix == ".tmp":
            continue  # in-flight safe_write temp — becomes a blob via atomic replace
        try:
            total += p.stat().st_size
        except OSError:
            continue  # vanished between iterdir and stat (concurrent replace/unlink)
    return total


def _bytes_under_management(project_dir: Path) -> int:
    stats = _read_stats(project_dir)
    if "_bytes" in stats:
        return int(stats["_bytes"])
    return _du_blobs(project_dir)


def put_blob(project_dir: Path, content: str) -> str:
    """Write content into the content-addressed store; returns the digest.

    Quota breaker: when the store exceeds ``SHENBI_ARCHIVE_QUOTA_BYTES``,
    the CONTENT write is skipped (WARN + stat) but the digest is still
    returned — the archive record stays verifiable, reproducibility for
    that blob is lost (spec §1 rev2 honest-degradation semantics).
    """
    digest = sha256_of(content)
    blob = project_dir / _OBS / _BLOBS / digest.split(":", 1)[1]
    if blob.exists():
        return digest
    nbytes = len(content.encode("utf-8"))
    if _bytes_under_management(project_dir) + nbytes > quota_bytes():
        bump_stats(project_dir, "archive_quota_skip")
        log.warning("archive_quota_skip", dir=str(project_dir / _OBS))
        return digest
    blob.parent.mkdir(parents=True, exist_ok=True)
    safe_write(blob, content.encode("utf-8"))
    _account_bytes(project_dir, nbytes)
    return digest


def next_seq(project_dir: Path) -> int:
    """Atomic max+1 over existing archives, under the stats-file flock.

    Cross-restart continuation (advances from what's on disk, never
    resets). Gaps are tolerated and never renumbered — archive seq is a
    historical identifier, same discipline as the specs INDEX numbering.

    Locking note: ``truth_file_flock`` is per-fd; callers already holding
    the stats-file lock must use ``_max_seq`` instead (nested acquisition
    of the same lockfile deadlocks).
    """
    with truth_file_flock(_stats_path(project_dir)):
        return _max_seq(project_dir / _OBS / _DISPATCHES) + 1


def _max_seq(dispatch_dir: Path) -> int:
    if not dispatch_dir.exists():
        return 0
    seqs = [
        int(p.name.split("-", 1)[0])
        for p in dispatch_dir.glob("*.json")
        if p.name.split("-", 1)[0].isdigit()
    ]
    return max(seqs) if seqs else 0


def skill_contract_sha(skill: str) -> str | None:
    """sha256 of the skill's SKILL.md bytes — prompt provenance anchor.

    Content sha256, not the git blob SHA (equivalent drift-detection
    strength, uniform digest format across the archive) — spec deviation
    pre-registered in the plan.
    """
    from shenbi.contracts.loader import validate_skill_name  # lazy: cold path
    from shenbi.gates.shared import SKILLS

    try:
        path = SKILLS / validate_skill_name(skill) / "SKILL.md"
    except Exception:  # noqa: BLE001 (C13 allowlist: invalid skill names → None provenance, spec #81 §1)
        return None
    if not path.exists():
        return None
    return sha256_of(path.read_text(encoding="utf-8"))


@dataclass
class ArchiveFrame:
    """Everything known about a dispatch at archive time."""

    skill: str
    chapter: int | None
    attempt: int
    model: str
    system_prompt: str
    user_prompt: str
    reads_manifest: list[dict[str, Any]] = field(default_factory=list)
    raw_reads: dict[str, str] = field(default_factory=dict)
    skill_contract_sha256: str | None = None
    loop_id: int | None = None
    feedback_ref: str | None = None


def _archive_name(seq: int, frame: ArchiveFrame) -> str:
    ch = frame.chapter if frame.chapter is not None else 0  # genesis → ch000
    return f"{seq:05d}-{frame.skill}-ch{ch:03d}-a{frame.attempt}.json"


def write_dispatch_archive(
    project_dir: Path,
    frame: ArchiveFrame,
    *,
    finish_reason: str | None,
    response_text: str | None,
    usage: dict[str, Any] | None,
) -> Path | None:
    """Write one dispatch record; returns its path, or None when skipped.

    Skips entirely (no directory created) when ``SHENBI_ARCHIVE_DISPATCH=0``
    or on any failure (WARN + ``archive_write_failed`` stat — never raises,
    never blocks the dispatch; same fail-safe class as
    ``_persist_failed_write_output``).

    Locking: blobs are content-addressed and written BEFORE the critical
    section (order-independent); the stats-file flock guards only
    seq-allocation + collision check + record write — single-layer, no
    nested acquisition (bump_stats takes the same lock and therefore runs
    outside the critical section).
    """
    if not archive_enabled():
        return None
    try:
        system_blob = put_blob(project_dir, frame.system_prompt)
        user_blob = put_blob(project_dir, frame.user_prompt)
        response_blob = put_blob(project_dir, response_text) if response_text is not None else None
        reads_out: list[dict[str, Any]] = [
            {
                **entry,
                "blob": (
                    put_blob(project_dir, frame.raw_reads[entry["path"]])
                    if entry.get("path") in frame.raw_reads
                    else None
                ),
            }
            for entry in frame.reads_manifest
        ]
        collision = False
        path: Path | None = None
        with truth_file_flock(_stats_path(project_dir)):
            dispatch_dir = project_dir / _OBS / _DISPATCHES
            seq = _max_seq(dispatch_dir) + 1
            record: dict[str, Any] = {
                "seq": seq,
                "ts": datetime.now(UTC).isoformat(),
                "skill": frame.skill,
                "chapter": frame.chapter,
                "attempt": frame.attempt,
                "model": frame.model,
                "finish_reason": finish_reason,
                "skill_contract_sha256": frame.skill_contract_sha256,
                "system_prompt_blob": system_blob,
                "user_prompt_blob": user_blob,
                "response_blob": response_blob,
                "usage": usage,
                "loop_id": frame.loop_id,
                "feedback_ref": frame.feedback_ref,
                "reads": reads_out,
            }
            dispatch_dir.mkdir(parents=True, exist_ok=True)
            candidate = dispatch_dir / _archive_name(seq, frame)
            if candidate.exists():
                collision = True
            else:
                safe_write(candidate, json.dumps(record, ensure_ascii=False))
                path = candidate
        if collision:
            bump_stats(project_dir, "archive_seq_collision")
            log.warning("archive_seq_collision", skill=frame.skill)
            return None
        return path
    except Exception:
        bump_stats(project_dir, "archive_write_failed")
        log.warning("archive_write_failed", skill=frame.skill, exc_info=True)
        return None
