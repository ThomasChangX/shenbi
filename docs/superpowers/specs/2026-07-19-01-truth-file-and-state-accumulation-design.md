# Spec 1: Truth File and State Accumulation Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical
> **Consolidated from:**
> - `2026-07-17-fix-truth-file-overwrite-pattern-design.md` (CN3)
> - `2026-07-17-fix-protagonist-disappearance-design.md` (CN1)
> - `2026-07-17-fix-hook-system-bifurcation-design.md`
> - `2026-07-17-fix-resonance-score-null-design.md`
> - `2026-07-17-fix-style-learning-never-updated-design.md`
> - `2026-07-17-fix-pipeline-state-stale-data-design.md`

---

## 1. Executive Summary

The shenbi pipeline's truth-file system (the L1-L2 memory layer of the 6-layer memory hierarchy) is fundamentally broken in production. Five accumulation-style truth files contain only the last chapter's data instead of the full 56-chapter history. This single root cause cascades into six distinct failure modes: resonance trend analysis is useless, the hook/foreshadowing economy is non-functional, protagonist presence cannot be tracked, style learning never updates, and pipeline state audit counts are stale.

**Root cause (refined after codebase verification):** The `state-settling` skill's prompt **does** mandate incremental append-only updates (iron-rule #4: "增量更新 — 追加变更，不重写整个文件"). However, this is a **prompt-only guardrail with zero programmatic enforcement**. The dispatch write path (`dispatch_helper.py:294-323` `_write_parsed_outputs`) parses `### FILE:` blocks from the agent's response and calls `safe_write(full_path, content)` for each — and the agent is instructed to emit each file in full (prompt: "complete file content"). Since `safe_write` (`safe_write.py:108`) uses `os.replace` for atomic overwrite, any agent that emits a full file (even when told not to) silently destroys accumulated history. There is no distinction between replace-mode files (current snapshots) and append-mode files (cumulative histories), and no post-write verification that accumulation files actually grew.

**Impact scope:** All 7 truth files have identical last-modified timestamps (21:17:47) indicating batch overwrite, not incremental append. The entire memory system produces only Chapter 55/56 data -- 54 chapters of history are destroyed.

---

## 2. Root Cause Analysis (Per-Source-Spec Breakdown)

### 2.1 Truth File Overwrite Pattern (CN3)

**Discovery (D18-D20):** Audit of `novel-output/xinghuo-ranqiong/truth/` revealed:

| Truth File | Expected | Actual | Mode |
|-----------|----------|--------|------|
| `resonance_trend.md` | 55-56 rows | 1 row (Ch55) | Overwrite |
| `audit_drift.md` | 55-56 sections | 1 section (Ch55) | Overwrite |
| `emotional_arcs.md` | 56 chapter entries | Ch55-56 only | Overwrite |
| `chapter_summaries.md` | 56 chapter refs | 1 chapter | Overwrite |
| `pending_hooks.md` | 56 chapters of hooks | Ch55-56 only | Overwrite |
| `character_matrix.md` | 56 chapter states | Last chapter snapshot | Overwrite |
| `current_state.md` | Chapter snapshot | Last chapter | Overwrite |

**Direct cause:** The `state-settling` skill prompt mandates incremental append (iron-rule #4), but this is a **prompt-only guardrail with no programmatic enforcement**. The dispatch write path (`dispatch_helper.py:294-323` `_write_parsed_outputs`) instructs the agent to emit "complete file content" and then calls `safe_write` (overwrite) for each `### FILE:` block. When the LLM obeys the emit-full-file instruction over the append-only rule, the full file overwrites accumulated history. The underlying `safe_write` (`src/shenbi/safe_write.py:108`) uses `os.replace` for atomic overwrite -- there is no append capability and no read-merge-write path for accumulation files.

**Important nuance (verified):** Not all 7 files are equally affected. `pending_hooks.md` has a **dual-writer architecture**: the deterministic `hook_planting.py:204-276` (`_append_to_pending_hooks`) correctly reads frontmatter YAML, deduplicates by hook `id`, merges, and writes back — so the structured `hooks` array accumulates properly. However, the markdown **body** is overwritten by the LLM `foreshadowing-track`/`state-settling` path. So the spec's claim should be refined: the structured hooks list accumulates; the prose body history is lost.

**Why this went undetected:** No post-write verification checked whether truth files had grown or shrunk. No row-count assertion existed in G4 validation for accumulation-mode files. The G4 `state_settling.py` checker (113 lines) only verifies content presence via regex heading checks (`## 角色`/`## 人物`) — it never inspects HOW the file was written or whether prior content was preserved.

### 2.2 Protagonist Disappearance (CN1)

**Discovery (Agent 1 Audit 3):** Protagonist Lin Feng disappears from text starting Ch35:

| Dimension | Ch1-10 | Ch20 | Ch35 | Ch50 |
|-----------|--------|------|------|------|
| Human dialogue | Present | Absent (solo chapter) | **Absent** | **Absent** |
| Physical action | Present | Present (parameterized) | **Absent** | **Absent** |
| Inner monologue | Present | Present | **Absent** | **Absent** |
| Name "林烽" | Appears | Appears | **Absent** | **Absent** |

**Direct cause:** `character_matrix.md` is overwritten each chapter by the state-settling dispatch path. Parameter agents ("冷", "光", "安静", "缺口") are written into `character_matrix.md` as if they were characters, forming a self-reinforcing parameter-character system. Verified evidence: the live `character_matrix.md` opens with a `## 参数角色定位` table listing 11 parameter agents but NO human protagonist (林烽), whereas the early-stage fixture `tests/fixtures/truth-character_matrix.md` (lines 19-39) properly defines 林烽 with a full character table. The human role definitions declared in `characters/protagonist.md` are erased after each overwrite cycle.

**Aggravating factor:** Parameter agents are **duplicated** into BOTH `character_matrix.md` AND `particle_ledger.md` (which already exists and already tracks parameter state). The defect is not the absence of `particle_ledger.md` — it exists — but the leak/duplication into `character_matrix.md` where human characters should be authoritative.

**Result:** Approximately 21 chapters (Ch35-56, 37.5%) contain zero human protagonist presence. The declared character relationships (Chen Weimin, Zhao Tiezhu, Chu Yunlan, etc.) never appear.

### 2.3 Hook System Bifurcation (CN2)

**Discovery (Agent 1 Audit 2 + D4):**

- `pending_hooks.md` uses non-standardized format (zero MH-xxx/PO-xxx IDs)
- 12 MH-xxx IDs referenced in chapter META blocks (MH-001 through MH-028)
- Starting Ch42, the hook system silently switches from MH-xxx to P0-xx with no mapping
- `book_spine.md` shows 6 main hooks (MH01-MH06) all at 0% progress
- `foreshadowing-plant/track/recall` skills ran on all 56 chapters but their output was never structurally appended to `pending_hooks.md`

**Dual root cause:**
1. `foreshadowing-plant` is replaced in the pipeline by deterministic `hook_planting.py` (`chapter_loop.py:1189-1194`), which correctly appends to the frontmatter `hooks` array with ID-based dedup. However, `foreshadowing-track` (LLM path) and `state-settling` emit the full markdown body, and the dispatch write path overwrites it — so the per-chapter tracking prose history is lost even though structured hook data accumulates.
2. The markdown body of `pending_hooks.md` is overwritten each chapter by the LLM dispatch path, destroying historical tracking prose. (The frontmatter hooks array survives via the deterministic plant path.)

**Result:** The entire foreshadowing economy (one of shenbi's core design advantages) is completely non-functional. No hook lifecycle tracking (PLANTED -> RELEVANT -> TRIGGERED -> RESOLVED) occurs.

**Hook ID scheme inconsistency (verified):** The codebase has multiple ID regex patterns that don't agree:
- `hook_planting.py:144`: `re.match(r"^(MH|H)-", cells[0])` — expects `MH-xxx` or `H-xxx` (with hyphen)
- `truth_index.py:30`: `_HOOK_ID_RE = re.compile(r"[HM]\d+")` — matches `H01`, `M01` (no hyphen, no prefix combo)
- Production data: `MH-001` through `MH-028` in chapter META blocks, `P0-xx` starting Ch42, `MH01-MH06` in book_spine.md

A prompt update to the LLM track skill cannot fix a deterministic ID-generation inconsistency. The fix must standardize the canonical ID format across `hook_planting.py` (generation), `truth_index.py` (indexing), and production data (migration if needed).

### 2.4 Resonance Score Null (CN4)

**Discovery (Agent 3 Section 6):**

- All 56 chapters have `resonance_score: null`
- `resonance_trend.md` contains only a single Ch55 entry of 70/100
- `shenbi-review-resonance` passes G4 gates but scores are never stored

**Direct cause:** The resonance audit report (`audits/chapter-N-resonance.md`) contains a detailed scoring table. Two parsers already exist in the codebase — `_parse_resonance_score` (`chapter_loop.py:667`, reads the per-chapter report) and `parse_resonance_scores` (`escalation_bridge.py:10`, reads `resonance_trend.md`) — but **neither writes** to `resonance_trend.md` or persists scores durably. The orchestrator stores the parsed score only in in-memory state (`cs.resonance_score` at `chapter_loop.py:1431`), then calls `_route_revision_after_resonance` (`chapter_loop.py:1021`) which only logs a warning if below floor. Maintenance of `resonance_trend.md` is delegated entirely to the `shenbi-review-resonance` LLM skill (SKILL.md lines 141-145: "趋势（写入 resonance_trend）...追加行"), but since that skill's output goes through the overwrite dispatch path, the trend file never accumulates. Missing links:
1. G4 checks resonance report format (detail_table, verdict, evidence) but never extracts scores.
2. `_route_revision_after_resonance` (`chapter_loop.py:1021`) reads the in-memory score but never persists it to the trend file.
3. Even in the single case where a score exists (Ch55 value 70), it is only present because the LLM happened to emit it during that chapter's overwrite -- it was never accumulated.

**Result:** The entire scoring system is non-functional. No chapter quality trend tracking. No score-based revision routing.

### 2.5 Style Learning Never Updated (CN5)

**Discovery (D12):** `style/style_profile.md` state:

- **Generation mode:** Seed fingerprint (bootstrap)
- **Confidence:** low
- **Sample chapter count:** 0
- **Sample total characters:** 0
- **All statistics:** "Inferred values"
- First formal extraction should trigger after 3 chapters -- never triggered
- Periodic update (every 12 chapters) -- never triggered
- **56 chapters generated, zero style profile updates**

**Direct cause (verified — trigger system EXISTS but may not execute):** The style-learning trigger system is NOT missing — it is fully wired through a dedicated trigger module, NOT `chapter_loop.py`/`CHAPTER_STEPS`:

1. `src/shenbi/pipeline/triggers.py` defines `TRIGGER_STEPS` with TWO entries for `shenbi-style-learning`: a periodic entry (lines 176-181, `category="style_learning"`) and a volume-boundary entry (lines 213-217, `category="volume_boundary"`).
2. `check_triggers` (`triggers.py:401`) sets `r.style_learning = True` at `chapter % STYLE_INTERVAL == 0` (line 418, `STYLE_INTERVAL = 12`) and at volume boundaries (line 431).
3. `run_triggered_skills` (`triggers.py:503`) dispatches each triggered skill and runs G4.
4. This is invoked from `cli.py` (not `chapter_loop.py`) after each chapter completes.

The real bug is therefore NOT a missing trigger — it is that the trigger fires but the result is not persisted. Likely failure points:
- `run_triggered_skills` returns `False` on dispatch/G4 failure (line 562, 573) and the caller silently continues.
- Resume after checkpoint/interrupt: `cli.py`'s trigger invocation may be guarded by a `step_index == 0` or `is_at_checkpoint` condition that skips trigger execution on resume.
- The style-learning skill output goes through the overwrite dispatch path, so even if it runs, the output may not accumulate correctly.

**Fix direction:** Do NOT add a parallel trigger in `chapter_loop.py`. Instead: (a) add logging/assertion in `run_triggered_skills` to detect dispatch/G4 failures, (b) add self-heal on resume — if `style_profile.md` is still bootstrap mode and >= 3 chapters are completed, force `r.style_learning = True` on the next `check_triggers` call, (c) ensure the trigger invocation path in `cli.py` is not skipped on resume.

**Result:** Style drift detection (see Spec 4 / Context Persistence and Linguistic Drift Prevention) loses its baseline reference. All 56 chapters of style evolution are untracked. This is a key root cause of why prose collapse went undetected.

### 2.6 Pipeline State Stale Data (CN6)

**Discovery (Agent 3 Section 5):**

- Pipeline state reports 11 audit types, but `audits/chapter-N-*.md` actually has 13 types on disk
- `resonance.md` and `review-summary.md` are never recorded in state
- Ch56: pipeline state reports 0 audits, but 7 audit files exist on disk

**Direct cause:** Audit counts in `pipeline-state.json` are updated by code logic rather than verified against the filesystem. The audit type registry in `audit_layer.py` uses three structures — `GENRE_ACTIVATION_MATRIX` (lines 44-54, maps genre dimensions to review skills), `_CORE_CIRCLE_KEYS` (lines 57-67, core-circle audit keys: antiAi, character, pacing, continuity, foreshadowing, memoCompliance, pov), and `BOUNDARY_TRIGGERS` (lines 76-81, long-span/arc-payoff/spinoff/chapter-pattern). Missing audit types (`resonance.md`, `review-summary.md`) are not registered in any of these. The state-update logic increments counters programmatically but never cross-checks with actual disk files.

**Result:** Pipeline state is untrustworthy -- resume may skip completed steps or re-execute them. Failed resume logic compounds other failures.

---

## 3. Unified Fix Strategy

### 3.1 Distinguish Replace-Mode vs Append-Mode Truth Files

Introduce an `update_mode` field in truth file frontmatter metadata to declare whether a file is a snapshot (replace) or a cumulative history (append).

**Replace-mode files (snapshot type):**
- `current_state.md` -- current chapter snapshot
- `character_matrix.md` -- character state snapshot (but see 3.3 for write-protection)
- `current_focus.md` -- focus snapshot

**Append-mode files (cumulative type):**
- `resonance_trend.md` -- per-chapter resonance scores
- `audit_drift.md` -- per-chapter drift audit results
- `emotional_arcs.md` -- per-chapter emotional arc entries
- `chapter_summaries.md` -- per-chapter summary references
- `pending_hooks.md` -- per-chapter hook/foreshadowing data

**Frontmatter convention:**
```yaml
---
update_mode: upsert_markdown_row    # or: replace, upsert_yaml
chapter_key: "Ch{{n}}"
---
```

### 3.2 Implement `write_truth_file()` Utility with Key-Based Upsert Capability

Create a dedicated truth-file write utility that respects the `update_mode` field. Location: new module `src/shenbi/pipeline/truth_io.py` (alongside `truth_index.py`).

**Critical design lesson from the codebase itself:** The existing `truth_index.py` (Route A) explicitly abandoned substring matching in favor of structured-key matching (module docstring: "the broken approach" → canonical names from structured truth files). The proposed substring-based idempotency (`if new_content.strip() not in existing`) repeats that known-broken pattern: LLM-generated prose is never byte-identical across runs, causing both false negatives (trivial whitespace diffs defeat the check → duplicate rows) and false positives (short new sections that are substrings get silently dropped). The codebase already has a correct implementation in `hook_planting.py:204-276` (`_append_to_pending_hooks`): read structured data (YAML frontmatter), deduplicate by stable key (`id`), merge, write back. `write_truth_file()` should generalize this pattern.

```python
# truth_io.py (new file, alongside src/shenbi/pipeline/truth_index.py)

from __future__ import annotations
import re
from pathlib import Path
from shenbi.safe_write import safe_write

# Natural key per accumulation file — determines dedup identity
# Two serialization formats:
#   - "yaml": YAML frontmatter list[dict] (hooks, structured records)
#   - "markdown_table": | row | row | markdown table (trend files, read by
#     escalation_bridge.py:15-17 which splits on "|" and reads cells[6])
_ACCUM_REGISTRY: dict[str, tuple[str, str, int]] = {
    # filename: (format, key_field, key_column_index)
    # key_column_index = 0-based index of the key column in markdown rows
    "resonance_trend.md":  ("markdown_table", "chapter", 0),
    "audit_drift.md":      ("markdown_table", "chapter", 0),
    "emotional_arcs.md":   ("markdown_table", "chapter", 0),
    "chapter_summaries.md":("markdown_table", "chapter", 0),
    "pending_hooks.md":    ("yaml",           "id",      None),
}

def write_truth_file(
    project_dir: Path,
    filename: str,
    new_data: str | list[dict],  # str for markdown_table mode, list[dict] for yaml
    *,
    mode: str = "replace",       # replace | upsert_yaml | upsert_markdown_row
    key_field: str | None = None,
) -> None:
    """Write to a truth file, respecting update_mode.

    Modes:
    - replace: atomic overwrite via safe_write (snapshot files)
    - upsert_yaml: read existing YAML records, dedup by key_field, merge,
      re-serialize, write (structured data like hooks)
    - upsert_markdown_row: read existing markdown table rows, dedup by key
      column, merge new row, write (trend files read by escalation_bridge)

    Idempotency is based on natural keys (chapter number, hook id), NOT
    substring matching — see truth_index.py design lesson.

    CRITICAL: For markdown_table files, the output format MUST match what
    downstream readers expect. E.g., escalation_bridge.py:15-17 parses
    lines starting with "|", splits on "|", requires >=7 cells, reads
    cells[6] as the overall score. Producing YAML here would silently
    break escalation routing.
    """
    path = project_dir / "truth" / filename

    if mode == "upsert_markdown_row":
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        merged = _upsert_markdown_table_row(existing, new_data, key_field or "chapter")
        safe_write(path, merged)
    elif mode == "upsert_yaml":
        if key_field is None:
            key_field = _ACCUM_REGISTRY.get(filename, ("yaml", "chapter", None))[1]
        existing_records = _read_yaml_records(path)
        merged = _upsert_by_key(existing_records, new_data, key_field)
        content = _serialize_yaml_records(merged, filename)
        safe_write(path, content)
    else:  # replace
        safe_write(path, new_data if isinstance(new_data, str) else _serialize_yaml_records(new_data, filename))

def _upsert_markdown_table_row(existing: str, new_row: str, key_name: str) -> str:
    """Dedup markdown table row by key column value.

    Extracts the key from new_row's first | cell, removes any existing
    row with the same key, appends new_row. Preserves headers and non-table
    content (frontmatter, prose).
    """
    # Extract key from new_row (first cell after |)
    new_key_match = re.match(r"\|\s*(\S+)", new_row)
    if not new_key_match:
        return existing.rstrip() + "\n" + new_row
    new_key = new_key_match.group(1)

    lines = existing.split("\n")
    result_lines = []
    for line in lines:
        if line.startswith("|"):
            existing_key_match = re.match(r"\|\s*(\S+)", line)
            if existing_key_match and existing_key_match.group(1) == new_key:
                continue  # Skip duplicate — replace with new_row
        result_lines.append(line)
    result_lines.append(new_row)
    return "\n".join(result_lines)
```

**Key design decisions:**
- **Key-based idempotency** (not substring): Dedup on a stable natural key (`chapter` for trend files, `id` for hooks). This is the proven pattern from `hook_planting.py` and aligns with `truth_index.py`'s design philosophy.
- **Structured records** (`list[dict]`): Callers pass structured data, not raw prose. The utility handles serialization. This eliminates the "LLM emits full file" problem at the API boundary — the caller never has the option to emit a full file.
- **Serialization format**: For YAML-mode files (hooks), YAML frontmatter (authoritative structured data) + markdown body (human-readable projection). This matches principle #3 in `truth-files-reference.md` (~line 21: "YAML frontmatter 权威 — 结构化数据以 YAML 为准，Markdown body 是投影"). For markdown-table files (trend files), the format is dictated by existing readers like `escalation_bridge.py:15-17` and must remain `|`-delimited table rows.
- `safe_write` remains the sole atomic write path — upsert reads, merges in memory, then writes atomically.

### 3.3 Write-Protect `character_matrix.md` Human Character Definitions

`character_matrix.md` must be partitioned into two sections:

1. **Character definitions** (human-authored, never auto-overwritten): Names, roles, relationships, arcs from `characters/protagonist.md` and other character design files.
2. **Per-chapter state** (append-only): Character appearances, state changes, emotional arc updates.

**Write-protection mechanism (preventive, not just post-hoc detection):**

Post-hoc G4 detection alone is insufficient — failing G4 sends the chapter back to revision, which will likely produce the same erasure. The write path itself must preserve the definitions section. Two-layer approach:

1. **Write-path protection (primary):** Route `character_matrix.md` writes through a custom merge function in `truth_io.py` that:
   - Reads the existing `## 角色定义` (or `## 人物`) section from the current file.
   - Reads canonical human character definitions from `characters/*.md` frontmatter (`name`, `role`, `relationships`).
   - Merges: human definitions section is re-injected from canonical source, only the per-chapter state section is updated from the skill's output.
   - Parameter agents (冷, 光, 安静, etc.) are stripped from the definitions section and redirected to `particle_ledger.md` (which already tracks them).

2. **G4 post-hoc detection (secondary safety net):** Enhance `g4_state_settling.py` to verify human character definitions persist after each write.

**Verified current state of G4 checker:** `src/shenbi/gates/g4/state_settling.py` (113 lines) is a pure content-presence checker — it only verifies a character heading regex (`## 角色`/`## 人物`) exists via `g4_state_settling`. It has NO write-protection logic, no diff/append validation, and never inspects whether prior content was preserved. This checker must be enhanced.

**Implementation — G4 `state_settling.py` (secondary safety net):**

```python
# Enhanced g4_state_settling checker — add to existing state_settling.py
# Rule: character_matrix.md "角色定义" section must retain human characters
# Parameter agents (冷, 光, 安静, etc.) belong in particle_ledger.md (which
# already exists and already tracks them) — NOT duplicated in character_matrix.md

def _check_character_matrix_integrity(path: Path, context: GateContext) -> list[Issue]:
    """Verify human character definitions persist and parameter agents don't leak."""
    issues = []
    text = path.read_text()
    # Read canonical human character names from characters/*.md frontmatter
    human_names = _load_human_character_names(context.project_dir)
    # Check at least one human character name appears in definitions section
    definitions_section = _extract_section(text, "角色定义") or _extract_section(text, "人物")
    if definitions_section and not any(n in definitions_section for n in human_names):
        issues.append(Issue(
            id="G4.ss.human_chars_erased",
            severity="error",
            message="Human character definitions erased from character_matrix.md; "
                    "only parameter agents remain",
        ))
    return issues
```

**Additionally** — add protagonist presence G4 check. Verified: `src/shenbi/gates/g4/chapter_drafting.py` (205 lines) currently has NO protagonist_presence check. It validates PRE_WRITE_CHECK, POST_WRITE_SELF_CHECK, transition-word density, fatigue words, meta-narrative, word count, content uniqueness, scene concreteness, and chapter-end hook. The new check must be added:

```python
# G4.cd.protagonist_presence check — add to chapter_drafting.py
def _check_protagonist_presence(path: Path, context: GateContext) -> list[Issue]:
    protagonist_names = _load_protagonist_names(context.project_dir)  # from characters/protagonist.md
    text = extract_prose(path)
    name_count = sum(text.count(n) for n in protagonist_names)
    if name_count < 3:
        issues.append(Issue(
            id="G4.cd.protagonist_absent",
            severity="error",
            message=f"Protagonist appears <3 times ({name_count}) in chapter",
        ))
    return issues
```

### 3.4 Persist Resonance Scores to Trend File After G4 Pass

**Reuse existing parsers — do NOT create a new one.** Two parsers already exist:
- `_parse_resonance_score` (`chapter_loop.py:667`) — reads the per-chapter audit report, returns overall score. Already called at line 1431 and stored in `cs.resonance_score`.
- `parse_resonance_scores` (`escalation_bridge.py:10-24`) — reads `resonance_trend.md` as a **markdown table**: scans lines starting with `|`, splits on `|`, requires `len(cells) >= 7`, reads `cells[6]` (7th column = overall score). Returns `list[float]`.

**Critical format constraint:** The existing reader (`escalation_bridge.py:15-17`) parses markdown table rows (`|`-delimited, 7+ columns, column 7 = overall). The writer MUST produce this exact format — NOT YAML frontmatter. If the `write_truth_file` upsert produces YAML records, `parse_resonance_scores` returns `[]` and escalation silently breaks.

The missing piece is purely the **write/persistence step**. After `_parse_resonance_score` succeeds and the score is stored in `cs.resonance_score` (line 1431), persist it to `resonance_trend.md` as a markdown table row via key-based upsert:

```python
# In chapter_loop.py, after line 1431 (cs.resonance_score = _parse_resonance_score(...))
# and after _route_revision_after_resonance (line 1438)

# Persist to resonance_trend.md as a MARKDOWN TABLE ROW (not YAML)
# Format must match what parse_resonance_scores (escalation_bridge.py:15-17) reads:
#   | Ch{N} | {role} | {dim1} | {dim2} | ... | {overall} | {confidence} |
# Key-based dedup on chapter number column (cells[0])

# Note: _parse_resonance_score (chapter_loop.py:667) returns int|None (overall score only).
# For the markdown-table format that escalation_bridge.py reads, we need 7 columns.
# Populate what we have; use placeholders for missing dimensions.
# If per-dimension scores are needed in the future, extend _parse_resonance_score.

overall = cs.resonance_score  # int|None, already parsed at line 1431
if overall is None:
    return  # skip persistence if no score

# Simplified 7-column row matching escalation_bridge.py:15-17 format
# (column 7 = overall score, which is all the reader extracts)
trend_row = f"| Ch{chapter} | - | - | - | - | {overall} | - |"
write_truth_file(
    project_dir, "resonance_trend.md",
    trend_row,
    mode="upsert_markdown_row",
    key_field="chapter",       # dedup on first column (Ch{N})
)
```

**Note on `write_truth_file` modes:** The utility (section 3.2) must support both structured-record upsert (YAML-keyed, for hooks) and markdown-row upsert (table-row-keyed, for trend files). For markdown-row files, dedup works by parsing the key column from each `|`-delimited row and matching against the new record's key.

### 3.5 Fix Style-Learning Trigger Execution (NOT Add New Triggers)

**The trigger system already exists** in `triggers.py` (verified): `TRIGGER_STEPS` has two `shenbi-style-learning` entries (periodic at lines 176-181, volume-boundary at 213-217), `check_triggers` fires at `chapter % 12 == 0` and volume boundaries, and `run_triggered_skills` executes them. Do NOT add a parallel trigger in `chapter_loop.py` — that would conflict with the existing system.

**Fix strategy — diagnose why triggers fire but produce no updates:**

```python
# In triggers.py run_triggered_skills() — add failure visibility
# Currently (line 550-562): dispatch failure -> log.error -> return False
# The caller may not check the return value, silently swallowing the failure.

# Fix 1: Surface trigger failures to pipeline state
def run_triggered_skills(state, project_dir, chapter, result) -> bool:
    # ... existing dispatch loop ...
    for step in steps:
        disp = dispatch_skill(step.skill, project_dir, prompt)
        if not disp.success:
            log.error("trigger_dispatch_failed", ...)
            # NEW: Record failure in state for post-mortem
            state.last_trigger_failure = {
                "chapter": chapter,
                "skill": step.skill,
                "mode": step.mode,
                "timestamp": _iso_now(),
            }
            return False
    # ...

# Fix 2: Self-heal on resume — in cli.py or check_triggers
def check_triggers(state, chapter, total_chapters) -> TriggerResult:
    r = TriggerResult()
    # ... existing trigger logic ...

    # NEW: Self-heal — if style profile is stale, force trigger
    if not r.style_learning and _style_profile_is_stale(state.project_dir):
        log.warning("style_learning_self_heal_triggered", chapter=chapter)
        r.style_learning = True
    return r

def _style_profile_is_stale(project_dir: Path) -> bool:
    """True if style_profile.md is still bootstrap mode with >=3 chapters done."""
    profile = project_dir / "style" / "style_profile.md"
    if not profile.exists():
        return False
    text = profile.read_text()
    is_bootstrap = ("confidence: low" in text or "Generation mode: Seed" in text)
    sample_count_match = re.search(r"[Ss]ample.{0,20}count.{0,5}(\d+)", text)
    sample_count = int(sample_count_match.group(1)) if sample_count_match else 0
    if is_bootstrap and sample_count == 0:
        # Check how many chapters exist on disk
        chapter_count = len(list((project_dir / "chapters").glob("chapter-*.md")))
        return chapter_count >= 3
    return False
```

**Additional fix:** Audit `cli.py` trigger invocation path (around line 214) to ensure trigger execution is NOT skipped on resume after checkpoint/interrupt. The likely culprit is a `step_index == 0` or `is_at_checkpoint` guard that bypasses `run_triggered_skills` on resume.

### 3.6 Fix Pipeline-State Audit Count via Filesystem Verification + Self-Heal

Add a filesystem-verified audit counter before state save. Self-heal direction matters — only auto-correct when disk has MORE audits than recorded (missed count, safe). When disk has FEWER (possible data loss), flag as error, do NOT silently overwrite:

```python
def _count_audits_on_disk(project_dir: Path, chapter: int) -> int:
    """Count actual audit files on disk for a chapter."""
    audit_dir = project_dir / "audits"
    return len(list(audit_dir.glob(f"chapter-{chapter}-*.md")))

# Before state save (chapter_loop.py, near state persistence)
actual_audits = _count_audits_on_disk(project_dir, chapter)
if actual_audits != recorded_audits:
    if actual_audits > recorded_audits:
        # Safe direction: disk has more — we missed counting some
        logger.warning("audit_count_undercount", chapter=chapter,
                       recorded=recorded_audits, actual=actual_audits)
        ch_state['audit_count'] = actual_audits  # self-heal
    else:
        # Unsafe direction: disk has fewer — possible data loss or gate bypass
        logger.error("audit_count_overcount", chapter=chapter,
                     recorded=recorded_audits, actual=actual_audits)
        # Do NOT self-heal — flag for investigation
        ch_state['audit_count_anomaly'] = True
```

### 3.7 Register Missing Audit Types in Audit Registry

The codebase has no single `AUDIT_TYPES` constant. Instead, audit routing is split across three structures in `audit_layer.py`: `GENRE_ACTIVATION_MATRIX` (lines 44-54), `_CORE_CIRCLE_KEYS` (lines 57-67), and `BOUNDARY_TRIGGERS` (lines 76-81). Ensure `resonance.md` and `review-summary.md` are tracked by adding them to `_CORE_CIRCLE_KEYS` (or a new `_SPECIAL_AUDIT_KEYS` set if they don't fit the core-circle model), so they are counted in pipeline state audit tallies.

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/safe_write.py:108` | Reference only | `os.replace` is the atomic write mechanism; no code change needed, but upsert-mode callers must read-merge-write before calling `safe_write` |
| `src/shenbi/pipeline/truth_io.py` (NEW) | New module with `write_truth_file()` | Key-based upsert truth file writer — NOT substring matching (see truth_index.py design lesson) |
| `src/shenbi/pipeline/dispatch_helper.py:294-323` (`_write_parsed_outputs`) | Add upsert routing | Route append-mode truth file writes through `write_truth_file(mode="upsert")` instead of raw `safe_write` |
| `skills/shenbi-state-settling/SKILL.md` | Prompt + contract update | Instruct LLM to output only new chapter records for append-mode files; add `update_mode` to truth file frontmatter convention |
| `skills/shenbi-state-settling/truth-files-reference.md` | Add `update_mode` field documentation | Distinguish replace vs append truth files in the reference |
| `src/shenbi/pipeline/chapter_loop.py:1427-1438` (after resonance G4 pass) | Add score persistence to trend file | Use existing `_parse_resonance_score` (line 667) result, persist via `write_truth_file(mode="upsert_markdown_row")` to `resonance_trend.md`. Format MUST match `escalation_bridge.py:15-17` reader (markdown table, 7+ columns, column 7 = overall) |
| `src/shenbi/orchestration/escalation_bridge.py:10` | Reference only (READ side) | `parse_resonance_scores` reads `resonance_trend.md` as markdown table — writer must produce compatible format |
| `src/shenbi/pipeline/triggers.py:401-443` (`check_triggers`) + `:503-617` (`run_triggered_skills`) | Add self-heal + failure visibility | Style-learning trigger system EXISTS here — do NOT add parallel trigger in `chapter_loop.py`. Add `_style_profile_is_stale()` self-heal + `state.last_trigger_failure` recording |
| `src/shenbi/pipeline/cli.py` (~line 214) | Audit trigger invocation on resume | Ensure `run_triggered_skills` is NOT skipped on resume after checkpoint/interrupt |
| `src/shenbi/pipeline/chapter_loop.py` (near state save) | Add audit count filesystem verification | Self-heal stale audit counts |
| `src/shenbi/gates/g4/state_settling.py` | Enhance existing checker with character_matrix integrity validation | Currently only checks heading regex (113 lines); add `_check_character_matrix_integrity` to verify human character definitions persist |
| `src/shenbi/gates/g4/chapter_drafting.py` | Add `G4.cd.protagonist_presence` check | Currently 205 lines with NO protagonist check; add `_check_protagonist_presence` |
| `src/shenbi/pipeline/audit_layer.py:57-67` (`_CORE_CIRCLE_KEYS`) | Register `resonance` and `review-summary` audit keys | Ensure all 13 audit types are tracked in state |
| `skills/shenbi-foreshadowing-track/SKILL.md` | Prompt update | Clarify hook ID standardization and body-append format (frontmatter hooks array already handled by deterministic `hook_planting.py`) |

---

## 5. Verification Criteria

1. **Mini-pipeline (5 chapters):**
   - `resonance_trend.md` has 5 data rows (not 1)
   - `chapter_summaries.md` references 5 chapters (not 1)
   - `pending_hooks.md` contains hook data from all 5 chapters
   - `emotional_arcs.md` has 5 chapter entries

2. **Idempotency:** Running the same chapter twice does not produce duplicate entries in append-mode files.

3. **Resonance scores:** All 5 chapters have `resonance_score != null` in pipeline state.

4. **Style learning:** After 4 chapters, `style_profile.md` is non-bootstrap (confidence >= medium, sample_chapter_count >= 3).

5. **Protagonist presence:** Every chapter's G4 check confirms protagonist name appears >= 3 times.

6. **Character matrix integrity:** `character_matrix.md` retains human character definitions; parameter agents go to `particle_ledger.md`.

7. **Audit count accuracy:** Pipeline state audit counts match filesystem `chapter-N-*.md` file count for every chapter.

8. **Regression:** `just check` passes fully.

---

## 6. Dependencies

```
Spec 1 (this spec, Truth File and State Accumulation)
    |
    +---> Spec 4 (Context Persistence and Linguistic Drift Prevention) -- needs historical resonance data for baseline
    |
    +---> Spec 3 (Dispatch Safety and File Integrity) -- pipeline state accuracy affects resume safety

Prerequisites: None (standalone fix)
```

### 6.1 Original Issue Code Mapping

| Original Issue Code | Description | Consolidated To |
|---|---|---|
| CN1 | 主角消失 (Protagonist Disappearance) | Spec 1 (this spec) |
| CN2 | Hook System Bifurcation | Spec 1 (this spec) |
| CN3 | Truth File Overwrite | Spec 1 (this spec) |
| CN4 | Resonance Score Null | Spec 1 (this spec) |
| CN5 | Style Learning Never Updated | Spec 1 (this spec) |
| CN6 | Pipeline State Stale Data | Spec 1 (this spec) |
| H1 | JSON Corruption | Spec 2 |
| H2 | Revision System Failure | Spec 2 |
| M5 | G4 Format Mismatch | Spec 2 |
| C1 | Revision Overwrite Chapter Content | Spec 3 |
| H4 | Staging Residue Leak | Spec 3 |
| M3 | Snapshot Coverage Gaps | Spec 3 |
| LN1-LN3 | Snapshot Bloat / Lockfile / Budget Copy | Spec 3 |
| C2 | Progressive Prose Collapse | Spec 4 |
| H3 | Context Assembly Persistence Gap | Spec 4 |
| HN1 | Template Duplication | Spec 4 |
| content-looping | Chapter Content Looping | Spec 4 |
| title-degradation, plan-content-mismatch, RS1, static-review-checklist | Review Quality Issues | Spec 5 |
| step-reorganization, parallelize, SCR, M1 | Pipeline Architecture | Spec 6 |
| maturity-bp-fixes, crash-recovery, runtime-optimizations, L1-L3, M2, H5, M4 | Pipeline Infrastructure | Spec 7 |
| llm-context-optimization | LLM Context Engineering | Spec 8 |
| volume-map, character-archive, C3 | Content Planning and Deliverable Design | Spec 9 |
| gate-markers, review-checklist-static, snapshot-differential | Data Storage Optimization | Spec 10 |
| validation, chapter-size-time | End-to-End Validation Protocol | Spec 11 |
