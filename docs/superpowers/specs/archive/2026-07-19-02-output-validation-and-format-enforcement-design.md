# Spec 2: Output Validation and Format Enforcement Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** High
> **Consolidated from:**
> - `2026-07-17-fix-decisions-json-corruption-design.md` (H1)
> - `2026-07-17-fix-json-nonstandard-format-design.md`
> - `2026-07-17-fix-revision-system-failure-design.md` (H2)
> - `2026-07-17-fix-missing-revision-decisions-design.md`
> - `2026-07-17-fix-resonance-g4-format-mismatch-design.md` (M5)

---

## 1. Executive Summary

The pipeline produces JSON output files that are corrupt, non-standard, or missing -- and the existing G2/G4 gate system fails to catch these defects before they persist to disk. Of 55 primary `chapter-N-decisions.json` files measured, 34/55 (61.8%) contain trailing markdown after a single valid JSON object. Ten out of 34 revision decisions files have JSON syntax errors, and the remaining 24 have zero change records. The revision system ran 34 times and produced zero effective modifications. Separately, the resonance audit G4 checker caused 35 retry loops (65% of all retries) because retry feedback only returned opaque check IDs without format examples, and the checker rejected legitimate format variants.

**Shared root cause (verified):** LLM output is written to disk in `dispatch_helper.py:_write_parsed_outputs` (line 294-323) with zero pre-write JSON validation — confirmed by grep showing zero `json.loads`/`valid`/`sanitize` calls in the write path. The write-before-gate ordering is confirmed: `chapter_loop.py:1243` dispatches (which writes to disk), then `chapter_loop.py:1286` runs G4 — the corrupt file is already persisted when G4 fires. G4 gates for revision decisions only check JSON syntax via `g4_decisions` (routed at `generic.py:237`), not content validity. G4 retry feedback lacks format guidance. No output completeness requirement exists for revision routes.

---

## 2. Root Cause Analysis (Per-Source-Spec Breakdown)

### 2.1 Decisions JSON Corruption (H1)

**Discovery (verified by filesystem audit of `novel-output/xinghuo-ranqiong/chapters/`):** Of 55 primary `chapter-N-decisions.json` files, 34/55 (61.8%) contain trailing markdown after a single valid JSON object. The dominant corruption pattern is **trailing markdown after one valid JSON object** (NOT multi-JSON concatenation as initially reported). 3 additional files are genuinely invalid (unparseable).

**Correction of earlier claim:** Initial analysis reported "Ch5 has 35 concatenated JSON objects; Ch54 has 22." Filesystem verification found this to be **FALSE** — Ch5 has exactly 1 `$schema` key (trailing markdown case), and Ch54 is fully valid JSON with no corruption. No file in the repo has multiple `$schema` keys. The earlier multi-JSON concatenation narrative was incorrect; the real problem is uniformly trailing markdown after a single JSON object.

**Typical corruption (Ch1 — verified exact match):**
```json
{"$schema": "shenbi-decisions-v1", "skill": "shenbi-chapter-drafting", ...}
```
```
---

**两项 G4 失败修复摘要：**
1. **G4.transition (7→0)** — 正文中监控转折词使用量为零...
```
Ch1's first JSON ends at byte 3007 of 3371; the 364-byte tail is English/Chinese markdown summary.

**Direct cause (verified):** `dispatch_helper.py:294-323` (`_write_parsed_outputs`) parses `### FILE: path/to/file.md` markers via `_parse_file_outputs` (regex `r"###\s*FILE:\s*(\S+)\s*\n(.*?)(?=###\s*FILE:|\Z)"` at line 279), then unconditionally writes via `safe_write(path, content)` at line 316. The regex captures everything up to the next `### FILE:` marker or end-of-string — so trailing markdown after the last file's JSON is included in `content` and written verbatim. There is zero pre-write JSON validation (confirmed by grep: the only `json.loads` calls in `dispatch_helper.py` are for parsing G3/G4 subprocess stdout at lines 624, 653, NOT for validating content before write).

**Why gates did not catch this:**
1. G2 (`gates/g2.py:85`): `json.loads(content)` would throw `JSONDecodeError("Extra data")` — but only if G2 is invoked on these files. G2 has a hard guard at `g2.py:81-82`: `if not fp.endswith(".json"): continue`, and only validates files passed in `file_paths`.
2. G4 (`gates/g4/decisions_validator.py:53`): `json.loads(p.read_text())` with `DecisionsDoc.model_validate(data)` (`extra="forbid"` at `decisions.py:70`) — would catch it if invoked.

Both should catch these errors IF invoked. They did not prevent corrupted files from persisting because:
- `_write_parsed_outputs` writes before gates check — file is already persisted when gate failure occurs (confirmed: `chapter_loop.py:1243` dispatch → write, then `:1286` G4)
- If G4 fails on a corrupted file, the retry cycle writes a new output that may still have trailing markdown, and the old corrupted file is already on disk

**Multi-JSON concatenation (theoretical, not observed):** While no current file exhibits multi-JSON concatenation, the proposed G2.dec.4 check (`content.count('"$schema"') > 1`) is still a valid defensive measure against future retry-loop concatenation.

### 2.2 Non-Standard JSON Format (Extension of H1)

**Discovery (Agent 3 Section 3):**
- 84 decisions.json: valid first JSON + trailing markdown (recoverable)
- 1 genuinely corrupted file: `staging/plans/chapter-49-plan-decisions.json` line 21 col 160 -- illegal control character
- All gate-marker and checklist JSONs are normal

**Additional finding:** Staging path JSON files lack the same validation as final-path files. Control characters (`0x00-0x1F` excluding `\n`, `\r`, `\t`) are not sanitized before write.

**Direct cause:** The pre-write validation designed in H1's Layer 1 must apply equally to staging paths. A general-purpose `sanitize_json_content()` function is missing.

### 2.3 Revision System Failure (H2)

**Discovery:** 34 `chapter-N-revision-decisions.json` files audited:

| Type | Count | Percentage | Example |
|------|-------|------------|---------|
| JSON syntax errors | 10 | 29.4% | Ch2: empty file; Ch15: illegal comma; Ch18: control character |
| Zero change records | 24 | 70.6% | `changes: []` or missing changes field |
| **Effective revisions** | **0** | **0%** | -- |

**Conclusion: The revision system executed 34 times and produced zero effective modifications.**

**Retry loop evidence:** Pipeline recorded 54 retry_feedback entries, 35 (65%) from `shenbi-review-resonance` G4 failures. Pattern: resonance failure -> trigger revision -> revision produces invalid file -> G4 fails again -> re-trigger revision -> infinite loop.

**Root causes (threefold):**

1. **G4 coverage gap for revision outputs:** `gates/g4/generic.py:237` routes `shenbi-chapter-revision` to `g4_decisions` only -- which checks JSON syntax but does not check:
   - Whether `changes` array is non-empty
   - Whether change entries have required fields (`location`, `before`, `after`, `reason`)
   - Whether no-op routes have adequate rationale
   - Whether "retention verification" block exists (required by SKILL.md lines 63-64)

2. **SKILL.md missing no-op output specification:** `skills/shenbi-chapter-revision/SKILL.md:105-108` defines spot-fix and rewrite modes but has no definition of no-op/auto-skip output format. The LLM, when determining "no revision needed," outputs arbitrarily.

3. **Revision routing logic defect:** `chapter_loop.py:1021` (`_route_revision_after_resonance`) routes to spot-fix or rewrite based on resonance scores, but Route B (spot-fix) may trigger when the LLM cannot find concrete modification points, leading to empty changes.

### 2.4 Missing Revision Decisions Files

**Discovery (Agent 3):** 21 chapters have revision routing recorded in pipeline state but no `chapter-N-revision-decisions.json` on disk: Ch3, 4, 10, 13, 14, 16, 17, 25, 27-32, 34, 36-38, 42, 54.

**Direct causes:**
1. Route "no-revision" causes the skill to be skipped entirely, but the pipeline contract expects a decisions file even for no-op routes.
2. Revision dispatch times out or fails but pipeline state marks it as completed.
3. Staging output is never committed to final path.

### 2.5 Resonance G4 Format Mismatch (M5)

**Discovery:** 35 retry_feedback entries (65% of all retries) from `shenbi-review-resonance` G4 failures:

```
ch1-shenbi-review-resonance: G4 HARD check failed: ["G4.rr.detail_table:chapter-1-resonance.md:missing_['裁判理由']"]
ch2-shenbi-review-resonance: G4 HARD check failed: ['G4.rr.verdict:chapter-2-resonance.md:no_valid_verdict', 'G4.rr.evidence:...']
```

**Pattern analysis:**
- `no_valid_verdict` most frequent -- LLM's `校准门判定` line doesn't match G4 regex
- `missing_['裁判理由']` -- scoring detail table missing column
- `no_file_line_ref` -- evidence column missing `file:line` references

**Why retries don't resolve the issue:** G4 failure feedback only returns opaque check IDs (e.g., `G4.rr.verdict`), not the specific format expectations. The LLM sees "verdict failed" but doesn't know what format is expected, so it regenerates -- still incorrect -- and fails again.

**G4 checker expectations** (`gates/g4/review_resonance.py:28-89` — verified line ranges):
1. `G4.rr.detail_table` (line 48-57): Scoring detail table must have 6 column headers matching `_DETAIL_COLS = ("维度", "得分", "满分", "置信度", "证据", "裁判理由")` (line 22)
2. `G4.rr.verdict` (line 61-72): `校准门判定` section must have a verdict line. **Verified actual regex** at line 64: `r'判定\s*[:：]\s*(\S+)'` — the code already accepts BOTH half-width `:` and full-width `：` with optional whitespace, and matches any non-whitespace token (then validates membership against `_VERDICTS`). The code is already more lenient than the spec's earlier description suggested. The remaining gaps are: (a) `**判定**` (markdown bold) is NOT matched, (b) English `Verdict: PASS` is NOT matched.
3. `G4.rr.evidence` (line 75-82): At least one `L\d+|line\s+\d+|:\d+` reference

---

## 3. Unified Fix Strategy

The fix is organized into three layers of defense for JSON output integrity, plus targeted fixes for the revision system and resonance G4 feedback.

### Layer 1: Pre-Write JSON Validation + Recovery

**Location:** `dispatch_helper.py:_write_parsed_outputs` (around line 316, before `safe_write` call)

```python
# In _write_parsed_outputs, before safe_write(full_path, content)
if full_path.suffix == '.json':
    from pydantic import ValidationError  # MUST import at module level or here
    try:
        parsed = json.loads(content)
        # Additional: validate shenbi-decisions-v1 schema
        if isinstance(parsed, dict) and parsed.get('$schema') == 'shenbi-decisions-v1':
            from shenbi.contracts.schemas.decisions import DecisionsDoc
            DecisionsDoc.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("decisions_json_invalid", path=str(full_path), error=str(e))
        # Recovery: truncate to first complete JSON object
        try:
            decoder = json.JSONDecoder()
            clean_data, end_pos = decoder.raw_decode(content)
            logger.warning("decisions_json_truncated", path=str(full_path),
                           original_len=len(content), cleaned_len=end_pos)
            content = json.dumps(clean_data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            raise ValueError(f"Decisions JSON invalid and unrecoverable: {e}")
```

**Key design decisions:**
- `json.JSONDecoder().raw_decode()` returns the first complete JSON object and its end byte position, cleanly truncating trailing text.
- Schema validation is applied after JSON parse to catch structural issues.
- If unrecoverable, raise ValueError to prevent corrupt file persistence (stops the pipeline rather than silently corrupting).

### Layer 2: G2 Enhancement for Multi-JSON Concatenation Detection

**Location:** `gates/g2.py` — inside the decisions branch, BEFORE the `continue` at line 105 (the decisions branch hits `continue` early, skipping the general `.json` path at line 108, so the check must go inside the decisions branch).

```python
# g2.py: inside the `if file_type == "decisions":` branch (lines 74-105)
# BEFORE the `continue` at line 105
# New check G2.dec.4 -- multi-JSON concatenation detection
if content.count('"$schema"') > 1:
    issues.append("G2.dec.4: multiple JSON objects concatenated in single file")
```

While no current file exhibits multi-JSON concatenation (verified — see §2.1 correction), this is a valid defensive measure against future retry-loop concatenation.

### Layer 3: Control Character Sanitization

**Location:** New utility function, potentially in `dispatch_helper.py` or a shared sanitization module

```python
def sanitize_json_content(content: str) -> str:
    """Remove illegal control characters from JSON content.

    JSON spec only permits specific control characters (\n, \r, \t).
    Removes all other control characters in range 0x00-0x1F except those three.
    """
    import re
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    return cleaned
```

Apply `sanitize_json_content()` to all JSON content in `_write_parsed_outputs` before writing, for both staging and final paths.

### Guard Ordering in `_write_parsed_outputs`

Multiple specs add guards at the `safe_write` call in `_write_parsed_outputs`. The execution order MUST be:

1. Sanitize control characters (Spec 2 Layer 3)
2. Pre-write JSON validation + recovery (Spec 2 Layer 1)
3. Content-size guard for chapter files (Spec 3 §3.2)
4. Truth file mode routing via `write_truth_file` (Spec 1 §3.2)
5. Wildcard write-path resolution (Spec 9 §3.2.1)
6. `safe_write` call (original)

### G4 Revision Checker Upgrade

**Critical schema constraint:** Revision decisions files conform to `DecisionsDoc` (`contracts/schemas/decisions.py:69-83` with `extra="forbid"`). They have `selections` and `adjustments` arrays — NOT a `changes` array. The `generic.py:237` already routes `shenbi-chapter-revision` to `g4_decisions`, so the LLM is told to produce `selections`/`adjustments`. The new checker must validate revision-specific content WITHIN the existing schema, not invent new fields.

**Option A (preferred): Extend DecisionsDoc with optional revision fields.** Add optional `revision_mode`, `skip_reason` fields to `DecisionsDoc` (or create a `RevisionDecisionsDoc` subclass). This allows the revision skill to emit revision-specific metadata while maintaining schema compatibility.

**Option B: Check adjustments content semantics.** Validate that when `adjustments` is non-empty, each adjustment has meaningful content (the `Adjustment` model already requires `issue_id`, `severity`, `handling`, `rationale` — so the checker validates rationale quality).

**Location:** New file `gates/g4/chapter_revision.py`

```python
def g4_chapter_revision(files: list[Path], rd: Path, project_dir: Path, repo_root: Path) -> str:
    """Dedicated revision output checker beyond basic JSON validation.

    Works WITHIN the DecisionsDoc schema (selections/adjustments), not against it.
    Signature matches the G4 checker protocol for make_composite_checker integration.
    """
    issues = []
    for f in files:
        if f.suffix != '.json' or 'revision' not in f.name:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            issues.append(f"G4.rev.invalid_json:{f.name}")
            continue

        # The DecisionsDoc schema has selections + adjustments.
        # For revision: adjustments represent the actual revision actions.
        adjustments = data.get('adjustments', [])

        # HARD: if no adjustments, the revision mode must be documented
        if not adjustments:
            # Check if selections document a no-op/skip decision
            selections = data.get('selections', [])
            has_skip_selection = any(
                'no_revision' in str(s.get('target', '')).lower() or
                'skip' in str(s.get('target', '')).lower()
                for s in selections if isinstance(s, dict)
            )
            if not has_skip_selection:
                issues.append(
                    f"G4.rev.empty_adjustments_no_skip:{f.name} -- "
                    f"revision has zero adjustments and no documented skip reason"
                )

        # HARD: each adjustment must have substantive rationale (>= 20 chars)
        for i, adj in enumerate(adjustments):
            if isinstance(adj, dict):
                rationale = str(adj.get('rationale', ''))
                if len(rationale) < 20:
                    issues.append(
                        f"G4.rev.adjustment_{i}_thin_rationale:{f.name} -- "
                        f"rationale must be >=20 chars, got {len(rationale)}"
                    )

    return issues  # Returns list of issue strings for composite checker
```

**Return type correction:** The function must return a JSON result string matching the G4 checker protocol (like `g4_decisions` returns). The `make_composite_checker` (`decisions_validator.py:87`) calls `json.loads(existing_result)` and expects `{"status": "...", "checks": [...], "must_fix": [...]}`. Replace `return issues` with `return json.dumps({"status": "PASS" if not issues else "HARD_FAIL", "checks": issues, "must_fix": issues})`.

Corrected return statement at the end of the function:

```python
    # Return a JSON result string matching the G4 checker protocol.
    # make_composite_checker (decisions_validator.py:87) does
    # json.loads(existing_result) and expects {"status","checks","must_fix"}.
    return json.dumps({
        "status": "PASS" if not issues else "HARD_FAIL",
        "checks": issues,
        "must_fix": issues,
    })
```

**Integration with existing g4_decisions:** Use `make_composite_checker(g4_decisions, g4_chapter_revision)` at `generic.py:237` — this runs both the JSON syntax/schema check AND the revision-content check. The composite checker partitions files by extension (`.json` → both checkers).

**Key design decisions:**
- Works within `DecisionsDoc` schema — does NOT invent `changes`/`route`/`skip_reason` fields that would fail `extra="forbid"`.
- Empty `adjustments` are allowed ONLY when `selections` documents a no-op/skip decision.
- Each adjustment rationale must be >= 20 characters (the `Adjustment` model already requires `rationale`, but doesn't enforce minimum length).

### Revision SKILL.md Update

**Location:** `skills/shenbi-chapter-revision/SKILL.md` (around line 105-108)

Add explicit output requirements using the **actual DecisionsDoc schema fields** (`selections`/`adjustments`, NOT `changes`):

```markdown
### Revision Modes and Output Requirements

All revision-decisions.json files MUST conform to shenbi-decisions-v1 schema.
Use the `adjustments` array for revision actions and `selections` for routing decisions.

- **spot-fix mode**: `adjustments` array, each entry must contain `issue_id` (target dimension),
  `severity` (impact level), `handling` (compensation strategy), `rationale` (change justification >= 20 chars)
- **rewrite mode**: `adjustments` array with `handling: "explicit_callout"`,
  each `rationale` must justify the rewrite (>= 20 chars)
- **no-op mode**: `adjustments: []`, with a `selections` entry documenting the skip:
  `{target: "no_revision_needed", selected: [], basis: "arc_relevance", severity: "low"}`
- **auto-skip mode**: same as no-op, but `basis: "adjacent_to_target_chapter"`
- **CRITICAL**: In no-op/auto-skip mode, do NOT output the chapter body file
  (`chapters/chapter-N.md`). Only output `chapters/chapter-N-revision-decisions.json`.
```

### Ensure Every Revision Route Writes a Decisions File

**Location:** `chapter_loop.py` — in the revision step success handler (around line 1243-1286, in the `if "chapter-revision" in step.skill:` block, NOT at line 1438 which is the resonance path).

**Critical schema constraint:** The fallback file must conform to `DecisionsDoc` schema (`extra="forbid"`) — it must NOT use `route`/`changes`/`rationale` keys that would fail `g4_decisions` validation.

```python
# After revision step completes, ensure decisions file exists
# MUST conform to DecisionsDoc schema ($schema, skill, chapter, selections, adjustments, produced_at)
rev_path = project_dir / f"chapters/chapter-{chapter}-revision-decisions.json"
if not rev_path.exists():
    # Minimal DecisionsDoc-compliant file for no-revision routes
    from datetime import datetime, timezone
    min_decisions = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-revision",
        "chapter": chapter,
        "selections": [
            {
                "target": "no_revision_needed",
                "selected": [],
                "basis": "arc_relevance",
                "severity": "low",
                "omitted": [],
            }
        ],
        "adjustments": [],  # empty = no changes made
        "produced_at": datetime.now(timezone.utc).isoformat(),
    }
    safe_write(rev_path, json.dumps(min_decisions, ensure_ascii=False, indent=2))
```

This ensures every chapter that has a revision route (including no-revision) produces a `DecisionsDoc`-compliant artifact for audit trail completeness.

### Enrich G4 Retry Feedback with Format Examples

**Location:** `chapter_loop.py` (in retry feedback construction, near where G4 failures are formatted for LLM consumption)

```python
G4_FORMAT_EXAMPLES = {
    "G4.rr.detail_table": (
        "评分明细表格式：\n"
        "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |\n"
        "|------|------|------|--------|------|----------|\n"
        "| 情感落地 | 25 | 30 | 高 | chapter-N.md L45-52 > ... | ... |"
    ),
    "G4.rr.verdict": (
        "校准门判定必须包含以下行：\n"
        "判定: 通过    （或：判定: 阻断  / 判定: 待人机复核）\n"
        "注意：冒号可用半角 : 或全角 ：，'判定' 后冒号前可有空格"
    ),
    "G4.rr.evidence": (
        "证据列每行必须包含文件和行号引用，格式：\n"
        "chapter-N.md L45-52 > \"引用原文\""
    ),
}

def _enrich_g4_feedback(failures: list[str]) -> str:
    """Build enriched retry feedback with format examples for each failed check."""
    feedback = "以下 G4 检查失败，请按指定格式修正：\n\n"
    for f in failures:
        check_id = f.split(":")[0] if ":" in f else f
        feedback += f"- **{f}**\n"
        if check_id in G4_FORMAT_EXAMPLES:
            feedback += f"  期望格式：\n  {G4_FORMAT_EXAMPLES[check_id]}\n"
    return feedback
```

### Add Lenient Parsing in Resonance G4 Checker (Gap-Specific)

**Location:** `gates/g4/review_resonance.py:64` (verdict regex)

**Verified current state:** The code at line 64 already uses `r'判定\s*[:：]\s*(\S+)'` which accepts both half-width `:` and full-width `：` with optional whitespace, and matches any non-whitespace token (validated against `_VERDICTS`). This is already lenient for the colon variant.

**Remaining gaps** (what the current regex does NOT match — verified by testing):
1. `**判定**: 通过` — markdown bold wrapping (`**判定**`) — the `**` breaks the `判定` prefix match
2. `Verdict: PASS` — English verdict prefix — `判定` is not in the string

**Already matched (NOT a gap):** `## 判定：通过` — heading-style verdict IS matched by the existing regex because it is not anchored (`re.search` finds `判定：通过` within the line regardless of `##` prefix).

Add tolerance for the 2 genuine gaps:

```python
# In g4_review_resonance, supplement the existing regex with gap-specific patterns
# Current (line 64): r'判定\s*[:：]\s*(\S+)' — already handles : and ：, ## prefix, etc.
# Only 2 genuine gaps remain:
VERDICT_SUPPLEMENT_PATTERNS = [
    r'\*\*判定\*\*\s*[:：]\s*(\S+)',           # markdown bold
    r'Verdict\s*[:：]\s*(\S+)',                # English prefix
]

verdict = None
# Try existing pattern first (line 64)
verdict_match = re.search(r'判定\s*[:：]\s*(\S+)', content)
if not verdict_match:
    # Fall back to supplement patterns
    for pattern in VERDICT_SUPPLEMENT_PATTERNS:
        verdict_match = re.search(pattern, content)
        if verdict_match:
            break
if verdict_match:
    verdict = verdict_match.group(1)
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/dispatch_helper.py:294-323` | Add pre-write JSON validation via `json.JSONDecoder().raw_decode()` + schema validation | Layer 1: catch and recover trailing markdown before write |
| `src/shenbi/pipeline/dispatch_helper.py` (new function) | Add `sanitize_json_content()` | Layer 3: strip illegal control characters |
| `src/shenbi/gates/g2.py:85-90` (new check) | Add `G2.dec.4` multi-JSON concatenation detection | Layer 2: detect concatenated JSON objects |
| `src/shenbi/gates/g4/chapter_revision.py` (new file) | Create `g4_chapter_revision()` checker with `(fps, rd, project_dir, repo_root) -> str` signature | Validate adjustments array content WITHIN DecisionsDoc schema (selections/adjustments, NOT changes array) |
| `src/shenbi/gates/g4/generic.py:237` | Route `shenbi-chapter-revision` to `make_composite_checker(g4_decisions, g4_chapter_revision)` | Run both JSON syntax check AND revision-content check |
| `skills/shenbi-chapter-revision/SKILL.md:105-108` | Add no-op/auto-skip output specification using selections/adjustments schema | Prevent arbitrary empty-adjustment outputs |
| `src/shenbi/pipeline/chapter_loop.py` (revision step success handler, ~line 1243-1286) | Ensure `revision-decisions.json` written for all routes, conforming to DecisionsDoc schema | Close missing-file gap for 21 chapters |
| `src/shenbi/pipeline/chapter_loop.py` (retry feedback) | Add `G4_FORMAT_EXAMPLES` dict + `_enrich_g4_feedback()` function | Give LLM concrete format examples in retry loops |
| `src/shenbi/gates/g4/review_resonance.py:64` | Add lenient verdict patterns with multiple regex variants | Reduce false-negative G4 failures |
| `skills/shenbi-review-resonance/SKILL.md` | Add concrete format examples in output specification | Prevent LLM from guessing format |

---

## 5. Verification Criteria

1. **Unit tests** (`tests/unit/test_decision_json_validation.py`):
   - Valid JSON -> passes
   - JSON + trailing markdown -> Layer 1 truncates to first valid JSON object
   - 3 concatenated JSON objects -> Layer 1 extracts first + Layer 2 reports
   - Completely invalid JSON -> Layer 1 raises ValueError

2. **Unit tests** (`tests/unit/gates/g4/test_chapter_revision.py`):
   - Valid spot-fix revision (3 changes with detailed descriptions) -> PASS
   - Valid no-op revision (empty changes + >=50 char rationale) -> PASS
   - Empty changes without rationale -> HARD FAIL
   - Change with missing description -> HARD FAIL
   - JSON syntax error -> HARD FAIL (caught by g4_decisions)

3. **Integration test:** Simulate dispatch write with corrupted Ch1 decisions.json content, verify written file is valid JSON.

4. **Resonance retry reduction:** 5 consecutive resonance audits -> retry count <= 1 per chapter.

5. **Lenient parsing:** Verify all 3 verdict format variants match correctly.

6. **Revision completeness:** All 56 chapters have `revision-decisions.json` regardless of route.

7. **0 illegal control characters** in any staging or final JSON file.

8. **Regression:** `just check` passes fully.

---

## 6. Dependencies

```
Spec 2 (this spec, Output Validation and Format Enforcement)
    |
    +---> Spec 3 (Dispatch Safety and File Integrity) -- revision content guard depends on valid JSON

Prerequisites: None (standalone fix)
```

### 6.1 Original Issue Code Mapping

| Original Issue Code | Description | Consolidated To |
|---|---|---|
| H1 | JSON Corruption | Spec 2 (this spec) |
| H2 | Revision System Failure | Spec 2 (this spec) |
| M5 | G4 Format Mismatch | Spec 2 (this spec) |
| CN1 | 主角消失 (Protagonist Disappearance) | Spec 1 |
| CN2 | Hook System Bifurcation | Spec 1 |
| CN3 | Truth File Overwrite | Spec 1 |
| CN4 | Resonance Score Null | Spec 1 |
| CN5 | Style Learning Never Updated | Spec 1 |
| CN6 | Pipeline State Stale Data | Spec 1 |
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
