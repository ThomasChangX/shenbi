# Spec 10: Data Storage Optimization

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** High (composite)
> **Merged from:** `2026-07-17-consolidate-gate-markers-manifest-design.md`, `2026-07-17-consolidate-review-checklist-static-fields-design.md`, `2026-07-17-consolidate-snapshot-differential-storage-design.md`
> **Purpose:** Fix three data storage inefficiencies rooted in early-development decisions that prioritized simplicity over storage efficiency and historical traceability.

---

## 1. Executive Summary

During initial pipeline development, three storage subsystems were implemented with correctness-first simplicity: gate markers scattered across 21 individual JSON files, review checklists regenerating 7 static fields for every chapter, and snapshots storing full file copies at 172% of referenced content size. While functionally correct, each decision incurs accumulating cost as the pipeline scales to 100 chapters. This spec consolidates fixes for all three: a central pipeline manifest for gate markers, static/dynamic field separation for review checklists, and differential hash-reference snapshots for chapter recovery points.

---

## 2. Root Cause Analysis

### 2.1 Gate Markers: 21 Scattered Files, History Lost on Overwrite

**Evidence chain:**

The `gate-markers/` directory contains 21 individual JSON files (one per skill), totaling approximately 11 KB. Each file is named `G4-{skill}-generative.json` and records the last G4 verification result for that skill.

**Root cause (two-level):**

1. **Write-side fragmentation:** `dispatch_helper.py:run_gate_g4()` and `phase_runner.py:cmd_post_skill()` (line 219-222) write gate markers independently:

```python
# phase_runner.py:219-222
marker_dir = Path(round_dir) / "gate-markers"
marker = marker_dir / f"G4-{skill}-generative.json"
```

The `gates/shared.py:write_gate_marker()` function (line 182-198) provides the single write path but is called per-skill, per-gate, producing one file per call. There is no central aggregation -- each skill manages its own marker file.

2. **Read-side fragmentation:** The `scoring.py:check_gate_markers()` function (line 186-211) globs individual files to verify gate completion:

```python
# scoring.py:191-211
marker_dir = rd / "gate-markers"
marker_file = marker_dir / f"G4-{skill_name}-{test_type}.json"
```

For chapter loop skills that run every chapter (e.g., `shenbi-chapter-drafting`), the gate marker is overwritten each time -- only the last result is preserved. Historical G4 pass/fail records for earlier chapters are lost.

**Why this matters:**
- Cannot track G4 result trends (is a skill failing more frequently over time?)
- 21 fragmented files increase I/O and inode consumption
- Downstream tools must glob 21 files to understand complete gate status
- Historical gate results lost for all but the last chapter

### 2.2 Review Checklist: 7 Static Fields Regenerated 56 Times

**Evidence chain:**

The `context/review-checklist-N.json` files contain 10 fields per chapter. Across all 56 generated chapters, 7 of these 10 fields have identical values in every file:

| Field | Source | Changes Across Chapters? |
|-------|--------|------------------------|
| `chapter` | Chapter number | Yes (1-56) |
| `transition_budget` | Chapter plan | Yes (5-11 range) |
| `ending_constraints` | Chapter plan | Yes (0-3 range) |
| `ai_blacklist` | `style/style_profile.md` | **Never (always 14 items)** |
| `fatigue_warnings` | `style/style_profile.md` | **Never** |
| `voice_constraints` | Project config | **Never** |
| `pov_mode` | Project config | **Never (always empty)** |
| `hook_deliverables` | Chapter plan | **Never (always 0 -- bug, fixed in Spec 5: Content Quality Gates)** |
| `world_rules_brief` | `world/rules.md` | **Never (identical long text)** |
| `sensitivity_flags` | Project config | **Never (always 0)** |

**Root cause:**

`review_checklist.py:generate_review_checklist()` (line 60-119) builds and caches a complete `ReviewChecklist` dataclass for each chapter. The `_build_checklist()` helper reads source files and populates all 10 fields. Since 7 fields derive from static sources (`world/rules.md`, `style/style_profile.md`, project config) that do not change during the chapter loop, the LLM (via `shenbi-context-composing`) is asked to regenerate identical content for every chapter.

The review checklist was designed as a cache to avoid 11 review skills independently computing context (~330K chars -> ~4K chars). This was correct for its original purpose (review context deduplication), but the design did not distinguish between static (one-time) and dynamic (per-chapter) fields -- both are regenerated every chapter.

The token waste is compounded because `shenbi-context-composing` is an LLM dispatch: the LLM is prompted to output all 10 fields for each chapter, and 7 of them are identical to previous outputs. This introduces unnecessary format drift risk (the LLM might rephrase `world_rules_brief` differently across chapters).

### 2.3 Snapshots: Full File Copies at 172% of Referenced Size

**Evidence chain:**

~51-52 snapshots consume **~12 MB (52% of total pipeline output).** Each snapshot is a concatenated markdown file created by `chapter_loop.py:_snapshot_chapter_files()` (line 903-960):

```python
# chapter_loop.py:903-960
def _snapshot_chapter_files(project_dir: Path, chapter: int) -> None:
    parts: list[str] = []

    # Full chapter text
    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if chapter_file.exists():
        parts.append(f"## Chapter {chapter}\n\n{chapter_file.read_text(encoding='utf-8')}")

    # Full audit reports (all 13 types)
    for audit_file in sorted(audit_dir.glob(f"chapter-{chapter}-*.md")):
        parts.append(f"## Audit: {audit_file.stem}\n\n{audit_file.read_text(encoding='utf-8')}")

    # Full truth files
    for truth_file in sorted(truth_dir.glob("*.md")):
        parts.append(f"## Truth: {truth_file.name}\n\n{truth_file.read_text(encoding='utf-8')}")

    # Write concatenated markdown
    content = "\n\n---\n\n".join(parts)
    safe_write(snap_path, content.encode("utf-8"))
```

**Root cause analysis:**

The snapshot was designed as a recovery point -- a known-good state to roll back to. However, the implementation copies full file contents rather than storing references:

1. **Chapter text** is duplicated: once in `chapters/chapter-N.md` and again in the snapshot. The chapter file is immutable after snapshot creation (it is the snapshot target), making the full-text copy pure redundancy.

2. **Audit reports** are duplicated: stored in both `audits/chapter-N-*.md` and the snapshot. Audit reports are historical records -- they do not change after generation. On average, audit content constitutes 30-40% of snapshot size. In sample analysis (Ch25), ~34% of snapshot content was byte-for-byte identical to files in `audits/`.

3. **Truth files** are the only content that might differ from the working directory at restore time (truth files accumulate state across chapters). These are the only files that need content-level snapshots.

Snapshot size = 172% of (chapter file size + audit file size sum). The 72% overhead is entirely redundant copies.

**What a recovery point actually needs:**
- Which files existed at snapshot time (paths + content hashes)
- Truth file content (the only mutable, accumulating state)
- Audit report hashes for integrity verification

Full file copies are unnecessary for immutable files (chapters don't change post-snapshot; audit reports don't change post-generation).

---

## 3. Unified Fix Strategy

### 3.1 Gate Markers: Single Pipeline Manifest

**New file:** `gate-markers/pipeline-manifest.json`

Introduce a hierarchical manifest structure that replaces 21 individual files:

```json
{
  "pipeline": "xinghuo-ranqiong",
  "updated_at": "2026-07-17T21:32:04Z",
  "gates": {
    "genesis": {
      "shenbi-worldbuilding": {
        "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
      },
      "shenbi-character-design": {
        "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
      }
    },
    "chapter_loop": {
      "1": {
        "shenbi-chapter-drafting": {
          "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
        },
        "shenbi-review-resonance": {
          "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
        }
      },
      "2": { ... }
    }
  }
}
```

**Hierarchy:** phase (genesis/chapter_loop) -> chapter (number or "genesis") -> skill -> gate -> result.

#### 3.1.1 Write-Side Change

**Thread safety:** The manifest read-modify-write MUST be atomic. Use `safe_write` (temp + os.replace) for the final write, AND acquire a threading.Lock keyed by manifest path before the read-merge-write sequence. This prevents concurrent gate-marker writes from racing. See Spec 12 §3.2 for the locking pattern.

**File:** `src/shenbi/gates/shared.py` (line 182, `write_gate_marker`)

Modify `write_gate_marker()` to write into the central manifest:

```python
# Thread-safe manifest write: the read-merge-write MUST be guarded by a lock
# keyed by manifest path so concurrent gate-marker writes (e.g. parallel audits)
# do not race and clobber each other's updates. See Spec 12 §3.2 locking pattern.
import threading
_MANIFEST_LOCKS: dict[str, threading.Lock] = {}
_MANIFEST_LOCKS_GUARD = threading.Lock()

def _manifest_lock(manifest_path: Path) -> threading.Lock:
    """Return (creating if needed) a per-path lock for manifest writes."""
    key = str(manifest_path)
    with _MANIFEST_LOCKS_GUARD:
        if key not in _MANIFEST_LOCKS:
            _MANIFEST_LOCKS[key] = threading.Lock()
        return _MANIFEST_LOCKS[key]

def record_gate_result(project_dir, phase, chapter, skill, gate, result):
    manifest_path = project_dir / 'gate-markers' / 'pipeline-manifest.json'

    with _manifest_lock(manifest_path):  # guard the whole read-merge-write
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            manifest = {'pipeline': str(project_dir.name), 'gates': {}}

        phase_key = phase  # 'genesis' or 'chapter_loop'
        chapter_key = str(chapter) if chapter else 'genesis'

        gates = manifest.setdefault('gates', {})
        phases = gates.setdefault(phase_key, {})
        chapters = phases.setdefault(chapter_key, {})
        skills = chapters.setdefault(skill, {})
        skills[gate] = result

        manifest['updated_at'] = datetime.now(UTC).isoformat()
        safe_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
```

Also update callers:
- `phase_runner.py:219-222` -- redirect from per-file write to manifest write
- `gates/cli.py:121-128` -- redirect `write_gate_marker` calls

#### 3.1.2 Read-Side Change with Backward Compatibility

**File:** `src/shenbi/scoring.py` (line 186, `check_gate_markers`)

Read from manifest first, fall back to old per-file format:

```python
def get_gate_result(project_dir, skill, gate='G4'):
    # Priority: new manifest format
    manifest_path = project_dir / 'gate-markers' / 'pipeline-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for phase, chapters in manifest.get('gates', {}).items():
            for chapter, skills in chapters.items():
                if skill in skills and gate in skills[skill]:
                    return skills[skill][gate]

    # Fallback: old per-file format
    old_path = project_dir / 'gate-markers' / f'{gate}-{skill}-generative.json'
    if old_path.exists():
        return json.loads(old_path.read_text())

    return None
```

Update `check_gate_markers()` in `scoring.py` to use this unified reader.

#### 3.1.3 Benefits

- Single-file read for complete gate status (pipeline status reports)
- Historical trend tracking per chapter, per skill (is a skill's failure rate increasing?)
- Reduced I/O (1 file instead of 21+)
- Existing per-file markers remain readable during transition

### 3.2 Review Checklist: Static Template + Per-Chapter Deltas

#### 3.2.1 Split Storage

**Static template** (generated once in Genesis by `shenbi-context-composing`):

`context/review-checklist-template.json`:
```json
{
  "ai_blacklist": [...],
  "fatigue_warnings": {...},
  "voice_constraints": {...},
  "pov_mode": "",
  "world_rules_brief": "...",
  "sensitivity_flags": []
}
```

**Per-chapter deltas** (generated in chapter loop):

`context/review-checklist-chapter-N.json`:
```json
{
  "chapter": 5,
  "transition_budget": 6,
  "ending_constraints": 3,
  "hook_deliverables": ["MH-001", "MH-020"]
}
```

#### 3.2.2 Template Regeneration Triggers

The static template is regenerated only when its source data changes:
- Genesis completion (initial generation)
- `shenbi-style-learning` update (every 12 chapters, per Spec 1: Truth File)
- `shenbi-genre-config` change

#### 3.2.3 Merger Function

**File:** `src/shenbi/pipeline/review_checklist.py` (new function)

```python
def get_checklist(project_dir: Path, chapter: int) -> ReviewChecklist:
    """Merge static template with per-chapter delta to produce full checklist."""
    template_path = project_dir / 'context' / 'review-checklist-template.json'
    delta_path = project_dir / 'context' / f'review-checklist-chapter-{chapter}.json'

    template = json.loads(template_path.read_text()) if template_path.exists() else {}
    delta = json.loads(delta_path.read_text()) if delta_path.exists() else {}

    merged = {**template, **delta}
    return ReviewChecklist(**merged)
```

#### 3.2.4 SKILL.md Update

**File:** `skills/shenbi-context-composing/SKILL.md`

Update output contract:
- Genesis phase: output `context/review-checklist-template.json` (static fields only)
- Chapter loop: output `context/review-checklist-chapter-N.json` (dynamic fields + hook_deliverables)
- Remove static fields from per-chapter output prompt

#### 3.2.5 Consumer Adaptation

**File:** `src/shenbi/pipeline/review_checklist.py` (line 60, `generate_review_checklist`)

Modify to call `get_checklist()` merger instead of regenerating all fields. Cache invalidation logic shifts to checking template mtime + delta mtime vs merged result.

### 3.3 Snapshots: Differential Mode with SHA-256 Hash References

**Rollback limitation:** The differential format stores only SHA-256 hashes for chapter/plan/audit files (deemed "immutable"). However, the revision-rollback use case requires restoring the PREVIOUS chapter content after a revision overwrite. Since the chapter file IS mutated during revision, the hash-reference approach cannot restore it. **Fix:** Store full content for the last N=3 chapter snapshots (ring buffer) alongside hash references for older snapshots. This preserves rollback capability for the most common recovery scenario while maintaining differential efficiency for historical data.

#### 3.3.1 New Snapshot Format

**File:** `src/shenbi/pipeline/chapter_loop.py` (line 903, `_snapshot_chapter_files`)

Replace full-content markdown snapshot with a JSON manifest containing hash references:

```json
{
  "chapter": 25,
  "timestamp": "20260717T213204",
  "label": null,
  "files": {
    "chapter": {
      "path": "chapters/chapter-025.md",
      "sha256": "a1b2c3d4...",
      "size": 15234
    },
    "plan": {
      "path": "plans/chapter-25-plan.md",
      "sha256": "e5f6g7h8...",
      "size": 4521
    }
  },
  "audit_files": {
    "chapter-25-review-resonance.md": {
      "sha256": "i9j0k1l2...",
      "size": 8932
    },
    "chapter-25-review-character.md": {
      "sha256": "m3n4o5p6...",
      "size": 6712
    }
  },
  "truth_snapshot": {
    "book_spine.md": "# Book Spine\n\n...",
    "character_matrix.md": "| Character | Slug | ...",
    "foreshadowing_ledger.md": "| Hook ID | ..."
  }
}
```

**Storage:** `snapshots/chapter-025-20260717T213204.json`

**Design rationale:**
- **Chapter text and audit reports:** Store SHA-256 hashes only (these files are immutable post-snapshot)
- **Truth files:** Store full content (only mutable, accumulating state that rollback must restore)
- **Plan file:** Store SHA-256 hash (plan is write-once per chapter)

#### 3.3.2 Implementation

```python
def _snapshot_chapter_files(project_dir: Path, chapter: int) -> None:
    """Create a differential snapshot: hash references for immutable files,
    full content for mutable truth files."""
    import hashlib
    from datetime import datetime, UTC

    snap_dir = project_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    snap_path = snap_dir / f"chapter-{chapter:03d}-{timestamp}.json"

    manifest = {
        'chapter': chapter,
        'timestamp': timestamp,
        'label': None,
        'files': {},
        'audit_files': {},
        'truth_snapshot': {}
    }

    # 1. Hash chapter file (immutable); ring-buffer full content for recent chapters
    #    so revision-rollback can restore the PREVIOUS chapter content after a
    #    revision overwrite. Only the last N=3 chapters keep full content; older
    #    snapshots are hash-only (see §3.3 rollback-limitation note).
    latest_chapter = _latest_chapter_number(snap_dir)  # highest chapter seen so far
    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if chapter_file.exists():
        file_content = chapter_file.read_text(encoding='utf-8')
        content_bytes = file_content.encode('utf-8')
        record = {
            'path': f"chapters/chapter-{chapter}.md",
            'sha256': hashlib.sha256(content_bytes).hexdigest(),
            'size': len(content_bytes)
        }
        if chapter >= latest_chapter - 2:  # ring buffer for recent chapters (N=3)
            record["content"] = file_content  # enables revision rollback
        manifest['files']['chapter'] = record

    # 2. Hash plan file (write-once); same ring-buffer treatment for recent chapters
    plan_file = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if plan_file.exists():
        file_content = plan_file.read_text(encoding='utf-8')
        content_bytes = file_content.encode('utf-8')
        record = {
            'path': f"plans/chapter-{chapter}-plan.md",
            'sha256': hashlib.sha256(content_bytes).hexdigest(),
            'size': len(content_bytes)
        }
        if chapter >= latest_chapter - 2:  # ring buffer for recent chapters (N=3)
            record["content"] = file_content
        manifest['files']['plan'] = record

    # 3. Hash audit files (immutable post-generation)
    audit_dir = project_dir / "audits"
    if audit_dir.exists():
        for af in sorted(audit_dir.glob(f"chapter-{chapter}-*.md")):
            content = af.read_bytes()
            manifest['audit_files'][af.name] = {
                'sha256': hashlib.sha256(content).hexdigest(),
                'size': len(content)
            }

    # 4. Full content for truth files (mutable, accumulating state)
    truth_dir = project_dir / "truth"
    if truth_dir.exists():
        for tf in sorted(truth_dir.glob("*.md")):
            manifest['truth_snapshot'][tf.name] = tf.read_text(encoding='utf-8')

    safe_write(snap_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    # Update manifest and prune
    ...
```

#### 3.3.3 Restore from Snapshot

Add `restore_from_snapshot()` function:

```python
def restore_from_snapshot(project_dir: Path, snapshot_path: Path) -> None:
    """Restore truth files from a differential snapshot manifest."""
    manifest = json.loads(snapshot_path.read_text())

    # 1. Restore truth files (the only content stored in full)
    for name, content in manifest['truth_snapshot'].items():
        safe_write(project_dir / 'truth' / name, content)

    # 2. Verify chapter and audit file integrity via hash comparison;
    #    for files whose full content was stored (ring buffer, recent chapters),
    #    restore them — this is what enables revision-rollback to recover the
    #    PREVIOUS chapter content after a revision overwrite.
    for key, info in manifest['files'].items():
        original_path = project_dir / info['path']
        if "content" in info:
            # Recent-chapter ring buffer: full content was snapshotted — restore it.
            safe_write(original_path, info["content"])
        elif original_path.exists():
            # Older snapshot: hash-only. Verify integrity, do not restore.
            current_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
            if current_hash != info['sha256']:
                log.warning("snapshot_hash_mismatch",
                           file=info['path'],
                           snapshot_hash=info['sha256'],
                           current_hash=current_hash)

    # 3. Audit files: verify existence and hash (no restore needed --
    #    they are immutable historical records)
    for name, info in manifest.get('audit_files', {}).items():
        af = project_dir / 'audits' / name
        if af.exists():
            current_hash = hashlib.sha256(af.read_bytes()).hexdigest()
            if current_hash != info['sha256']:
                log.warning("snapshot_audit_hash_mismatch",
                           file=name,
                           snapshot_hash=info['sha256'],
                           current_hash=current_hash)
```

#### 3.3.4 Snapshot Naming Convention

New snapshots use `.json` extension (was `.md`). Old markdown snapshots remain readable for backward compatibility during transition. `shenbi-snapshot-manage` SKILL.md updated to document the new format.

---

## 4. Affected Files

### Gate Marker Manifest
| File | Change |
|------|--------|
| `src/shenbi/gates/shared.py` (331 lines) | Add `record_gate_result()` function; modify `write_gate_marker()` (line 182) to use manifest |
| `src/shenbi/phase_runner.py` (358 lines) | Redirect gate marker writes from per-file (line 219-222) to manifest |
| `src/shenbi/gates/cli.py` | Update `write_gate_marker` callers (line 121, 128) |
| `src/shenbi/scoring.py` | Update `check_gate_markers()` (line 186-211) to read manifest first; add `get_gate_result()` |
| `src/shenbi/gates/g7.py` | Update gate marker verification (line 169, 249) for manifest format |
| `gate-markers/pipeline-manifest.json` | **New file** -- hierarchical gate result manifest |

### Review Checklist Static/Dynamic Split
| File | Change |
|------|--------|
| `src/shenbi/pipeline/review_checklist.py` (477 lines) | Add `get_checklist()` merger function; modify `generate_review_checklist()` (line 60) to use template+delta |
| `context/review-checklist-template.json` | **New file** -- static fields generated once in Genesis |
| `context/review-checklist-chapter-N.json` | Replace current `review-checklist-N.json` -- dynamic fields only |
| `skills/shenbi-context-composing/SKILL.md` | Update output contract: Genesis writes template, chapter loop writes deltas |
| `src/shenbi/pipeline/chapter_loop.py` (1450 lines) | Update context assembly to load merged checklist |

### Snapshot Differential Storage
| File | Change |
|------|--------|
| `src/shenbi/pipeline/chapter_loop.py` (1450 lines) | Rewrite `_snapshot_chapter_files()` (line 903-960) for differential JSON manifest; add `restore_from_snapshot()` |
| `skills/shenbi-snapshot-manage/SKILL.md` | Update output format documentation for JSON manifest |
| `src/shenbi/pipeline/cli.py` | Update `rollback` command to use new `restore_from_snapshot()` |

---

## 5. Verification Criteria

### Gate Marker Manifest
1. After Genesis completes, `pipeline-manifest.json` contains G4 results for all genesis skills
2. After each chapter completes, manifest contains G4 results for all chapter loop skills for that chapter
3. `get_gate_result('shenbi-chapter-drafting', 'G4')` returns the most recent result
4. Old per-file format (`G4-{skill}-generative.json`) remains readable via fallback
5. Pipeline status reports read complete gate status from single file
6. `just check` passes with zero failures

### Review Checklist Static/Dynamic Split
7. After Genesis, `review-checklist-template.json` exists with 6 static fields
8. After 5 chapters, each chapter has only `review-checklist-chapter-N.json` (<= 500 bytes each)
9. `get_checklist(N)` merged result is functionally equivalent to current `review-checklist-N.json`
10. `hook_deliverables` is not always 0 when plan has active hooks (cross-dependency with Spec 5: Content Quality Gates)
11. Static template regenerates when style-learning updates (every 12 chapters)
12. `just check` passes with zero failures

### Snapshot Differential Storage
13. New snapshot file size <= chapter file size * 2 (not 172% as current)
14. Rollback test: restore from snapshot -> truth files correctly restored
15. Hash verification: modifying a chapter file after snapshot creation -> `restore_from_snapshot()` detects hash mismatch and warns
16. Old markdown snapshot format remains readable during transition
17. Snapshot coverage: all chapters have snapshots (cross-dependency with Spec 3: Dispatch Safety)
18. `just check` passes with zero failures

---

## 6. Dependencies

```
Spec 3 (Dispatch Safety and File Integrity)
  └── Ensures all chapters have snapshots before optimizing snapshot format

Spec 5 (Content Quality Gates and Review Optimization)
  └── Covers review checklist fixes (hook_deliverables field)

Spec 1 (Truth File and State Accumulation)
  └── Triggers static template regeneration on style-learning update

This Spec
  ├── Pipeline status report (consumes unified manifest)
  ├── shenbi-chapter-drafting (checklist consumer adaptation)
  ├── shenbi-context-composing SKILL.md (split output: template vs deltas)
  ├── shenbi-snapshot-manage SKILL.md (new JSON manifest format)
  └── pipeline rollback (restore_from_snapshot logic)
```

---

## 7. Original Code Mapping

This consolidated spec merges the following original issue codes:

| Original Issue Code | Description | Section in This Spec |
|---------------------|-------------|---------------------|
| `gate-markers` | 21 scattered gate marker JSON files with history lost on overwrite | 2.1, 3.1 |
| `review-checklist-static` | 7 static fields regenerated for every chapter | 2.2, 3.2 |
| `snapshot-differential` | Full file copies at 172% of referenced content size | 2.3, 3.3 |

---

## 8. Storage Impact Summary

| Subsystem | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Gate markers | 21 files, 11 KB total; historical data lost on overwrite | 1 file; all historical results preserved | -95% file count; +historical traceability |
| Review checklist | 56 files * 10 fields (7 static) = 560 field writes; ~220 KB | 1 template + 56 delta files (3 dynamic fields each); ~50 KB | -77% storage; -70% token waste |
| Snapshots (~51-52 chapters) | ~12 MB (172% of referenced content) | ~3.5 MB (hash references + truth files only) | -72% storage |
