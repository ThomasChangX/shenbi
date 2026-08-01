# Spec 10: Data Storage Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce storage waste: consolidate 21 gate marker files into 1 manifest (-95%), split review checklist into static template + per-chapter deltas (-77%), convert snapshots to differential SHA-256 mode with a ring buffer for recent chapters (-72%).

**Architecture:** Three independent optimizations: (1) Single `pipeline-manifest.json` with hierarchical phase→chapter→skill→gate structure replaces 21 individual JSON files (write path guarded by a per-path `threading.Lock` since read-modify-write is not atomic), (2) Review checklist split into Genesis-generated template + per-chapter dynamic deltas, (3) Snapshots store SHA-256 hashes for immutable files and full content only for mutable truth files AND for the last N=3 chapter snapshots (ring buffer) so revision-rollback can restore the previous chapter after an overwrite.

**Tech Stack:** Python 3.11+, pathlib, hashlib, json

## Global Constraints

- `just check` passes with zero failures
- `pipeline-manifest.json` contains complete gate history for all chapters
- Manifest write path is guarded by a per-path `threading.Lock` (read-modify-write is not atomic); concurrent gate-marker writes must not lose updates
- `get_gate_result()` returns same data as old per-file format (backward compat)
- Static review checklist template regenerated only on source data changes
- `get_checklist(N)` merged result functionally equivalent to current `review-checklist-N.json`
- Differential snapshots ≤ 30% of original snapshot size
- Ring buffer: store FULL content for the last N=3 chapter snapshots alongside hash references, so revision-rollback can restore the PREVIOUS chapter after an overwrite
- `restore_from_snapshot()` correctly restores all truth files AND restores full-content chapter/plan records from the ring buffer; verifies hashes for older (hash-only) snapshots
- Hash verification detects modified chapter/audit files after snapshot creation

---

### Task 1: Pipeline Manifest for Gate Markers

**Files:**
- Create: `src/shenbi/gates/gate_manifest.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (call `record_gate_result`)
- Modify: `src/shenbi/pipeline/phase_runner.py` (call `record_gate_result`)
- Test: `tests/gates/test_gate_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/gates/test_gate_manifest.py
import json
import tempfile
from pathlib import Path
from shenbi.gates.gate_manifest import (
    record_gate_result,
    get_gate_result,
    GATE_MANIFEST_FILENAME,
)

def test_record_and_retrieve_gate_result():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        record_gate_result(
            gate_manifest_dir=manifest_dir,
            phase="chapter_loop",
            chapter=5,
            skill="shenbi-review-continuity",
            gate="G4",
            result={"passed": True, "checks": {"G4.cd.verdict": "passed"}},
        )
        record_gate_result(
            gate_manifest_dir=manifest_dir,
            phase="chapter_loop",
            chapter=5,
            skill="shenbi-review-resonance",
            gate="G4",
            result={"passed": False, "checks": {"G4.rr.verdict": "failed"}},
        )

        # Retrieve
        result = get_gate_result(manifest_dir, "chapter_loop", 5, "shenbi-review-continuity", "G4")
        assert result is not None
        assert result["passed"] is True

        result2 = get_gate_result(manifest_dir, "chapter_loop", 5, "shenbi-review-resonance", "G4")
        assert result2 is not None
        assert result2["passed"] is False


def test_manifest_structure_is_hierarchical():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        record_gate_result(manifest_dir, "genesis", 0, "shenbi-worldbuilding", "G2", {"passed": True})
        record_gate_result(manifest_dir, "chapter_loop", 1, "shenbi-chapter-drafting", "G4", {"passed": True})
        record_gate_result(manifest_dir, "chapter_loop", 2, "shenbi-chapter-drafting", "G4", {"passed": False})

        manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "gates" in data
        assert "genesis" in data["gates"]
        assert "chapter_loop" in data["gates"]
        # Chapter 1 and 2 should both be present
        assert "1" in data["gates"]["chapter_loop"] or 1 in data["gates"]["chapter_loop"]


def test_get_gate_result_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        result = get_gate_result(manifest_dir, "chapter_loop", 99, "nonexistent", "G4")
        assert result is None


def test_concurrent_manifest_writes_do_not_lose_results():
    """The read-modify-write is NOT atomic; concurrent writers must be serialized
    by a per-path threading.Lock so no results are lost. See Spec §3.1.1."""
    import threading
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        n_writers = 10
        n_writes_each = 20

        def writer(skill_suffix: int) -> None:
            for ch in range(n_writes_each):
                record_gate_result(
                    gate_manifest_dir=manifest_dir,
                    phase="chapter_loop",
                    chapter=ch,
                    skill=f"shenbi-skill-{skill_suffix}",
                    gate="G4",
                    result={"passed": True},
                )

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writers should have recorded their results (no lost updates)
        manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        chapter_skills = data["gates"]["chapter_loop"]
        # For each chapter, all n_writers distinct skills must be present
        for ch in range(n_writes_each):
            skills_for_ch = chapter_skills[str(ch)]
            assert len(skills_for_ch) == n_writers, (
                f"chapter {ch}: expected {n_writers} skill entries, got {len(skills_for_ch)}"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gates/test_gate_manifest.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/gates/gate_manifest.py
import json
import threading
import structlog
from pathlib import Path
from typing import Any

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


def _load_gate_manifest(manifest_dir: Path) -> dict:
    """Load or initialize the pipeline manifest."""
    manifest_file = manifest_dir / GATE_MANIFEST_FILENAME
    if manifest_file.exists():
        try:
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("manifest_corrupt_reinitializing")
    return {"version": "1.0", "gates": {}}


def _save_gate_manifest(manifest_dir: Path, data: dict) -> None:
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

        # Navigate: gates → {phase} → {chapter} → {skill} → {gate}
        phases = data.setdefault("gates", {})
        phase_data = phases.setdefault(phase, {})
        chapter_key = str(chapter)
        chapter_data = phase_data.setdefault(chapter_key, {})
        skill_data = chapter_data.setdefault(skill, {})

        # Record timestamped entry
        import datetime
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
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
) -> dict | None:
    """Retrieve the most recent gate result. Returns None if not found."""
    data = _load_gate_manifest(manifest_dir)
    try:
        entry = data["gates"][phase][str(chapter)][skill][gate]
        if isinstance(entry, list):
            return entry[-1]["result"]  # Most recent
        return entry.get("result", entry) if isinstance(entry, dict) else None
    except (KeyError, TypeError, IndexError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/gates/test_gate_manifest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/gate_manifest.py tests/gates/test_gate_manifest.py
git commit -m "feat: add pipeline manifest for consolidated gate marker storage"
```

---

### Task 2: Differential Snapshot with SHA-256 Hashes

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:903-960` (`_snapshot_chapter_files`)
- Create: `src/shenbi/pipeline/snapshot_diff.py`
- Test: `tests/pipeline/test_snapshot_diff.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_snapshot_diff.py
import hashlib
import json
import tempfile
from pathlib import Path
from shenbi.pipeline.snapshot_diff import (
    create_differential_snapshot,
    restore_from_snapshot,
    hash_file,
)

def test_differential_snapshot_stores_hashes_not_content():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapter_file = chapter_dir / "chapter-001.md"
        chapter_text = "林风站在山顶。" * 100
        chapter_file.write_text(chapter_text, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)

        create_differential_snapshot(project_dir, 1, snapshot_dir)

        manifest_file = snapshot_dir / "snapshot-manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "files" in manifest
        # Chapter file should be stored as hash, not full content
        chapter_entry = next((f for f in manifest["files"] if "chapter-001" in f["path"]), None)
        assert chapter_entry is not None
        assert "sha256" in chapter_entry
        assert len(chapter_entry["sha256"]) == 64  # SHA-256 hex digest


def test_recent_chapter_snapshot_stores_full_content_ring_buffer():
    """Ring buffer: store FULL content for the last N=3 chapter snapshots
    alongside hash references, so revision-rollback can restore the PREVIOUS
    chapter content after a revision overwrite. Only recent chapters keep
    full content; older snapshots are hash-only."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        chapters_text = {1: "第一章内容" * 50, 2: "第二章内容" * 50, 3: "第三章内容" * 50, 4: "第四章内容" * 50}
        for ch, text in chapters_text.items():
            (chapter_dir / f"chapter-{ch:03d}.md").write_text(text, encoding="utf-8")

        snapshot_base = project_dir / "snapshots"
        snapshot_base.mkdir(parents=True)

        # Snapshot chapters in order; latest = 4, so ring buffer (N=3) covers 2,3,4
        for ch in [1, 2, 3, 4]:
            create_differential_snapshot(project_dir, ch, snapshot_base / f"chapter-{ch:03d}")

        # Chapter 2,3,4 are recent (within N=3 of latest=4) -> full content stored
        snap_2 = json.loads((snapshot_base / "chapter-002" / "snapshot-manifest.json").read_text(encoding="utf-8"))
        ch2_entry = next(f for f in snap_2["files"] if "chapter-002" in f["path"])
        assert "content" in ch2_entry, "Recent chapter (within ring buffer N=3) must store full content"
        assert ch2_entry["content"] == chapters_text[2]

        # Chapter 1 is outside the ring buffer (1 < 4-2=2) -> hash-only, no content
        snap_1 = json.loads((snapshot_base / "chapter-001" / "snapshot-manifest.json").read_text(encoding="utf-8"))
        ch1_entry = next(f for f in snap_1["files"] if "chapter-001" in f["path"])
        assert "content" not in ch1_entry, "Older snapshot (outside ring buffer) must be hash-only"
        assert "sha256" in ch1_entry


def test_snapshot_restores_truth_files():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        for sub in ["chapters", "truth"]:
            (project_dir / sub).mkdir(parents=True)
        (project_dir / "chapters" / "chapter-001.md").write_text("chapter content", encoding="utf-8")
        truth_file = project_dir / "truth" / "current_state.md"
        original_truth = "主角状态：活跃"
        truth_file.write_text(original_truth, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)
        create_differential_snapshot(project_dir, 1, snapshot_dir)

        # Modify truth file
        truth_file.write_text("主角状态：已修改", encoding="utf-8")

        # Restore
        restore_from_snapshot(project_dir, 1, snapshot_dir)
        restored = truth_file.read_text(encoding="utf-8")
        assert restored == original_truth, f"Expected '{original_truth}', got '{restored}'"


def test_restore_restores_full_content_chapter_from_ring_buffer():
    """restore_from_snapshot must restore files whose full content was stored
    (ring-buffer recent chapters), not just verify hashes."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapter_dir = project_dir / "chapters"
        chapter_dir.mkdir(parents=True)
        original_text = "第一章原始内容" * 50
        (chapter_dir / "chapter-001.md").write_text(original_text, encoding="utf-8")

        snapshot_dir = project_dir / "snapshots" / "chapter-001"
        snapshot_dir.mkdir(parents=True)
        # Only chapter 1 exists, so it is "recent" and gets full content
        create_differential_snapshot(project_dir, 1, snapshot_dir)

        # Simulate a revision overwrite of the chapter
        (chapter_dir / "chapter-001.md").write_text("修订后的内容" * 50, encoding="utf-8")

        # Restore should recover the original chapter content (ring buffer)
        restore_from_snapshot(project_dir, 1, snapshot_dir)
        restored = (chapter_dir / "chapter-001.md").read_text(encoding="utf-8")
        assert restored == original_text, "Ring-buffer chapter content must be fully restored"


def test_hash_verification_detects_modification():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("original", encoding="utf-8")
        h1 = hash_file(f)
        f.write_text("modified", encoding="utf-8")
        h2 = hash_file(f)
        assert h1 != h2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_snapshot_diff.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/pipeline/snapshot_diff.py
import hashlib
import json
from pathlib import Path
import structlog

log = structlog.get_logger()

# Ring-buffer size: store FULL content for the last N=3 chapter snapshots so
# revision-rollback can restore the PREVIOUS chapter content after a revision
# overwrite. Older snapshots are hash-only.
RING_BUFFER_N = 3

# Files that need full content backup (mutable truth files)
TRUTH_FILES = {"current_state.md", "character_matrix.md", "current_focus.md",
               "resonance_trend.md", "audit_drift.md", "emotional_arcs.md",
               "chapter_summaries.md", "pending_hooks.md", "world_rules.md"}

# Files only tracked by hash (immutable once written)
HASH_ONLY_DIRS = {"chapters", "audits", "plans"}


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _latest_chapter_number(snapshots_base_dir: Path) -> int:
    """Return the highest chapter number seen among existing snapshots (0 if none)."""
    if not snapshots_base_dir.exists():
        return 0
    best = 0
    for d in snapshots_base_dir.iterdir():
        if d.is_dir() and d.name.startswith("chapter-"):
            try:
                best = max(best, int(d.name.split("-")[1]))
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

    # Determine the latest chapter seen so far (ring-buffer window)
    snapshots_base = snapshot_dir.parent
    latest_chapter = _latest_chapter_number(snapshots_base)
    # If this chapter is newer than any seen, it becomes the latest
    latest_chapter = max(latest_chapter, chapter)

    manifest = {"version": "1.0", "chapter": chapter, "files": [], "truth_snapshot": {}}

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
                if include_full and dir_name == "chapters" and f"chapter-{chapter:03d}" in f.name:
                    entry["content"] = f.read_text(encoding="utf-8")
                elif include_full and dir_name == "plans" and f"chapter-{chapter:03d}" in f.name:
                    entry["content"] = f.read_text(encoding="utf-8")
                manifest["files"].append(entry)

    # Full content for mutable truth files
    truth_dir = project_dir / "truth"
    if truth_dir.exists():
        for f in truth_dir.iterdir():
            if f.is_file() and f.name in TRUTH_FILES:
                manifest["truth_snapshot"][f.name] = f.read_text(encoding="utf-8")

    manifest_file = snapshot_dir / "snapshot-manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("differential_snapshot_created", chapter=chapter,
             file_count=len(manifest["files"]),
             truth_count=len(manifest["truth_snapshot"]),
             ring_buffer_full=include_full)


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
        (truth_dir / name).write_text(content, encoding="utf-8")

    # 2. Chapter/plan files: restore full-content records (ring buffer), else
    #    verify hash only.
    mismatches = []
    restored_full = 0
    for entry in manifest.get("files", []):
        filepath = project_dir / entry["path"]
        if "content" in entry:
            # Ring-buffer recent chapter: full content was snapshotted -- restore it.
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(entry["content"], encoding="utf-8")
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

    log.info("snapshot_restored", chapter=chapter,
             mismatches=len(mismatches), full_content_restored=restored_full)
    return True
```

- [ ] **Step 4: Wire `snapshot_diff.py` into `_snapshot_chapter_files`**
  In `chapter_loop.py`, after the existing `_snapshot_chapter_files` function body,
  add a call to `create_differential_snapshot(project_dir, chapter)` and replace
  the monolithic markdown snapshot with the differential SHA-256 approach.
  The old snapshot code is guarded by `if use_legacy_snapshot:` for rollback safety.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/pipeline/test_snapshot_diff.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/snapshot_diff.py tests/pipeline/test_snapshot_diff.py
git commit -m "feat: implement differential snapshot with SHA-256 hash verification"
```

---

### Task 3: Review Checklist Static/Dynamic Split

**Files:**
- Create: `src/shenbi/pipeline/review_checklist.py`
- Modify: `skills/shenbi-context-composing/SKILL.md`
- Test: `tests/pipeline/test_review_checklist.py`

> **Note:** `build_review_checklist()` is defined in Plan 2 (Content Quality Gates). This task adds `generate_static_template()`, `generate_chapter_delta()`, and `get_checklist()` to the same module (`src/shenbi/pipeline/review_checklist.py`). The two implementations coexist in one module.

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_review_checklist.py
import json
import tempfile
from pathlib import Path
from shenbi.pipeline.review_checklist import (
    generate_static_template,
    generate_chapter_delta,
    get_checklist,
)

def test_get_checklist_merges_template_and_delta():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)

        template = {
            "ai_blacklist": ["avoid_word_1"],
            "voice_constraints": "third_person",
            "pov_mode": "limited",
            "world_rules_brief": "rules summary",
            "sensitivity_flags": 0,
        }
        (context_dir / "review-checklist-template.json").write_text(
            json.dumps(template, ensure_ascii=False), encoding="utf-8")

        delta = {
            "chapter": 5,
            "transition_budget": 3,
            "ending_constraints": "cliffhanger",
            "hook_deliverables": ["MH-001-advance"],
        }
        (context_dir / "review-checklist-chapter-005.json").write_text(
            json.dumps(delta, ensure_ascii=False), encoding="utf-8")

        merged = get_checklist(project_dir, 5)
        assert merged["ai_blacklist"] == ["avoid_word_1"]
        assert merged["chapter"] == 5
        assert merged["hook_deliverables"] == ["MH-001-advance"]


def test_generate_chapter_delta_extracts_hooks():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        plans_dir = project_dir / "plans"
        plans_dir.mkdir(parents=True)
        plan = """## 7. Hook Ledger
| MH-001 | advance | 推到50% |
| MH-003 | plant | 新线索 |
"""
        (plans_dir / "chapter-005-plan.md").write_text(plan, encoding="utf-8")

        delta = generate_chapter_delta(project_dir, 5)
        assert "hook_deliverables" in delta
        assert len(delta["hook_deliverables"]) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_review_checklist.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/pipeline/review_checklist.py
import json
import re
from pathlib import Path
import structlog

log = structlog.get_logger()

STATIC_FIELDS = {"ai_blacklist", "fatigue_warnings", "voice_constraints",
                 "pov_mode", "world_rules_brief", "sensitivity_flags"}
DYNAMIC_FIELDS = {"chapter", "transition_budget", "ending_constraints",
                  "hook_deliverables", "fatigue_warnings_dynamic"}


def generate_static_template(project_dir: Path) -> dict:
    """Generate the static review checklist template from Genesis sources."""
    template = {
        "ai_blacklist": _load_blacklist(project_dir),
        "voice_constraints": _load_voice_constraints(project_dir),
        "pov_mode": _load_pov_mode(project_dir),
        "world_rules_brief": _load_world_rules_brief(project_dir),
        "sensitivity_flags": 0,
        "fatigue_warnings": [],
    }
    return template


def generate_chapter_delta(project_dir: Path, chapter: int) -> dict:
    """Generate per-chapter dynamic delta for review checklist."""
    delta = {
        "chapter": chapter,
        "transition_budget": 0,
        "ending_constraints": "",
        "hook_deliverables": _extract_hooks_from_plan(project_dir, chapter),
    }
    return delta


def get_checklist(project_dir: Path, chapter: int) -> dict:
    """Merge static template with per-chapter delta."""
    context_dir = project_dir / "context"
    template_file = context_dir / "review-checklist-template.json"
    delta_file = context_dir / f"review-checklist-chapter-{chapter:03d}.json"

    template = {}
    if template_file.exists():
        template = json.loads(template_file.read_text(encoding="utf-8"))

    delta = {}
    if delta_file.exists():
        delta = json.loads(delta_file.read_text(encoding="utf-8"))

    return {**template, **delta}


def _extract_hooks_from_plan(project_dir: Path, chapter: int) -> list[dict]:
    """Extract hook operations from chapter plan Section 7 hook ledger."""
    plan_file = project_dir / "plans" / f"chapter-{chapter:03d}-plan.md"
    if not plan_file.exists():
        return []
    plan_text = plan_file.read_text(encoding="utf-8")
    # Parse Section 7 hook ledger table
    hooks = []
    in_section_7 = False
    hook_pattern = re.compile(r"\|\s*(MH-\d+|P\d+-[a-z]+)\s*\|\s*(\w+)\s*\|")
    for line in plan_text.split("\n"):
        if "Hook Ledger" in line or "钩子账本" in line:
            in_section_7 = True
            continue
        if in_section_7 and line.startswith("##"):
            break
        if in_section_7:
            match = hook_pattern.search(line)
            if match:
                hooks.append({"id": match.group(1), "operation": match.group(2)})
    return hooks


def _load_blacklist(project_dir: Path) -> list[str]:
    style_file = project_dir / "style" / "style_profile.md"
    if style_file.exists():
        text = style_file.read_text(encoding="utf-8")
        # Extract blacklist items
        return [line.strip("- ") for line in text.split("\n") if "avoid" in line.lower()][:10]
    return []


def _load_voice_constraints(project_dir: Path) -> str:
    return "third_person_limited"


def _load_pov_mode(project_dir: Path) -> str:
    return "multi_pov"


def _load_world_rules_brief(project_dir: Path) -> str:
    rules_file = project_dir / "truth" / "world_rules.md"
    if rules_file.exists():
        return rules_file.read_text(encoding="utf-8")[:3000]
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_review_checklist.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/review_checklist.py tests/pipeline/test_review_checklist.py
git commit -m "feat: split review checklist into static template and per-chapter deltas"
```
