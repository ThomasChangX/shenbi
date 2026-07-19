import hashlib
import json
from pathlib import Path
from typing import Any

import structlog

from shenbi.safe_write import safe_write

log = structlog.get_logger()

# Ring-buffer size: store FULL content for the last N=3 chapter snapshots so
# revision-rollback can restore the PREVIOUS chapter content after a revision
# overwrite. Older snapshots are hash-only.
RING_BUFFER_N = 3

# Files that need full content backup (mutable truth files)
TRUTH_FILES = {
    "current_state.md",
    "character_matrix.md",
    "current_focus.md",
    "resonance_trend.md",
    "audit_drift.md",
    "emotional_arcs.md",
    "chapter_summaries.md",
    "pending_hooks.md",
    "world_rules.md",
}

# Files only tracked by hash (immutable once written)
HASH_ONLY_DIRS = {"chapters", "audits", "plans"}


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _latest_chapter_number(project_dir: Path) -> int:
    """Return the highest chapter number seen among existing chapter files (0 if none).

    Scans ``project_dir / "chapters"`` for files matching ``chapter-NNN.md``
    to determine the latest chapter that exists in the project. This is used
    to compute the ring-buffer window: only the most recent RING_BUFFER_N
    chapters get full-content snapshots; older ones are hash-only.
    """
    chapters_dir = project_dir / "chapters"
    if not chapters_dir.exists():
        return 0
    best = 0
    for f in chapters_dir.iterdir():
        if f.is_file() and f.name.startswith("chapter-") and f.name.endswith(".md"):
            try:
                # Extract number from "chapter-NNN.md"
                num_str = f.name.split("-")[1].split(".")[0]
                best = max(best, int(num_str))
            except (ValueError, IndexError):
                continue
    return best


def _is_within_ring_buffer(chapter: int, latest_chapter: int) -> bool:
    """True if this chapter is within the last RING_BUFFER_N chapters.

    A chapter's snapshot stores full content when chapter >= latest_chapter - (RING_BUFFER_N - 1).
    """
    return chapter >= latest_chapter - (RING_BUFFER_N - 1)


def create_differential_snapshot(project_dir: Path, chapter: int, snapshot_dir: Path) -> None:
    """Create a differential snapshot.

    - Truth files: always full content (mutable, accumulating state).
    - Chapter/plan/audit files: SHA-256 hash references, EXCEPT for the most
      recent RING_BUFFER_N chapters which also store full content so
      revision-rollback can restore the PREVIOUS chapter after an overwrite.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Determine the latest chapter that exists in the project (ring-buffer window)
    latest_chapter = _latest_chapter_number(project_dir)
    # If this chapter is newer than any seen, it becomes the latest
    latest_chapter = max(latest_chapter, chapter)

    manifest: dict[str, Any] = {
        "version": "1.0",
        "chapter": chapter,
        "files": [],
        "truth_snapshot": {},
    }

    # Hash immutable files; store full content for recent-chapter ring buffer
    include_full = _is_within_ring_buffer(chapter, latest_chapter)
    for dir_name in HASH_ONLY_DIRS:
        dir_path = project_dir / dir_name
        if not dir_path.exists():
            continue
        for f in dir_path.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                rel_path = str(f.relative_to(project_dir))
                entry = {
                    "path": rel_path,
                    "sha256": hash_file(f),
                    "size": f.stat().st_size,
                }
                # Ring buffer: include full content for files belonging to a
                # recent chapter (e.g. chapters/chapter-003.md when ch=3 is recent)
                if (
                    include_full and dir_name == "chapters" and f"chapter-{chapter:03d}" in f.name
                ) or (include_full and dir_name == "plans" and f"chapter-{chapter:03d}" in f.name):
                    entry["content"] = f.read_text(encoding="utf-8")
                manifest["files"].append(entry)

    # Full content for mutable truth files
    truth_dir = project_dir / "truth"
    if truth_dir.exists():
        for f in truth_dir.iterdir():
            if f.is_file() and f.name in TRUTH_FILES:
                manifest["truth_snapshot"][f.name] = f.read_text(encoding="utf-8")

    manifest_file = snapshot_dir / "snapshot-manifest.json"
    safe_write(manifest_file, json.dumps(manifest, indent=2, ensure_ascii=False))
    log.info(
        "differential_snapshot_created",
        chapter=chapter,
        file_count=len(manifest["files"]),
        truth_count=len(manifest["truth_snapshot"]),
        ring_buffer_full=include_full,
    )


def restore_from_snapshot(project_dir: Path, chapter: int, snapshot_dir: Path) -> bool:
    """Restore from a differential snapshot.

    - Truth files: always restored from full content.
    - Chapter/plan files with stored full content (ring-buffer recent chapters):
      restored in full -- this is what enables revision-rollback to recover the
      PREVIOUS chapter content after a revision overwrite.
    - Hash-only files (older snapshots): integrity-verified via hash comparison,
      not restored (they are immutable).
    - Audit files: hash-verified only (immutable historical records).
    """
    manifest_file = snapshot_dir / "snapshot-manifest.json"
    if not manifest_file.exists():
        log.error("snapshot_manifest_missing", snapshot_dir=str(snapshot_dir))
        return False

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    # 1. Restore truth files (always full content)
    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    for name, content in manifest.get("truth_snapshot", {}).items():
        safe_write(truth_dir / name, content)

    # 2. Chapter/plan files: restore full-content records (ring buffer), else
    #    verify hash only.
    mismatches = []
    restored_full = 0
    for entry in manifest.get("files", []):
        filepath = project_dir / entry["path"]
        if "content" in entry:
            # Ring-buffer recent chapter: full content was snapshotted -- restore it.
            filepath.parent.mkdir(parents=True, exist_ok=True)
            safe_write(filepath, entry["content"])
            restored_full += 1
        elif filepath.exists():
            # Older snapshot: hash-only. Verify integrity, do not restore.
            current_hash = hash_file(filepath)
            if current_hash != entry["sha256"]:
                mismatches.append(entry["path"])

    # 3. Audit files: hash-verified only (immutable historical records)
    for entry in manifest.get("files", []):
        if "/audits/" in entry["path"] or entry["path"].startswith("audits/"):
            filepath = project_dir / entry["path"]
            if filepath.exists():
                current_hash = hash_file(filepath)
                if current_hash != entry["sha256"] and entry["path"] not in mismatches:
                    mismatches.append(entry["path"])

    if mismatches:
        log.warning("snapshot_hash_mismatches", chapter=chapter, files=mismatches)

    log.info(
        "snapshot_restored",
        chapter=chapter,
        mismatches=len(mismatches),
        full_content_restored=restored_full,
    )
    return True
