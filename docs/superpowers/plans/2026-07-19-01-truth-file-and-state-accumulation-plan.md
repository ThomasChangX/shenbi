# Truth File and State Accumulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the truth-file system so cumulative-history files accumulate via key-based upsert (not overwrite or substring matching), persist resonance scores to `resonance_trend.md` reusing existing parsers, fix style-learning trigger self-heal and failure visibility in `triggers.py` (the system already exists — do NOT add parallel triggers), add G4 character_matrix integrity + protagonist_presence checks, and self-heal pipeline state audit counts against the filesystem.

**Architecture:** A new `truth_io.py` module wraps `safe_write` with key-based upsert driven by frontmatter `update_mode`. Two serialization formats are supported: `upsert_yaml` (structured records, key dedup — used by hooks) and `upsert_markdown_row` (table rows, key-column dedup — used by trend files read by `escalation_bridge.py`). Resonance scores reuse the existing `_parse_resonance_score` parser at `chapter_loop.py:667` (reads the per-chapter report) and persist a simplified 7-column markdown table row to `resonance_trend.md` matching the format `parse_resonance_scores` (`escalation_bridge.py:15-17`) consumes. Style-learning: the trigger system already EXISTS in `triggers.py` (`TRIGGER_STEPS`, `check_triggers`, `run_triggered_skills`) — the fix adds self-heal on resume + failure visibility, NOT a parallel trigger. Audit counts are verified against the filesystem at state-save time. In-process thread safety uses `threading.Lock` keyed by path.

**Tech Stack:** Python 3.11+, pathlib, structlog, json, re, threading

## Global Constraints

- `resonance_trend.md` must have N data rows for N chapters (not 1)
- `chapter_summaries.md` must reference N chapters (not 1)
- `pending_hooks.md` must contain hook data from all chapters
- `emotional_arcs.md` must have N chapter entries
- Idempotency: running the same chapter twice does not produce duplicate entries in upsert-mode files (key-based dedup, not substring matching)
- All chapters must have `resonance_score != null` in pipeline state
- After 4 chapters, `style_profile.md` must be non-bootstrap (confidence >= medium, sample_chapter_count >= 3)
- Every chapter's G4 check must confirm protagonist name appears >= 3 times
- `character_matrix.md` must retain human character definitions; parameter agents go to `particle_ledger.md`
- Pipeline state audit counts must match filesystem `chapter-N-*.md` file count for every chapter
- Regression: `just check` passes fully

---

### Task 1: Create `write_truth_file()` with Key-Based Upsert (Dual Format)

**Files:**
- Create: `src/shenbi/pipeline/truth_io.py`
- Test: `tests/unit/pipeline/test_truth_io.py`

**Interfaces:**
- Consumes: `safe_write` from `src/shenbi/safe_write.py`
- Produces: `write_truth_file(project_dir, filename, new_data, *, mode, key_field)` — `mode` is `"replace"`, `"upsert_yaml"`, or `"upsert_markdown_row"`

**Design note (from spec §3.2 and the `truth_index.py` lesson):** Idempotency is based on natural keys (chapter number, hook id), NOT substring matching. `truth_index.py` explicitly abandoned substring matching as "the broken approach." LLM-generated prose is never byte-identical across runs, so substring matching causes both false negatives (whitespace diffs defeat the check) and false positives (short sections that are substrings get dropped). Two serialization formats: `upsert_yaml` (structured records, like `hook_planting.py:204-276`) and `upsert_markdown_row` (table rows read by `escalation_bridge.py:15-17`).

**Thread safety:** Uses `threading.Lock` keyed by path (in-process concurrency). NOT `fcntl.flock` — the spec calls for in-process locking keyed by path.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for truth_io.py — key-based upsert truth file writer (dual format)."""
import tempfile
from pathlib import Path

from shenbi.pipeline.truth_io import write_truth_file


def test_replace_mode_overwrites_existing():
    """Replace mode completely overwrites the file with new content."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "current_state.md"
        target.write_text("## Chapter 1 state\nold data")

        write_truth_file(project_dir, "current_state.md",
                         "## Chapter 2 state\nnew data", mode="replace")

        result = target.read_text()
        assert "Chapter 2 state" in result
        assert "old data" not in result


def test_upsert_markdown_row_appends_new_key_and_preserves_existing():
    """markdown-row upsert keeps existing rows and adds the new key's row."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "resonance_trend.md"
        existing = "| Ch1 | - | - | - | - | 60 | high |\n"
        target.write_text(existing)

        new = "| Ch2 | - | - | - | - | 58 | medium |"
        write_truth_file(project_dir, "resonance_trend.md", new,
                         mode="upsert_markdown_row", key_field="chapter")

        result = target.read_text()
        assert "Ch1" in result
        assert "Ch2" in result
        assert result.index("Ch1") < result.index("Ch2")


def test_upsert_markdown_row_dedups_on_key_not_substring():
    """Re-writing the same key replaces the old row (key-based, not substring)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "resonance_trend.md"
        target.write_text("| Ch1 | - | - | - | - | 60 | high |")

        # New row for SAME key (Ch1) with DIFFERENT prose — substring would fail,
        # key-based upsert must replace the row in place.
        write_truth_file(project_dir, "resonance_trend.md",
                         "| Ch1 | - | - | - | - | 62 | high |",
                         mode="upsert_markdown_row", key_field="chapter")

        result = target.read_text()
        # Exactly one Ch1 row, with the new value (62), not duplicated
        assert result.count("| Ch1") == 1
        assert "62" in result
        assert "60" not in result


def test_upsert_markdown_row_creates_file_if_missing():
    """markdown-row upsert creates the file when it does not exist yet."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)

        write_truth_file(project_dir, "resonance_trend.md",
                         "| Ch1 | - | - | - | - | 60 | high |",
                         mode="upsert_markdown_row", key_field="chapter")

        target = truth_dir / "resonance_trend.md"
        assert target.exists()
        assert "Ch1" in target.read_text()


def test_upsert_markdown_row_preserves_headers_and_prose():
    """Non-table content (frontmatter, headers, prose) is preserved."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "audit_drift.md"
        target.write_text("---\nupdate_mode: upsert_markdown_row\n---\n\n# Audit Drift\n\n## Notes\nSome prose.\n")

        write_truth_file(project_dir, "audit_drift.md",
                         "| Ch1 | finding |",
                         mode="upsert_markdown_row", key_field="chapter")

        result = target.read_text()
        assert "# Audit Drift" in result
        assert "Some prose." in result
        assert "| Ch1 | finding |" in result


def test_upsert_yaml_dedups_records_by_key_field():
    """yaml upsert dedups structured records by key_field (hook id)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "pending_hooks.md"
        # Existing YAML-fronted file with one hook record
        target.write_text("---\nhooks:\n  - id: MH-001\n    state: PLANTED\n---\n\nbody\n")

        new_records = [{"id": "MH-001", "state": "TRIGGERED"},
                       {"id": "MH-002", "state": "PLANTED"}]
        write_truth_file(project_dir, "pending_hooks.md", new_records,
                         mode="upsert_yaml", key_field="id")

        result = target.read_text()
        # MH-001 replaced (not duplicated), MH-002 added
        assert result.count("MH-001") == 1
        assert result.count("MH-002") == 1
        assert "TRIGGERED" in result


def test_write_preserves_utf8_chinese_characters():
    """replace/upsert preserves Chinese characters correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "current_state.md"
        target.write_text("## 主角状态\n林烽在边城")

        write_truth_file(project_dir, "current_state.md",
                         "## 主角状态\n林烽离开边城", mode="replace")

        result = target.read_text()
        assert "林烽离开边城" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_truth_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.pipeline.truth_io'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Key-based upsert truth-file writer for pipeline integrity.

Wraps :func:`shenbi.safe_write.safe_write` with update-mode awareness:
- ``replace``: atomic overwrite (current snapshot files)
- ``upsert_yaml``: read existing YAML records, dedup by key_field, merge,
  re-serialize, write (structured data like hooks)
- ``upsert_markdown_row``: read existing markdown table rows, dedup by key
  column, merge new row, write (trend files read by escalation_bridge)

Idempotency is based on NATURAL KEYS (chapter number, hook id), NOT substring
matching. truth_index.py already abandoned substring matching as the broken
approach; LLM prose is never byte-identical across runs so substring matching
yields false negatives (whitespace diffs) and false positives (short substrings
dropped). The proven pattern is hook_planting.py:204-276 (read structured data,
dedup by stable key, merge, write back).

Thread safety: in-process threading.Lock keyed by path (not fcntl.flock).
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

# Per-path locks for in-process concurrency. Keyed by resolved truth-file path.
_PATH_LOCKS: dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _get_path_lock(path: Path) -> threading.Lock:
    """Get or create the in-process lock for a given truth-file path."""
    key = str(path)
    with _PATH_LOCKS_GUARD:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.Lock()
        return _PATH_LOCKS[key]


def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | list[dict],  # str for markdown_table mode, list[dict] for yaml
    *,
    mode: str = "replace",       # replace | upsert_yaml | upsert_markdown_row
    key_field: str | None = None,
) -> None:
    """Write to a truth file, respecting update_mode.

    Args:
        project_dir: Root directory of the novel project.
        filename: Relative filename within ``truth/`` (e.g. ``resonance_trend.md``).
        new_data: Content to write. ``str`` for replace/upsert_markdown_row,
            ``list[dict]`` for upsert_yaml.
        mode: ``"replace"`` for atomic overwrite, ``"upsert_yaml"`` for
            structured-record key dedup, ``"upsert_markdown_row"`` for
            table-row key-column dedup.
        key_field: Natural key for dedup (e.g. ``"chapter"``, ``"id"``).
            Required for the upsert modes.

    Raises:
        ValueError: If mode is unrecognized or key_field missing for upsert.
    """
    if mode not in ("replace", "upsert_yaml", "upsert_markdown_row"):
        raise ValueError(
            f"Unknown mode '{mode}'; expected 'replace', 'upsert_yaml', "
            f"or 'upsert_markdown_row'"
        )

    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    path = truth_dir / filename

    lock = _get_path_lock(path)
    with lock:
        if mode == "replace":
            content = new_data if isinstance(new_data, str) else str(new_data)
            safe_write(path, content)
            log.debug("truth_file_replaced", file=filename)
            return

        if mode == "upsert_markdown_row":
            if not isinstance(new_data, str):
                raise ValueError("upsert_markdown_row requires str new_data")
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            merged = _upsert_markdown_table_row(existing, new_data, key_field or "chapter")
            safe_write(path, merged)
            log.info("truth_file_markdown_row_upserted", file=filename)
            return

        if mode == "upsert_yaml":
            if not isinstance(new_data, list):
                raise ValueError("upsert_yaml requires list[dict] new_data")
            if key_field is None:
                raise ValueError("upsert_yaml requires key_field")
            existing_records = _read_yaml_records(path)
            merged = _upsert_by_key(existing_records, new_data, key_field)
            content = _serialize_yaml_records(merged, filename)
            safe_write(path, content)
            log.info("truth_file_yaml_upserted", file=filename)


def _upsert_markdown_table_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup a markdown table row by key column value.

    Extracts the key from new_row's first ``|`` cell, removes any existing row
    with the same key, appends new_row. Preserves headers and non-table content
    (frontmatter, prose). This is key-based dedup, NOT substring matching.
    """
    # Extract key from new_row (first cell after |)
    new_key_match = re.match(r"\|\s*(\S+)", new_row)
    if not new_key_match:
        # Not a table row — just append to existing content
        return existing.rstrip() + "\n" + new_row
    new_key = new_key_match.group(1)

    lines = existing.split("\n")
    result_lines = []
    for line in lines:
        if line.startswith("|"):
            existing_key_match = re.match(r"\|\s*(\S+)", line)
            if existing_key_match and existing_key_match.group(1) == new_key:
                continue  # Skip the existing row with the same key — replaced below
        result_lines.append(line)
    result_lines.append(new_row)
    return "\n".join(result_lines)


def _read_yaml_records(path: Path) -> list[dict]:
    """Read the YAML-fronted records list (e.g. frontmatter ``hooks:`` array)."""
    if not path.exists():
        return []
    try:
        import yaml
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
                for key in ("hooks", "records", "items"):
                    if isinstance(fm, dict) and isinstance(fm.get(key), list):
                        return fm[key]
        return []
    except (yaml.YAMLError, OSError, ValueError):
        log.warning("truth_yaml_read_failed", path=str(path))
        return []


def _upsert_by_key(existing: list[dict], new_records: list[dict], key_field: str) -> list[dict]:
    """Merge records by key_field: new records replace existing ones with same key."""
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for rec in existing:
        if isinstance(rec, dict) and key_field in rec:
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
        else:
            # Preserve records without the key field at the front
            order.insert(0, f"__nokey_{id(rec)}__")
            by_key[f"__nokey_{id(rec)}__"] = rec
    for rec in new_records:
        if isinstance(rec, dict) and key_field in rec:
            k = str(rec[key_field])
            if k not in by_key:
                order.append(k)
            by_key[k] = rec
    return [by_key[k] for k in order if k in by_key]


def _serialize_yaml_records(records: list[dict], filename: str) -> str:
    """Serialize records back into the YAML-frontmatter + markdown-body format."""
    import yaml
    yaml_key = "hooks" if "hook" in filename else "records"
    fm = {yaml_key: records}
    front = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_truth_io.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_truth_io.py src/shenbi/pipeline/truth_io.py
git commit -m "feat: add write_truth_file() with key-based dual-format upsert"
```

---

### Task 2: Add `update_mode` Frontmatter Convention to Truth File Templates

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (in `_TRUTH_FILE_TITLES` and `_init_truth_templates`)
- Test: `tests/unit/pipeline/test_truth_io.py` (append tests from Task 1 work without change)

**Interfaces:**
- Consumes: `write_truth_file` from Task 1
- Produces: Truth templates include `update_mode` (`replace`, `upsert_markdown_row`, or `upsert_yaml`) in YAML frontmatter

**Mode names (from spec §3.1):** Snapshot files use `update_mode: replace`. Cumulative-history markdown-table files use `update_mode: upsert_markdown_row`. Structured-record files use `update_mode: upsert_yaml`. These are the three modes `write_truth_file()` supports in Task 1.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/unit/pipeline/test_truth_io.py

def test_init_templates_include_update_mode_frontmatter():
    """Truth file templates include update_mode in YAML frontmatter."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        from shenbi.pipeline.dispatch_helper import _init_truth_templates
        _init_truth_templates(project_dir)

        # Cumulative markdown-table files must have update_mode: upsert_markdown_row
        resonance = (project_dir / "truth" / "resonance_trend.md").read_text()
        assert "update_mode: upsert_markdown_row" in resonance, (
            "resonance_trend should be upsert_markdown_row-mode")

        # Snapshot files must have update_mode: replace
        current = (project_dir / "truth" / "current_state.md").read_text()
        assert "update_mode: replace" in current, "current_state should be replace-mode"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_truth_io.py::test_init_templates_include_update_mode_frontmatter -v`
Expected: FAIL (assertion error, no update_mode in frontmatter)

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/dispatch_helper.py`, update `_TRUTH_FILE_TITLES` to include mode. Mode values match the `write_truth_file()` modes from Task 1.

```python
# Replace lines 331-336 in dispatch_helper.py
_TRUTH_FILE_TITLES: dict[str, tuple[str, str]] = {
    "current_state.md": ("Current State", "replace"),
    "character_matrix.md": ("Character Matrix", "replace"),
    "emotional_arcs.md": ("Emotional Arcs", "upsert_markdown_row"),
    "chapter_summaries.md": ("Chapter Summaries", "upsert_markdown_row"),
}
```

Then update `_init_truth_templates` (around line 378) to emit `update_mode` in the frontmatter:

```python
def _init_truth_templates(project_dir: Path) -> None:
    """Create minimal truth template files with required YAML frontmatter.

    Each template includes an ``update_mode`` field (``replace``,
    ``upsert_markdown_row``, or ``upsert_yaml``) so downstream writers and
    state-settling can distinguish snapshot vs cumulative files. The value
    must match one of the modes accepted by ``write_truth_file()``.
    """
    truth_dir = project_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    declared_fields = _collect_declared_truth_fields()
    for filename, (title, mode) in _TRUTH_FILE_TITLES.items():
        tp = truth_dir / filename
        if tp.exists():
            continue  # Don't overwrite existing truth files
        fields = declared_fields.get(filename, [])
        header = f"---\nupdate_mode: {mode}\n---\n\n# {title}\n\n"
        body = "\n".join(f"## {f}\n\n" for f in fields)
        safe_write(tp, header + body)
        log.info("truth_template_created", file=filename, mode=mode)
```

Also update the caller on line 378 where `_TRUTH_FILE_TITLES` is iterated:

```python
# Line ~378, in _init_truth_templates:
# Change: for filename, title in _TRUTH_FILE_TITLES.items():
# To:
for filename, (title, mode) in _TRUTH_FILE_TITLES.items():
```

Update the dict key reads in `_collect_declared_truth_fields()` (line 352):

```python
# Change: declared: dict[str, dict[str, None]] = {name: {} for name in _TRUTH_FILE_TITLES}
# To:
declared: dict[str, dict[str, None]] = {name: {} for name in _TRUTH_FILE_TITLES}
# (Still works because _TRUTH_FILE_TITLES.keys() is the filename)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_truth_io.py::test_init_templates_include_update_mode_frontmatter -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_truth_io.py src/shenbi/pipeline/dispatch_helper.py
git commit -m "feat: add update_mode frontmatter to truth file templates"
```

---

### Task 3: Update `state-settling` SKILL.md to Distinguish Append vs Replace Mode

**Files:**
- Modify: `skills/shenbi-state-settling/SKILL.md`

**Interfaces:**
- Consumes: `update_mode` field in truth file frontmatter (Task 2)
- Produces: LLM prompt instructs agent to output only new chapter sections/rows for upsert-mode files (upsert_markdown_row / upsert_yaml)

- [ ] **Step 1: Read current SKILL.md for precise edit points**

Read the file to understand its structure before editing:
Run: `head -80 skills/shenbi-state-settling/SKILL.md`

- [ ] **Step 2: Write the updated SKILL.md section**

Insert after the first paragraph of the skill description:

```markdown
### Truth File Update Mode Rules (CRITICAL)

**Every truth file declares its update mode in YAML frontmatter: `update_mode: replace`, `update_mode: upsert_markdown_row`, or `update_mode: upsert_yaml`.**

- **replace-mode files** (snapshot type — output the ENTIRE file content):
  - `current_state.md` — current chapter snapshot
  - `character_matrix.md` — character state snapshot (DO NOT overwrite "角色定义" section — see below)

- **upsert_markdown_row files** (cumulative type — output ONLY the new chapter's row, NOT the entire file):
  - `resonance_trend.md` — one trend row for the current chapter
  - `audit_drift.md` — drift findings for the current chapter
  - `emotional_arcs.md` — emotional arc entry for the current chapter
  - `chapter_summaries.md` — summary reference for the current chapter

- **upsert_yaml files** (cumulative structured records — output ONLY the new record(s)):
  - `pending_hooks.md` — hook planting/tracking data for the current chapter

**For cumulative files (upsert_markdown_row / upsert_yaml):** Output ONLY the
new data for the current chapter. The pipeline's `write_truth_file()` will
dedup by natural key (chapter number / hook id) and merge — it will replace any
existing record with the same key, so re-runs are safe. Do NOT output the
complete file content for cumulative files — doing so will cause data
accumulation to fail.

### `character_matrix.md` Write-Protection Rule

The `## 角色定义` section (character definitions) is HUMAN-AUTHORED from the
character design files (`characters/protagonist.md`, etc.) and MUST NEVER be
overwritten. Parameter agents (冷, 光, 安静, etc.) must be written to
`particle_ledger.md`, NOT to `character_matrix.md`. Only update the per-chapter
state section (names appearing in the chapter, state changes).
```

- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-state-settling/SKILL.md
git commit -m "docs: add update_mode rules and character_matrix write-protection to state-settling"
```

---

### Task 4: Persist Resonance Score to `resonance_trend.md` (Reuse Existing Parser, Simplified Row)

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (after `cs.resonance_score` is set at line 1431 and after `_route_revision_after_resonance` at line ~1438)
- Test: `tests/unit/pipeline/test_resonance_persistence.py`

**Interfaces:**
- Consumes: existing `_parse_resonance_score` (`chapter_loop.py:667`, returns `int | None`) — DO NOT create a new parser
- Consumes: `write_truth_file(..., mode="upsert_markdown_row", key_field="chapter")` from Task 1
- Produces: `resonance_trend.md` updated with current chapter's 7-column markdown row; `cs.resonance_score` already populated upstream

**Critical format constraint (from spec §3.4):** The existing reader `parse_resonance_scores` at `src/shenbi/orchestration/escalation_bridge.py:15-17` parses `|`-delimited markdown table rows, requires `len(cells) >= 7`, and reads `cells[6]` (the 7th column) as the overall score. The writer MUST produce this exact 7-column markdown format — NOT YAML. If the row had fewer than 7 columns, `parse_resonance_scores` returns `[]` and escalation routing silently breaks.

**Available data only:** `_parse_resonance_score` returns `int | None` (the overall score only). There is no per-dimension data or `chapter_role` available at this point in the loop. The row is therefore simplified: only the overall score (column 7) is populated; other columns use `-` placeholders. Per-dimension scores would require extending `_parse_resonance_score` (a future enhancement, NOT part of this task).

- [ ] **Step 1: Write the failing test**

```python
"""Tests for resonance score persistence to resonance_trend.md.

Verifies the persisted row matches the format parse_resonance_scores
(src/shenbi/orchestration/escalation_bridge.py:15-17) consumes:
lines starting with "|", split on "|", requires >=7 cells, reads cells[6]
(7th column) as the overall score.
"""
import re
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _build_resonance_trend_row


def test_trend_row_has_seven_columns_with_overall_in_column_7():
    """Row has >=7 | cells; overall score in cells[6] (7th column)."""
    row = _build_resonance_trend_row(chapter=5, overall=70)
    # Must start with | so parse_resonance_scores picks it up
    assert row.startswith("|")
    cells = [c.strip() for c in row.split("|") if c.strip() != "" or True]
    # Split on "|" yields empty strings at the ends; filter meaningfully:
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert len(cells) >= 7, f"Expected >=7 cells, got {len(cells)}: {row}"
    # cells[0] is the chapter key (Ch5), cells[6] is overall (column 7)
    assert cells[0] == "Ch5"
    assert cells[6] == "70"


def test_trend_row_key_column_is_chapter_number():
    """Key column (cells[0]) is Ch{N} for key-based dedup."""
    row = _build_resonance_trend_row(chapter=12, overall=55)
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert cells[0] == "Ch12"


def test_trend_row_has_placeholder_columns_for_missing_dims():
    """Columns without available data use '-' placeholders (not omitted)."""
    row = _build_resonance_trend_row(chapter=3, overall=42)
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    # Columns 1-5 (indices) are placeholders; overall is at index 6
    for idx in range(1, 6):
        assert cells[idx] == "-", f"cell {idx} should be '-' placeholder, got {cells[idx]}"
    assert cells[6] == "42"


def test_persist_via_write_truth_file_round_trips_through_reader():
    """Writing the row then parsing it yields the overall score back.

    Simulates what parse_resonance_scores (escalation_bridge.py:15-17) does:
    scan lines starting with '|', split on '|', require >=7 cells, read cells[6].
    """
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        write_truth_file(project_dir, "resonance_trend.md",
                         _build_resonance_trend_row(chapter=7, overall=88),
                         mode="upsert_markdown_row", key_field="chapter")

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        scores = []
        for line in text.splitlines():
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 7:
                    try:
                        scores.append(float(cells[6]))
                    except ValueError:
                        pass
        assert scores == [88.0]


def test_re_persist_same_chapter_replaces_row_in_place():
    """Key-based dedup: re-persisting the same chapter replaces, not duplicates."""
    from shenbi.pipeline.truth_io import write_truth_file

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()

        write_truth_file(project_dir, "resonance_trend.md",
                         _build_resonance_trend_row(chapter=9, overall=60),
                         mode="upsert_markdown_row", key_field="chapter")
        write_truth_file(project_dir, "resonance_trend.md",
                         _build_resonance_trend_row(chapter=9, overall=65),
                         mode="upsert_markdown_row", key_field="chapter")

        text = (project_dir / "truth" / "resonance_trend.md").read_text()
        assert text.count("| Ch9") == 1
        assert "65" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_resonance_persistence.py -v`
Expected: FAIL (`ImportError: cannot import name '_build_resonance_trend_row'`)

- [ ] **Step 3: Write minimal implementation**

Add the row builder to `src/shenbi/pipeline/chapter_loop.py`. It produces exactly the 7-column markdown format that `parse_resonance_scores` (`src/shenbi/orchestration/escalation_bridge.py:15-17`) reads — overall score in column 7, other columns `-` placeholders because only `cs.resonance_score` (an `int | None`) is available here:

```python
def _build_resonance_trend_row(chapter: int, overall: int) -> str:
    """Build a 7-column markdown table row for resonance_trend.md.

    Format MUST match what parse_resonance_scores
    (src/shenbi/orchestration/escalation_bridge.py:15-17) reads:
    lines starting with "|", split on "|", requires >=7 cells, reads
    cells[6] (7th column) as the overall score.

    Only the overall score (cs.resonance_score, an int) is available here;
    the upstream parser _parse_resonance_score (chapter_loop.py:667) returns
    int|None with no per-dimension breakdown. Columns without data use "-"
    placeholders so the column count stays at 7. Key column (cells[0]) is
    Ch{N} for key-based dedup.

    Column layout (split("|")[1:-1] yields exactly these cells):
        cells[0] = Ch{N}     (key)
        cells[1..5] = "-"    (placeholder dimensions)
        cells[6] = {overall} (7th column — what parse_resonance_scores reads)
    """
    return f"| Ch{chapter} | - | - | - | - | - | {overall} |"
```

Then wire the persistence into the chapter loop. After `cs.resonance_score` is assigned (around `chapter_loop.py:1431`, where `_parse_resonance_score` is already called) and after `_route_revision_after_resonance` (~line 1438):

```python
# Persist to resonance_trend.md as a MARKDOWN TABLE ROW (not YAML).
# _parse_resonance_score (chapter_loop.py:667) already ran and stored the
# overall int in cs.resonance_score. Reuse it — do NOT re-parse.
overall = cs.resonance_score  # int | None
if overall is not None:
    from shenbi.pipeline.truth_io import write_truth_file
    trend_row = _build_resonance_trend_row(chapter, overall)
    write_truth_file(
        project_dir, "resonance_trend.md", trend_row,
        mode="upsert_markdown_row",
        key_field="chapter",  # dedup on first column (Ch{N})
    )
    log.info("resonance_score_persisted", chapter=chapter, overall=overall)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_resonance_persistence.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_resonance_persistence.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: persist resonance score to resonance_trend.md reusing existing parser"
```

---

### Task 5: Fix Style-Learning Trigger Execution (Self-Heal + Failure Visibility) — System Already Exists

**Files:**
- Modify: `src/shenbi/pipeline/triggers.py` (`check_triggers` ~line 401, `run_triggered_skills` ~line 503)
- Audit: `src/shenbi/pipeline/cli.py` (~line 214, trigger invocation on resume)
- Test: `tests/unit/pipeline/test_style_learning_self_heal.py`

**Interfaces:**
- Consumes: existing `TRIGGER_STEPS`, `check_triggers`, `run_triggered_skills` in `triggers.py`
- Produces: `_style_profile_is_stale()` self-heal check added to `check_triggers`; `state.last_trigger_failure` recorded in `run_triggered_skills`

**Critical correction (from spec §3.5):** The style-learning trigger system ALREADY EXISTS and is fully wired in `triggers.py` (NOT `chapter_loop.py`/`CHAPTER_STEPS`):
- `TRIGGER_STEPS` has TWO `shenbi-style-learning` entries: periodic (lines 176-181, `category="style_learning"`) and volume-boundary (lines 213-217, `category="volume_boundary"`).
- `check_triggers` (`triggers.py:401`) sets `r.style_learning = True` at `chapter % STYLE_INTERVAL == 0` (line 418, `STYLE_INTERVAL = 12`) and at volume boundaries (line 431).
- `run_triggered_skills` (`triggers.py:503`) dispatches each triggered skill and runs G4.
- This is invoked from `cli.py` (not `chapter_loop.py`) after each chapter completes.

The real bug is NOT a missing trigger — the trigger fires but the result is not persisted, and failures are silently swallowed. DO NOT add a parallel trigger in `chapter_loop.py` — that would conflict with the existing system. The fixes are: (a) surface dispatch/G4 failures into pipeline state for post-mortem, (b) add self-heal in `check_triggers` when `style_profile.md` is still bootstrap with >=3 chapters done, (c) ensure the `cli.py` invocation path is not skipped on resume.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for style-learning self-heal and failure visibility in triggers.py."""
import re
import tempfile
from pathlib import Path

from shenbi.pipeline.triggers import _style_profile_is_stale


def _write_profile(style_dir: Path, confidence: str, sample_count: int) -> Path:
    """Write a style_profile.md with the given bootstrap/mature markers."""
    style_dir.mkdir(parents=True, exist_ok=True)
    profile = style_dir / "style_profile.md"
    profile.write_text(
        f"---\ngeneration_mode: extracted\n"
        f"confidence: {confidence}\nsample_chapter_count: {sample_count}\n---\n\nbody\n"
    )
    return profile


def test_stale_when_bootstrap_and_three_or_more_chapters_done():
    """Self-heal triggers when profile is bootstrap and >=3 chapters exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in (1, 2, 3):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="low", sample_count=0)

        assert _style_profile_is_stale(project_dir) is True


def test_not_stale_when_profile_mature():
    """Self-heal does NOT trigger when profile is already mature."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in range(1, 11):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="medium", sample_count=6)

        assert _style_profile_is_stale(project_dir) is False


def test_not_stale_when_fewer_than_three_chapters():
    """Self-heal does NOT trigger when fewer than 3 chapters exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        (project_dir / "chapters" / "chapter-1.md").write_text("prose")
        _write_profile(project_dir / "style", confidence="low", sample_count=0)

        assert _style_profile_is_stale(project_dir) is False


def test_stale_when_profile_missing_entirely():
    """Self-heal triggers when no style_profile.md exists and >=3 chapters done."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "chapters").mkdir()
        for n in (1, 2, 3):
            (project_dir / "chapters" / f"chapter-{n}.md").write_text("prose")
        # No style dir / profile at all

        assert _style_profile_is_stale(project_dir) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_style_learning_self_heal.py -v`
Expected: FAIL (`ImportError: cannot import name '_style_profile_is_stale' from 'shenbi.pipeline.triggers'`)

- [ ] **Step 3: Write minimal implementation**

Add the self-heal helper and failure recording to `src/shenbi/pipeline/triggers.py`. **Do NOT add any trigger logic to `chapter_loop.py`.**

```python
# In src/shenbi/pipeline/triggers.py

import re
from pathlib import Path


def _style_profile_is_stale(project_dir: Path) -> bool:
    """True if style_profile.md is still bootstrap mode with >=3 chapters done.

    Used by check_triggers() for self-heal: when the periodic/volume trigger
    did not fire (or fired but failed to persist), and the profile is still in
    bootstrap mode, force r.style_learning = True on the next check so the
    profile gets refreshed.
    """
    # Count completed chapters on disk
    chapters_dir = project_dir / "chapters"
    if not chapters_dir.exists():
        return False
    chapter_count = len(list(chapters_dir.glob("chapter-*.md")))
    if chapter_count < 3:
        return False

    profile = project_dir / "style" / "style_profile.md"
    if not profile.exists():
        return True  # No profile at all despite >=3 chapters

    text = profile.read_text(encoding="utf-8")
    # Bootstrap markers (match either YAML frontmatter or prose form)
    is_bootstrap = (
        "confidence: low" in text
        or "Generation mode: Seed" in text
        or "generation_mode: seed_fingerprint" in text
    )
    sample_count_match = re.search(r"[Ss]ample.{0,20}count.{0,5}(\d+)", text)
    sample_count = int(sample_count_match.group(1)) if sample_count_match else 0
    return is_bootstrap and sample_count == 0
```

Then, in `check_triggers` (~line 401, just before `return r`), add the self-heal:

```python
# In check_triggers(), before the final return r:
# Self-heal: if style profile is still bootstrap with >=3 chapters done,
# force the style_learning trigger even when the periodic/volume condition
# did not fire. This recovers from cases where the trigger ran but failed
# to persist (handled by run_triggered_skills failure visibility below).
if not r.style_learning and _style_profile_is_stale(project_dir):
    log.warning("style_learning_self_heal_triggered", chapter=chapter)
    r.style_learning = True
```

And in `run_triggered_skills` (~line 503, in the per-step dispatch loop), add failure visibility so dispatch/G4 failures are recorded in state instead of being silently swallowed by an unchecked return value:

```python
# In run_triggered_skills(), in the per-step loop (around the existing
# dispatch/G4 calls that currently `return False` on failure):
for step in steps:
    disp = dispatch_skill(step.skill, project_dir, prompt)
    if not disp.success:
        log.error("trigger_dispatch_failed", skill=step.skill, chapter=chapter)
        # NEW: record the failure in state for post-mortem analysis.
        # Previously the False return could be silently ignored by callers.
        state.last_trigger_failure = {
            "chapter": chapter,
            "skill": step.skill,
            "mode": getattr(step, "mode", None),
            "stage": "dispatch",
            "timestamp": _iso_now(),
        }
        return False
    # ... existing G4 check ...
    if g4_failed:
        log.error("trigger_g4_failed", skill=step.skill, chapter=chapter)
        state.last_trigger_failure = {
            "chapter": chapter,
            "skill": step.skill,
            "mode": getattr(step, "mode", None),
            "stage": "g4",
            "timestamp": _iso_now(),
        }
        return False
```

(Define `_iso_now = lambda: datetime.now(timezone.utc).isoformat()` at the top of `triggers.py` if it does not already exist; it is not a pre-existing helper in the current codebase. If the project already has a timestamp helper with a different name, use that instead.)

**Audit `cli.py` (~line 214):** Read the trigger invocation path in `cli.py` and confirm `run_triggered_skills` is NOT guarded by a `step_index == 0` or `is_at_checkpoint` condition that would skip it on resume. If such a guard exists, remove it or widen it so trigger execution runs on resume. This is a read-and-fix step against the actual code — do not assume the guard exists.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_style_learning_self_heal.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_style_learning_self_heal.py src/shenbi/pipeline/triggers.py
git commit -m "fix: add style-learning self-heal and trigger failure visibility in triggers.py"
```

---

### Task 6: Add Protagonist Presence G4 Check and Character Matrix Integrity Check

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py` (add G4.cd.protagonist_presence)
- Modify: `src/shenbi/gates/g4/state_settling.py` (add character_matrix write-protection)
- Test: `tests/unit/gates/g4/test_chapter_drafting.py` (add protagonist check test)
- Test: `tests/unit/gates/g4/test_state_settling.py` (or append to existing)

**Interfaces:**
- Consumes: Chapter prose text, protagonist name list from `characters/protagonist.md`
- Produces: G4 check result with protagonist presence verification, state_settling character_matrix rules

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/gates/g4/test_chapter_drafting.py (or create if not exists)

def test_protagonist_presence_check_detects_absence():
    """G4.cd.protagonist_presence fails when protagonist appears < 3 times."""
    from shenbi.gates.g4.chapter_drafting import _check_protagonist_presence

    text = "参数知道深度在第X层——光在场于第三日"  # No protagonist names
    protagonist_names = ["林烽", "他"]

    issues = _check_protagonist_presence(text, protagonist_names, threshold=3)
    assert len(issues) > 0
    assert "protagonist_absent" in issues[0]


def test_protagonist_presence_check_passes_with_sufficient_mentions():
    """G4 check passes when protagonist appears >= threshold."""
    from shenbi.gates.g4.chapter_drafting import _check_protagonist_presence

    text = "林烽握紧拳头。他看着前方。林烽知道这一战不可避免。他深吸一口气。"
    protagonist_names = ["林烽", "他"]

    issues = _check_protagonist_presence(text, protagonist_names, threshold=3)
    assert len(issues) == 0


def test_state_settling_character_matrix_protection():
    """state_settling prevents parameter agent names in character_matrix."""
    from shenbi.gates.g4.state_settling import _validate_character_matrix

    content = """---
update_mode: replace
---

# Character Matrix

## 角色定义
- 林烽: 主角
- 陈为民: 配角

## Ch50 State
- 冷: 参数化存在
- 光: 格式层出现
"""
    issues = _validate_character_matrix(content, known_parameter_agents=["冷", "光", "安静", "缺口"])
    assert len(issues) > 0
    assert "parameter_agent" in issues[0].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_chapter_drafting.py::test_protagonist_presence_check_detects_absence -v`
Expected: FAIL (AttributeError or NameError)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/gates/g4/chapter_drafting.py`:

```python
def _check_protagonist_presence(
    text: str,
    protagonist_names: list[str],
    threshold: int = 3,
) -> list[str]:
    """G4.cd.protagonist_presence: verify protagonist appears >= threshold times.

    Args:
        text: Chapter prose text.
        protagonist_names: List of protagonist names/pronouns to search for.
        threshold: Minimum required occurrences.

    Returns:
        List of issue strings (empty if check passes).
    """
    total = sum(text.count(name) for name in protagonist_names)
    if total < threshold:
        return [f"G4.cd.protagonist_absent: protagonist appears {total} times (threshold: {threshold})"]
    return []


# Then in the existing chapter_drafting G4 function, add:
# (Near where other chapter content checks run)
protagonist_names = _load_protagonist_names(project_dir) if project_dir else ["林烽", "他"]
issues.extend(_check_protagonist_presence(content, protagonist_names))


def _load_protagonist_names(project_dir: str) -> list[str]:
    """Load protagonist names from character design files."""
    from pathlib import Path
    names = []
    chars_dir = Path(project_dir) / "characters"
    if not chars_dir.exists():
        return ["林烽", "他"]
    protag = chars_dir / "protagonist.md"
    if protag.exists():
        text = protag.read_text(encoding="utf-8")
        import re
        import yaml
        # Try frontmatter name first
        match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        if match:
            names.append(match.group(1).strip())
        # Also try YAML frontmatter
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict) and "name" in fm:
                        names.append(str(fm["name"]))
                except Exception:
                    pass
    if not names:
        names = ["林烽", "他"]
    # Always include common pronoun
    if "他" not in names:
        names.append("他")
    return names
```

Add to `src/shenbi/gates/g4/state_settling.py`:

```python
# Known parameter-agent identifiers that must NOT appear in character_matrix
_PARAMETER_AGENT_NAMES = {"冷", "光", "安静", "缺口", "在场于", "参数", "槽位"}


def _validate_character_matrix(
    content: str,
    known_parameter_agents: set[str] | None = None,
) -> list[str]:
    """Validate that character_matrix.md does not contain parameter agents.

    Parameter agents (冷, 光, 安静, etc.) must be written to
    ``particle_ledger.md``, not to ``character_matrix.md``.

    Returns:
        List of issue strings (empty if valid).
    """
    agents = known_parameter_agents or _PARAMETER_AGENT_NAMES
    issues = []

    # Only check the content after the frontmatter, excluding the 角色定义 section
    body = content
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    # Find the 角色定义 section boundaries
    def_section = ""
    if "## 角色定义" in body:
        def_parts = body.split("## 角色定义", 1)
        if len(def_parts) > 1:
            def_section = def_parts[1].split("\n## ", 1)[0]

    for agent in agents:
        if agent in body:
            # Only flag if NOT in a legitimate context (角色定义 might reference them)
            if def_section and agent in def_section:
                # In character definitions — flag as issue. Human chars should not have
                # these names; if they do it's intentional, but parameter agents should
                # never be written into per-chapter state.
                pass
            # Check if agent appears in per-chapter state sections (not 角色定义)
            state_sections = body
            if def_section:
                state_sections = body.replace(def_section, "")
            if agent in state_sections:
                issues.append(
                    f"G4.ss.parameter_agent_in_character_matrix: {agent}"
                )

    return issues


# Integrate into existing state_settling G4 (in the main g4 function, near
# where character_matrix validation runs):
# if "character_matrix.md" in fp:
#     issues.extend(_validate_character_matrix(content))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_chapter_drafting.py -v`
Expected: PASS (all tests including the new protagonist tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/gates/g4/test_chapter_drafting.py src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/state_settling.py
git commit -m "feat: add protagonist presence G4 check and character_matrix write-protection"
```

---

### Task 7: Add Direction-Aware Filesystem Audit-Count Verification and Register Missing Audit Keys

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `_count_audits_on_disk`, direction-aware reconciliation before state save)
- Modify: `src/shenbi/pipeline/audit_layer.py` (register `resonance` and `review-summary` in the existing audit registry structures)
- Test: `tests/unit/pipeline/test_audit_count.py`

**Interfaces:**
- Consumes: Project directory filesystem, existing audit registry in `audit_layer.py`
- Produces: Direction-aware audit-count reconciliation (self-heal only when disk > recorded; flag error when disk < recorded), all 13 audit types tracked

**Direction matters (from spec §3.6):** Self-heal only when disk has MORE audits than recorded (a missed count — safe to auto-correct). When disk has FEWER than recorded (possible data loss or gate bypass), do NOT silently overwrite — set an anomaly flag and log an error for investigation.

**Audit registry structure (from spec §3.7):** The codebase has NO single `AUDIT_TYPES` constant. Audit routing is split across three structures in `audit_layer.py`: `GENRE_ACTIVATION_MATRIX` (lines 44-54), `_CORE_CIRCLE_KEYS` (lines 57-67), and `BOUNDARY_TRIGGERS` (lines 76-81). The missing audit types `resonance` and `review-summary` are not registered in any of these. Add them to `_CORE_CIRCLE_KEYS` (or a new `_SPECIAL_AUDIT_KEYS` set if they don't fit the core-circle model). Do NOT invent a standalone `_get_expected_audit_types()` list that does not correspond to any existing code.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_audit_count.py
"""Tests for direction-aware filesystem-verified audit counting."""
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _count_audits_on_disk, _reconcile_audit_count


def test_count_audits_on_disk_correct_count():
    """Count matches actual files on disk."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        audit_dir = project_dir / "audits"
        audit_dir.mkdir(parents=True)

        # Create 7 audit files for chapter 5
        for name in ["resonance", "drift", "quality", "foreshadowing",
                      "hook", "character", "pacing"]:
            (audit_dir / f"chapter-5-{name}.md").write_text("# audit")

        count = _count_audits_on_disk(project_dir, chapter=5)
        assert count == 7


def test_count_audits_on_disk_returns_zero_when_no_audits():
    """Returns 0 when audit directory exists but has no matching files."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        audit_dir = project_dir / "audits"
        audit_dir.mkdir(parents=True)

        count = _count_audits_on_disk(project_dir, chapter=5)
        assert count == 0


def test_count_audits_on_disk_returns_zero_when_dir_missing():
    """Returns 0 when audit directory does not exist."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        count = _count_audits_on_disk(project_dir, chapter=5)
        assert count == 0


def test_count_audits_on_disk_does_not_count_other_chapters():
    """Only counts files for the specified chapter."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        audit_dir = project_dir / "audits"
        audit_dir.mkdir(parents=True)

        (audit_dir / "chapter-5-resonance.md").write_text("# audit")
        (audit_dir / "chapter-6-resonance.md").write_text("# audit")

        count = _count_audits_on_disk(project_dir, chapter=5)
        assert count == 1


def test_reconcile_self_heals_when_disk_has_more():
    """When disk has MORE audits than recorded, self-heal the count."""
    result = _reconcile_audit_count(recorded=3, actual=7)
    assert result.new_count == 7        # self-healed up
    assert result.anomaly is False      # not an anomaly — safe direction


def test_reconcile_flags_error_when_disk_has_fewer():
    """When disk has FEWER audits than recorded, flag anomaly — do NOT overwrite."""
    result = _reconcile_audit_count(recorded=7, actual=3)
    assert result.new_count == 7        # NOT overwritten — preserved as-is
    assert result.anomaly is True       # flagged for investigation


def test_reconcile_no_change_when_matching():
    """When counts match, no change and no anomaly."""
    result = _reconcile_audit_count(recorded=5, actual=5)
    assert result.new_count == 5
    assert result.anomaly is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_audit_count.py -v`
Expected: FAIL (`ImportError: cannot import name '_count_audits_on_disk'`)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
from dataclasses import dataclass


@dataclass
class AuditCountReconciliation:
    """Result of reconciling a recorded audit count against the filesystem."""
    new_count: int
    anomaly: bool


def _count_audits_on_disk(project_dir: Path, chapter: int) -> int:
    """Count actual audit files on disk for a specific chapter.

    Counts files matching ``chapter-{chapter}-*.md`` in the ``audits/``
    directory. Returns 0 if the directory does not exist or has no matches.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number to count audits for.

    Returns:
        Number of audit files on disk.
    """
    audit_dir = project_dir / "audits"
    if not audit_dir.exists():
        return 0
    return len(list(audit_dir.glob(f"chapter-{chapter}-*.md")))


def _reconcile_audit_count(*, recorded: int, actual: int) -> AuditCountReconciliation:
    """Reconcile a recorded audit count against the filesystem, direction-aware.

    Direction matters (spec §3.6):
    - disk > recorded  -> safe direction (missed count): self-heal to actual.
    - disk < recorded  -> unsafe direction (possible data loss or gate bypass):
      do NOT overwrite; preserve recorded and set anomaly flag for investigation.
    - disk == recorded -> no change.

    Args:
        recorded: The audit count currently stored in pipeline state.
        actual: The audit count observed on disk.

    Returns:
        Reconciliation result with the count to store and an anomaly flag.
    """
    if actual > recorded:
        log.warning("audit_count_undercount", recorded=recorded, actual=actual)
        return AuditCountReconciliation(new_count=actual, anomaly=False)
    if actual < recorded:
        log.error("audit_count_overcount", recorded=recorded, actual=actual)
        return AuditCountReconciliation(new_count=recorded, anomaly=True)
    return AuditCountReconciliation(new_count=recorded, anomaly=False)
```

Then integrate into the state-save path (around the existing state-save in `_advance`, after `_record_step_done`):

```python
# Direction-aware reconciliation before state save
chapter = state.chapter_loop.current_chapter
ch_state = _get_chapter_state(state, chapter)
if ch_state:
    recorded = getattr(ch_state, "audit_count", 0)
    actual = _count_audits_on_disk(project_dir, chapter)
    rec = _reconcile_audit_count(recorded=recorded, actual=actual)
    ch_state.audit_count = rec.new_count
    if rec.anomaly:
        ch_state.audit_count_anomaly = True  # flag for investigation
```

In `src/shenbi/pipeline/audit_layer.py`, register the missing audit keys into the existing registry structure. Read the file first to confirm whether `resonance`/`review-summary` fit `_CORE_CIRCLE_KEYS` (lines 57-67) or need a new `_SPECIAL_AUDIT_KEYS` set:

```python
# In audit_layer.py, extend the existing _CORE_CIRCLE_KEYS set (lines 57-67)
# to include the two previously-untracked audit types. If they do not fit the
# core-circle model semantically, add a sibling set instead and ensure both
# are included wherever the total audit-type count is computed.
_CORE_CIRCLE_KEYS = {
    "antiAi", "character", "pacing", "continuity",
    "foreshadowing", "memoCompliance", "pov",
    # Newly registered (previously missing — spec §3.7):
    "resonance", "review-summary",
}
```

(Adjust the exact set name and insertion point to match what `grep` finds in `audit_layer.py` at execution time. The key requirement: both `resonance` and `review-summary` must be counted in the pipeline-state audit tallies.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_audit_count.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_audit_count.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/audit_layer.py
git commit -m "feat: direction-aware filesystem audit-count verification and register missing audit keys"
```

---
