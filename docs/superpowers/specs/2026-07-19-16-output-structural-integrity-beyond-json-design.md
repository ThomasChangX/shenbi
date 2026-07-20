# Spec 19: LLM Output Integrity — Structural, Write-Failure, and Content-Anomaly Detection

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** High
> **Source:** Systematic debugging Phase 1 evidence (E3, E10, E13, E14, E16, E26)
> **Consolidated from findings:**
> - E3: Ch56 truncated mid-generation — model stream-of-consciousness ("Now the decisions JSON:") leaked into chapter prose
> - E10: Ch55 audits reference line numbers (L29-31, L41-45) that don't exist in the 101-byte file — audit-content version skew
> - E13: Ch24 resonance audit is sandbox failure — model says "由于沙箱限制，我无法直接写文件" (sandbox limitation, cannot write file)
> - E14: Ch40 decisions.json says "The file on disk can't be updated (read-only sandbox)"
> - E16: Ch32 foreshadowing audit is 145-byte aborted stub ("inputs confirmed, now executing...") with no verdict
> - E26: 9 chapters have orphan code fences (odd number of ``` markers) — Markdown structural corruption
>
> **Merge note:** This spec unifies the former Spec 19 (Output Structural Integrity Beyond JSON) and Spec 20 (Write-Path Failure Detection), which shared overlapping pattern catalogs and the same root failure mode — the LLM emitting non-content (diagnostics, meta-commentary, aborted stubs) that the pipeline persisted as if it were real output.

---

## 1. Executive Summary

Spec 2 validates JSON structural integrity (trailing markdown, control characters, schema compliance). But six classes of defects in **LLM outputs** are completely undetected — spanning both JSON and non-JSON deliverables, and both the write path and post-write validation:

1. **Write-path failure (E13, E14):** The LLM reported it could not write to the filesystem and emitted a diagnostic message instead of the requested file content. Ch24's resonance audit begins "由于沙箱限制，我无法直接写文件..." and Ch40's decisions.json says "The file on disk can't be updated (read-only sandbox)." The pipeline accepted these diagnostics as valid content.

2. **Model leakage into prose (E3):** Ch56 ends with the model's internal monologue ("Now the decisions JSON:") instead of novel text. The chapter file contains planning intent, not prose.

3. **Markdown structural corruption (E26):** 9 chapters have an odd number of `` ``` `` code-fence markers, meaning an opening or closing fence is orphaned — the file was extracted from a code-fenced LLM response but one fence was lost.

4. **Audit-content version skew (E10):** Ch55's audit files cite `chapter-55.md L29-31` and `L41-45`, but the actual file is 101 bytes (3 lines). The audits ran against a longer pre-overwrite version.

5. **Aborted audit stubs (E16):** Ch32's `chapter-32-foreshadowing.md` is 145 bytes: just "所有输入文件已确认。现在执行完整的伏笔审计..." — no actual audit was performed.

**Root cause:** The dispatch path (`_write_parsed_outputs`) writes whatever the LLM outputs, and all structural validation targets JSON files. No single choke point runs a unified set of integrity checks across every parsed output. Prose (`.md`) and audit (`.md`) files have no structural integrity checks beyond G4 skill-specific format validation, which doesn't catch generic corruption patterns.

---

## 2. Root Cause Analysis

### 2.1 Write-Path Failure Mode (E13, E14)

Some LLM deployment environments (especially sandboxed code execution environments) restrict filesystem writes. When the model encounters this restriction, it may:
- Emit an apology/explanation instead of the file content
- Reference `### FILE:` markers without actually outputting content
- Produce a summary of what it "would have" written

The pipeline's `_parse_file_outputs` regex captures everything after `### FILE:` until the next marker or EOF — including diagnostic messages. `_write_parsed_outputs` then persists them with no scan for write-failure signatures.

### 2.2 Model Leakage Markers in Prose (E3)

When the LLM's generation is interrupted or it runs out of output tokens mid-response, the chapter file may contain:
- Stream-of-consciousness planning: "Now the decisions JSON:", "Let me write..."
- Schema references: "schema:", "```json"
- Meta-instructions: "The file on disk can't be updated..."

Ch56's file contains 1850 bytes of this leakage after the META-END marker. The content-size guard (Spec 3 §3.2) checks file size but not content semantics.

### 2.3 Audit-Content Version Skew (E10)

Audits cite specific line references (`chapter-N.md L29-31`). When the chapter file is later overwritten (e.g., by revision overwrite per Spec 3 E1), the line references become invalid. The audit files remain on disk with stale references, creating a false audit trail.

**Evidence:** Ch55 audits reference L29-31, L41-45 in a 101-byte (3-line) file.

### 2.4 Aborted Audit Stubs (E16)

Some audit skills produce a preamble ("inputs confirmed, now executing...") but then fail to produce the actual audit — possibly due to output token limits, sandbox restrictions, or dispatch failures. The preamble is written to disk as if it were a complete audit.

**Evidence:** `chapter-32-foreshadowing.md` = 145 bytes, single sentence, no verdict section. Ch32 still passed the chapter loop.

### 2.5 Markdown Fence Imbalance (E26)

The dispatch path extracts content from LLM responses that are wrapped in code fences. If the extraction regex captures an odd number of fence markers, the output file has an orphan fence. 9 chapters exhibit this: Ch1, 11, 14, 19, 22, 29, 33, 42, 56.

---

## 3. Fix Strategy

### 3.1 Unified Pattern Catalog (single source of truth)

The former Specs 19 and 20 maintained overlapping pattern lists (e.g., both matched `由于沙箱限制` and `read-only sandbox`). This consolidated catalog merges and de-duplicates them into one module, split by **detection mode** because write-failure and leakage signatures require different triggering rules (see §3.2).

```python
# src/shenbi/pipeline/llm_output_integrity.py (new)

# --- Write-failure signatures: the LLM reports it cannot write. ---
# These supersede the broader standalone patterns from the former specs
# (e.g. bare `由于沙箱限制`, `can't be updated.*sandbox`) which are now
# covered by the more specific entries below.
WRITE_FAILURE_PATTERNS = [
    r"由于沙箱限制.*?(?:无法|不能).*?(?:写|写入)",
    r"(?:can't|cannot|unable to).*?(?:write|update|create).*?(?:file|sandbox|read-only)",
    r"read-only sandbox",
    r"Use the existing.*?from input",
    r"was already provided via.*?markers",
    r"I (?:cannot|can't|could not) (?:write|create|update) (?:the )?(?:file|output)",
]

# --- Model meta-commentary leakage in prose (NOT a write failure). ---
# Removed write-failure overlaps (sandbox/can't-be-updated) which now live
# exclusively in WRITE_FAILURE_PATTERNS above.
LEAKAGE_PATTERNS = [
    r"Now the .* JSON",
    r"Let me write",
    r"schema:",
    r"Here's a summary of the revision",
    r"修订执行摘要",
    r"Revision complete",
    r"All \d+ files have been",
]

# --- Audit completeness markers ---
VERDICT_MARKERS = ['判定', '结论', 'verdict', '通过', '阻断', 'PASS', 'BLOCK']
PREAMBLE_MARKERS = ['现在执行', 'inputs confirmed', 'now executing', '开始审计']
```

### 3.2 Write-Failure Detection (false-positive safe)

The former Spec 20 §3.2 triggered on any occurrence of a write-failure pattern **anywhere** in the content. This is unsafe: a chapter can legitimately contain dialogue *about* sandboxes or a character saying "I cannot write." Write-failure patterns must only fire when the diagnostic **dominates** the output — i.e., the pattern appears at the very **start** of the content, or the matched region plus surrounding diagnostic prose comprises **>50%** of the total output.

```python
def detect_write_failure(content: str) -> tuple[bool, str | None]:
    """Check if content is a write-failure diagnostic instead of file content.

    False-positive mitigation: a pattern only counts as a failure when it
    appears at the START of the content OR the matched span sits within a
    region that comprises >50% of the total output. A chapter that merely
    *mentions* a sandbox in passing is NOT a failure.

    Returns (is_failure, matched_pattern).
    """
    stripped = content.lstrip()
    total_len = max(len(content), 1)
    for pattern in WRITE_FAILURE_PATTERNS:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            continue
        start, end = match.span()
        # Case 1: pattern at the very start (ignoring leading whitespace).
        at_start = content[:start].strip() == ""
        # Case 2: the region from first non-empty char to end of match
        #         covers more than half the output — i.e. the diagnostic
        #         dominates rather than being embedded in real content.
        dominant = end > total_len * 0.5
        if at_start or dominant:
            return True, match.group(0)
    return False, None
```

### 3.3 Prose Leakage / Fence-Balance / Audit Checks

```python
def check_prose_leakage(path: Path) -> list[str]:
    """Detect model meta-commentary leakage in prose files."""
    issues = []
    text = path.read_text(encoding="utf-8")

    for pattern in LEAKAGE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            issues.append(
                f"G4.pi.model_leakage:{path.name} — "
                f"found '{matches[0]}' pattern ({len(matches)} occurrences). "
                f"Chapter file contains model meta-commentary, not prose."
            )

    # Check for unfinished ending
    last_500 = text[-500:].strip()
    if last_500 and last_500[-1] in ':,；：，':
        issues.append(
            f"G4.pi.unfinished_ending:{path.name} — "
            f"file ends with '{last_500[-20:]}' — truncated mid-thought"
        )

    return issues


def check_markdown_fence_balance(path: Path) -> list[str]:
    """Verify Markdown code fences are balanced in prose files."""
    issues = []
    text = path.read_text(encoding="utf-8")

    fence_count = text.count('```')
    if fence_count % 2 != 0:
        issues.append(
            f"G4.pi.fence_imbalance:{path.name} — "
            f"odd number of ``` markers ({fence_count}). "
            f"Orphan code fence — file was likely extracted incorrectly."
        )

    return issues


def check_audit_completeness(path: Path) -> list[str]:
    """Verify audit files contain an actual verdict, not just a preamble."""
    issues = []
    text = path.read_text(encoding="utf-8")

    # Minimum size check — real audits are > 500 bytes
    if len(text) < 200:
        issues.append(
            f"G4.ac.too_short:{path.name} — "
            f"audit file is {len(text)} bytes, likely aborted stub"
        )

    has_verdict = any(marker in text for marker in VERDICT_MARKERS)
    if not has_verdict:
        issues.append(
            f"G4.ac.no_verdict:{path.name} — "
            f"audit file contains no verdict/conclusion marker"
        )

    has_only_preamble = (
        any(marker in text for marker in PREAMBLE_MARKERS)
        and not has_verdict
    )
    if has_only_preamble:
        issues.append(
            f"G4.ac.aborted_stub:{path.name} — "
            f"audit file contains only execution preamble, no results"
        )

    return issues


def check_audit_line_refs(path: Path, chapter_path: Path) -> list[str]:
    """Verify audit line references point to valid lines in the chapter."""
    issues = []
    audit_text = path.read_text(encoding="utf-8")

    if not chapter_path.exists():
        return issues  # Chapter missing is handled elsewhere

    chapter_lines = chapter_path.read_text(encoding="utf-8").split('\n')
    max_line = len(chapter_lines)

    # Find all line references like "L29-31" or "L41"
    line_refs = re.findall(r'L(\d+)(?:-(\d+))?', audit_text)
    for start_str, end_str in line_refs:
        start = int(start_str)
        end = int(end_str) if end_str else start
        if end > max_line:
            issues.append(
                f"G4.av.stale_line_ref:{path.name} — "
                f"references L{start}-{end} but chapter has only {max_line} lines. "
                f"Audit ran against a different version of the chapter."
            )

    return issues
```

### 3.4 Single Integration Point — `_write_parsed_outputs`

**All** checks run from one choke point in the write path, in a fixed order. Write-failure detection runs first (and hardest — it blocks the write and triggers retry); the remaining checks run as post-write validation against the persisted file:

```python
# In dispatch_helper.py _write_parsed_outputs

for full_path, content in parsed_outputs:
    # 1. WRITE-FAILURE DETECTION (pre-write, blocks the write)
    is_failure, signature = detect_write_failure(content)
    if is_failure:
        logger.error("dispatch_write_failure_detected",
                     path=str(full_path), signature=signature)
        raise DispatchWriteFailureError(
            f"LLM reported write failure for {full_path}: '{signature}'. "
            f"The output is a diagnostic message, not file content. "
            f"Retry with explicit write-capability confirmation."
        )

    safe_write(full_path, content)

    # 2-5. POST-WRITE INTEGRITY (in fixed order; collect all issues)
    issues: list[str] = []
    name = full_path.name
    is_chapter = name.startswith("chapter-") and not _is_audit_file(name)
    is_audit = _is_audit_file(name)

    if is_chapter:
        # 2. PROSE LEAKAGE
        issues += check_prose_leakage(full_path)
        # 3. FENCE BALANCE
        issues += check_markdown_fence_balance(full_path)

    if is_audit:
        # 4. AUDIT COMPLETENESS
        issues += check_audit_completeness(full_path)
        # 5. AUDIT LINE-REF SKEW (needs the corresponding chapter file)
        chapter_path = _resolve_chapter_for_audit(full_path)
        issues += check_audit_line_refs(full_path, chapter_path)

    for issue in issues:
        logger.warning("llm_output_integrity_issue", path=str(full_path), finding=issue)
        # Surface to G4 via the composite-checker registry so the gate
        # can FAIL/WARN per the severity rules in §4.5.
```

### 3.5 Retry with Write-Capability Confirmation

When a write-failure is detected, the retry prompt explicitly confirms write capability:

```python
RETRY_WRITE_CONFIRMATION = (
    "CRITICAL: You have filesystem write access in this environment. "
    "Output the complete file content directly — do not explain, apologize, "
    "or reference sandbox limitations. Previous attempt failed with: '{signature}'."
)
```

### 3.6 Severity Routing to G4

Post-write findings are surfaced to G4 as composite checkers with these severities:
- `G4.pi.model_leakage`, `G4.pi.unfinished_ending` → **FAIL**
- `G4.pi.fence_imbalance` → **WARN**
- `G4.ac.too_short`, `G4.ac.no_verdict`, `G4.ac.aborted_stub` → **FAIL**
- `G4.av.stale_line_ref` → **FAIL**

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/llm_output_integrity.py` (new) | Unified pattern catalog + all five check functions | Single source of truth for LLM output integrity |
| `src/shenbi/pipeline/dispatch_helper.py` (`_write_parsed_outputs`) | Single integration point running all checks in order | One choke point instead of scattered G4-only checks |
| `src/shenbi/pipeline/dispatch_helper.py` (retry path) | Add write-capability confirmation to retry prompt | Break the write-failure loop |
| `src/shenbi/gates/g4/generic.py` | Register composite checkers fed from the post-write findings | Route severities to the gate |

---

## 5. Verification Criteria

1. **Write failure (start):** Ch24-style "由于沙箱限制，我无法直接写文件..." at file start → detected, dispatch fails, retry triggered
2. **Write failure (dominant):** Ch40-style "read-only sandbox" diagnostic comprising >50% of output → detected, dispatch fails
3. **No false positive:** A chapter whose prose legitimately mentions "sandbox" or "cannot write" in passing (not at start, <50% of content) → passes normally
4. **Prose leakage:** Ch56-style "Now the decisions JSON:" → `G4.pi.model_leakage` FAIL
5. **Aborted stub:** Ch32-style 145-byte audit → `G4.ac.aborted_stub` FAIL
6. **Version skew:** Audit referencing L41 in a 3-line file → `G4.av.stale_line_ref` FAIL
7. **Fence balance:** Odd ``` count → `G4.pi.fence_imbalance` WARN
8. **All 9 affected chapters** (Ch1,11,14,19,22,29,33,42,56) flagged for fence imbalance
9. **Normal output** with no failure/leakage signatures → passes through normally
10. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 19 (this spec, LLM Output Integrity)
    |
    +---> Complements: Spec 2 (JSON validation) — this covers non-JSON files + pre-content failures
    +---> Complements: Spec 3 (content-size guard) — this covers content semantics
    +---> Subsumes: former Spec 20 (Write-Path Failure Detection) — merged here

Prerequisites: None (standalone integrity fix)
```
