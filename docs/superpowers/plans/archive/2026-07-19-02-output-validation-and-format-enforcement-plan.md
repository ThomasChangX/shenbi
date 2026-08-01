# Output Validation and Format Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add layered JSON validation defense (pre-write recovery that requires schema + required-field completeness, G2 multi-concatenation detection, control character sanitization), create a dedicated revision G4 checker that works WITHIN the DecisionsDoc schema and returns a JSON result string, enrich G4 retry feedback with format examples, add lenient parsing for the two genuine resonance-verdict gaps (**判定** and Verdict:), and ensure every revision route writes a DecisionsDoc-compliant decisions file.

**Architecture:** Pre-write validation in `dispatch_helper.py` uses `json.JSONDecoder().raw_decode()` to recover the dominant corruption pattern — trailing markdown after a single valid JSON object. Recovery is tightened: after truncation, the recovered object must pass `DecisionsDoc.model_validate` (schema + required-field completeness); otherwise raise rather than persisting a structurally-invalid file. A new `g4/chapter_revision.py` checker validates the `adjustments` array (NOT a non-existent `changes` array) WITHIN the existing `DecisionsDoc` schema and returns a JSON result string for `make_composite_checker` compatibility. `G4_FORMAT_EXAMPLES` dict in `chapter_loop.py` enriches retry feedback. Resonance G4 verdict matching already accepts both `:` and `：` — only the two genuine gaps (`**判定**` markdown bold and `Verdict:` English prefix) are added. Guard ordering in `_write_parsed_outputs`: sanitize → validate JSON → content-size guard → truth file routing → wildcard → safe_write.

**Tech Stack:** Python 3.11+, pathlib, structlog, json, re, pydantic

## Global Constraints

- Dominant corruption pattern: valid JSON + trailing markdown after a single JSON object (NOT multi-JSON concatenation — that earlier claim was FALSE; no repo file has multiple `$schema` keys)
- Valid JSON + trailing markdown: Layer 1 truncates to first valid JSON object, then requires schema + required-field completeness before recovering; otherwise raises ValueError
- 3+ concatenated JSON objects: Layer 1 extracts first + Layer 2 reports (defensive measure against future retry-loop concatenation; not currently observed)
- Completely invalid JSON: Layer 1 raises ValueError (stops the pipeline rather than persisting corrupt data)
- Revision decisions conform to `DecisionsDoc` schema (`extra="forbid"`): use `selections` and `adjustments`, NOT a `changes` array
- Valid spot-fix revision (non-empty `adjustments`, each rationale >= 20 chars): PASS
- Valid no-op revision (`adjustments: []` with a `selections` entry documenting the skip): PASS
- Empty `adjustments` without a documented skip in `selections`: HARD FAIL
- Adjustment with rationale < 20 chars: HARD FAIL
- JSON syntax error in revision output: HARD FAIL (caught by g4_decisions)
- 5 consecutive resonance audits: retry count <= 1 per chapter
- The two genuine verdict gaps (`**判定**` markdown bold, `Verdict:` English prefix) match correctly; the existing regex already accepts both `:` and `：`
- All 56 chapters have `revision-decisions.json` conforming to DecisionsDoc schema regardless of route
- 0 illegal control characters in any staging or final JSON file
- Regression: `just check` passes fully

---

### Task 1: Add Pre-Write JSON Validation with `raw_decode()` Recovery

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_write_parsed_outputs`, around line 316)
- Test: `tests/unit/pipeline/test_dispatch_helper.py` (create if not exists)

**Interfaces:**
- Consumes: JSON content from LLM output parsing
- Produces: `_validate_json_output(content, path) -> str` returning cleaned content, raises ValueError on unrecoverable

**Recovery tightening (from spec §3 Layer 1):** The dominant corruption pattern (61.8% of decisions files) is a valid JSON object followed by trailing markdown — NOT multi-JSON concatenation (the earlier "Ch5 has 35 concatenated JSONs" claim was FALSE; no repo file has multiple `$schema` keys). Recovery via `raw_decode()` truncates to the first complete JSON object. After truncation, the recovered object MUST pass schema validation (`DecisionsDoc.model_validate` for `shenbi-decisions-v1`) AND required-field completeness before it is accepted — otherwise raise `ValueError` rather than persisting a structurally-incomplete file. This prevents recovering a truncated-tail object that is missing required fields.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for JSON validation in dispatch_helper.

The dominant corruption pattern (verified by filesystem audit) is a valid
JSON object followed by trailing markdown — NOT multi-JSON concatenation.
"""
import json
import tempfile
from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _validate_json_output


def test_validate_json_passes_clean_json():
    """Clean JSON passes validation unchanged."""
    content = json.dumps({"key": "value", "number": 42}, ensure_ascii=False)
    result = _validate_json_output(content, Path("test.json"))
    assert json.loads(result) == {"key": "value", "number": 42}


def test_validate_json_truncates_trailing_markdown():
    """Dominant pattern: valid JSON + trailing markdown -> truncate to first object."""
    content = '{"key": "value"}\n\n---\n**G4 failure summary:**\n- Fixed X\n'
    result = _validate_json_output(content, Path("test.json"))
    parsed = json.loads(result)
    assert parsed == {"key": "value"}
    assert "G4 failure summary" not in result


def test_validate_json_recovers_decisions_with_complete_schema():
    """A shenbi-decisions-v1 object + trailing markdown passes schema + recovers."""
    valid_decisions = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-drafting",
        "chapter": 5,
        "selections": [],
        "adjustments": [],
        "produced_at": "2026-07-19T00:00:00+00:00",
    }
    content = json.dumps(valid_decisions, ensure_ascii=False) + (
        "\n\n---\n\n**两项 G4 失败修复摘要：**\n1. 修正转折词。\n")
    result = _validate_json_output(content, Path("chapter-5-decisions.json"))
    parsed = json.loads(result)
    assert parsed["$schema"] == "shenbi-decisions-v1"
    assert parsed["chapter"] == 5
    assert "G4 失败修复摘要" not in result


def test_validate_json_recovers_revision_decisions_adjustments():
    """A revision decisions object with non-empty adjustments recovers."""
    valid_rev = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-chapter-revision",
        "chapter": 5,
        "selections": [],
        "adjustments": [
            {"issue_id": "resonance.sentiment", "severity": "high",
             "handling": "explicit_callout", "rationale": "Dialogue lacked emotional grounding in scene."}
        ],
        "produced_at": "2026-07-19T00:00:00+00:00",
    }
    content = json.dumps(valid_rev, ensure_ascii=False) + "\n\nSummary text."
    result = _validate_json_output(content, Path("chapter-5-revision-decisions.json"))
    parsed = json.loads(result)
    assert parsed["adjustments"][0]["issue_id"] == "resonance.sentiment"


def test_validate_json_raises_when_recovered_object_missing_required_fields():
    """Recovery tightened: if the recovered object fails DecisionsDoc schema
    (missing required fields), raise rather than persisting an incomplete file."""
    # Object with trailing markdown but MISSING required fields (no skill/chapter/...)
    incomplete = {"$schema": "shenbi-decisions-v1", "note": "partial"}
    content = json.dumps(incomplete) + "\n\n---\ntail markdown"
    with pytest.raises(ValueError, match="schema|incomplete|unrecoverable"):
        _validate_json_output(content, Path("chapter-5-decisions.json"))


def test_validate_json_handles_multiple_concatenated_json_defensively():
    """Defensive (not the dominant pattern): multiple concatenated JSON objects
    extracts only the first, then validates it against schema. If the first
    object is not a decisions doc, the non-decisions branch returns it as-is."""
    content = '{"a":1}\n{"b":2}\n{"c":3}'
    result = _validate_json_output(content, Path("test.json"))
    parsed = json.loads(result)
    assert parsed == {"a": 1}
    assert "b" not in result


def test_validate_json_raises_on_unrecoverable():
    """Completely invalid JSON (no recoverable object) raises ValueError."""
    content = "not json at all"
    with pytest.raises(ValueError, match="unrecoverable"):
        _validate_json_output(content, Path("test.json"))


def test_validate_json_skips_non_json_files():
    """Non-JSON files are returned unchanged."""
    content = "# Chapter 5\n\n## Section 1\nProse content here."
    result = _validate_json_output(content, Path("chapter-5.md"))
    assert result == content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: FAIL with `ImportError: cannot import name '_validate_json_output'`

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/dispatch_helper.py` (before `_write_parsed_outputs`). Recovery is tightened: after `raw_decode()` truncation, a `shenbi-decisions-v1` object must pass `DecisionsDoc.model_validate` (schema + required-field completeness) before being accepted; otherwise raise.

```python
def _validate_json_output(content: str, path: Path) -> str:
    """Validate and clean JSON content before writing to disk.

    Recovery policy (tightened per spec §3 Layer 1):
    - Clean JSON parses and is returned unchanged.
    - The dominant corruption pattern (valid JSON + trailing markdown) is
      recovered via ``json.JSONDecoder().raw_decode()`` (truncates to the
      first complete JSON object).
    - After truncation, if the recovered object declares
      ``$schema == "shenbi-decisions-v1"`` it MUST pass
      ``DecisionsDoc.model_validate`` (schema + required-field completeness).
      A recovered object missing required fields raises ValueError rather
      than being persisted (prevents recovering a truncated-tail fragment).
    - Non-decisions JSON files (no matching ``$schema``) are returned as-is
      after truncation.
    - Completely unrecoverable content raises ValueError.

    Args:
        content: Raw content to validate.
        path: Target file path (used to check extension and for error messages).

    Returns:
        Cleaned JSON string.

    Raises:
        ValueError: If content is JSON-typed but unrecoverable, or if a
            recovered decisions object fails schema validation.
    """
    if not path.suffix == ".json":
        return content

    # Try strict parse first — fastest path for clean JSON
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass

    # Recovery: extract first complete JSON object
    decoder = json.JSONDecoder()
    try:
        clean_data, end_pos = decoder.raw_decode(content)
    except json.JSONDecodeError as e:
        log.error("decisions_json_unrecoverable", path=str(path), error=str(e))
        raise ValueError(
            f"Decisions JSON invalid and unrecoverable for {path}: {e}"
        ) from e

    # Tightened recovery: a shenbi-decisions-v1 object must pass schema +
    # required-field completeness before being accepted. This prevents
    # recovering a truncated-tail fragment that is missing required fields.
    if isinstance(clean_data, dict) and clean_data.get("$schema") == "shenbi-decisions-v1":
        try:
            from shenbi.contracts.schemas.decisions import DecisionsDoc
            DecisionsDoc.model_validate(clean_data)
        except (ValidationError, ImportError) as e:
            log.error(
                "decisions_json_recovered_but_schema_incomplete",
                path=str(path), error=str(e),
            )
            raise ValueError(
                f"Recovered decisions JSON for {path} failed schema validation "
                f"(missing required fields): {e}"
            ) from e

    log.warning(
        "decisions_json_truncated",
        path=str(path),
        original_len=len(content),
        cleaned_len=end_pos,
    )
    return json.dumps(clean_data, ensure_ascii=False, indent=2)
```

Then integrate into `_write_parsed_outputs` at line 316. Before the `safe_write(full_path, content)` call:

```python
# Replace line 316: safe_write(full_path, content)
# With:
try:
    content = _validate_json_output(content, full_path)
except ValueError as e:
    log.error("output_validation_failed", path=rel_path, error=str(e))
    raise  # Pipeline must stop rather than persist corrupt data

safe_write(full_path, content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_dispatch_helper.py src/shenbi/pipeline/dispatch_helper.py
git commit -m "feat: add pre-write JSON validation with raw_decode() recovery"
```

---

### Task 2: Add Control Character Sanitization

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add `sanitize_json_content()`, integrate into `_write_parsed_outputs`)
- Test: `tests/unit/pipeline/test_dispatch_helper.py` (add tests)

**Interfaces:**
- Consumes: Raw JSON content from LLM output
- Produces: `sanitize_json_content(content: str) -> str` with illegal control characters removed

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/pipeline/test_dispatch_helper.py

from shenbi.pipeline.dispatch_helper import sanitize_json_content


def test_sanitize_strips_illegal_control_characters():
    """Removes control characters except \\n, \\r, \\t."""
    # Build string with illegal control chars
    content = '{"key": "val\x00\x01\x02\x08\x0b\x0c\x0e\x1fue"}'
    result = sanitize_json_content(content)
    assert "\x00" not in result
    assert "\x01" not in result
    assert "\x08" not in result
    assert "value" in result


def test_sanitize_preserves_legal_control_characters():
    """Preserves \\n, \\r, \\t which are valid in JSON strings."""
    content = '{"text": "line1\\nline2\\r\\n\\tindented"}'
    result = sanitize_json_content(content)
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result


def test_sanitize_handles_clean_input():
    """Clean input is returned unchanged."""
    content = '{"key": "value"}'
    result = sanitize_json_content(content)
    assert result == content


def test_sanitize_handles_chinese_characters():
    """Chinese characters are preserved."""
    content = '{"name": "林烽", "status": "在场"}'
    result = sanitize_json_content(content)
    assert "林烽" in result
    assert "在场" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::test_sanitize_strips_illegal_control_characters -v`
Expected: FAIL (ImportError: sanitize_json_content not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/dispatch_helper.py`:

```python
import re as _re

# Regex matching control characters EXCEPT newline (\n), carriage return (\r),
# and tab (\t) which are valid in JSON strings when properly escaped.
_ILLEGAL_CTRL_RE = _re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def sanitize_json_content(content: str) -> str:
    """Remove illegal control characters from JSON content.

    JSON spec (RFC 8259) only permits specific control characters
    (``\\n``, ``\\r``, ``\\t``) within strings. All other control
    characters in the range ``0x00-0x1F`` are stripped before write.

    This applies to both staging and final paths equally.

    Args:
        content: Raw JSON string to sanitize.

    Returns:
        Sanitized string with illegal control characters removed.
    """
    return _ILLEGAL_CTRL_RE.sub("", content)
```

Then integrate into `_write_parsed_outputs`. Sanitize BEFORE validation (control characters can break JSON parsing), following the cross-spec guard ordering.

**Guard ordering in `_write_parsed_outputs` (defined across Specs 1/2/3/9 — the order MUST be):**

1. **Sanitize** control characters (this task, Spec 2 Layer 3) — strips illegal control chars that would break the JSON parse in step 2
2. **Validate JSON** + recover (Task 1 of this plan, Spec 2 Layer 1) — `raw_decode()` recovery + schema completeness check
3. **Content-size guard** for chapter files (Spec 3 §3.2) — refuse writes < 20% of original chapter prose
4. **Truth file mode routing** via `write_truth_file` (Spec 1 §3.2) — upsert instead of overwrite for cumulative files
5. **Wildcard write-path resolution** (Spec 9 §3.2.1)
6. **`safe_write`** call (original)

```python
# In _write_parsed_outputs, BEFORE the _validate_json_output call:
if full_path.suffix == ".json":
    content = sanitize_json_content(content)
```

Because sanitization runs before validation, `_validate_json_output` sees clean content. (Task 1's `_validate_json_output` integration call and `safe_write` remain in their positions relative to this new sanitize line — sanitize is the first guard, validate is the second.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v -k "sanitize or validate"`
Expected: PASS (all sanitize and validate tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_dispatch_helper.py src/shenbi/pipeline/dispatch_helper.py
git commit -m "feat: add control character sanitization for JSON outputs"
```

---

### Task 3: Add Multi-JSON Concatenation Detection in G2

**Files:**
- Modify: `src/shenbi/gates/g2.py` (add G2.dec.4 check, around line 85-90)
- Test: `tests/unit/gates/test_g2.py` (add test for new check)

**Interfaces:**
- Consumes: JSON file content during G2 gate check
- Produces: `G2.dec.4` failure when multiple `"$schema"` keys found

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/gates/test_g2.py (create if not exists)

import json
import tempfile
from pathlib import Path

from shenbi.gates.g2 import gate_G2


def test_g2_dec4_detects_concatenated_json():
    """G2.dec.4 fails when multiple JSON objects exist in one file."""
    with tempfile.TemporaryDirectory() as tmp:
        # Create a file with two concatenated decision JSONs
        decisions_json = Path(tmp) / "chapter-5-decisions.json"
        obj1 = {"$schema": "shenbi-decisions-v1", "skill": "chapter-drafting"}
        obj2 = {"$schema": "shenbi-decisions-v1", "skill": "chapter-revision"}
        content = json.dumps(obj1) + "\n" + json.dumps(obj2)
        decisions_json.write_text(content)

        result = gate_G2([str(decisions_json)], file_type="decisions")
        assert "G2.dec.4" in result
        assert "FAIL" in result


def test_g2_dec4_passes_single_json():
    """G2.dec.4 passes when only one JSON object is present."""
    with tempfile.TemporaryDirectory() as tmp:
        decisions_json = Path(tmp) / "chapter-5-decisions.json"
        content = json.dumps({
            "$schema": "shenbi-decisions-v1",
            "skill": "chapter-drafting",
        })
        decisions_json.write_text(content)

        result = gate_G2([str(decisions_json)], file_type="decisions")
        assert "G2.dec.4" not in result or "PASS" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/test_g2.py::test_g2_dec4_detects_concatenated_json -v`
Expected: FAIL (no G2.dec.4 detected, assertion error)

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/gates/g2.py`, in the `gate_G2` function, inside the `file_type == "decisions"` branch, add the G2.dec.4 multi-JSON check **BEFORE** `data = json.loads(content)`. The check MUST run before `json.loads()` because concatenated JSON (`{"a":1}\n{"b":2}`) makes `json.loads()` raise `JSONDecodeError` (it does not accept trailing data after the first object), so the check would be unreachable if placed after the parse.

```python
# G2.dec.4 — multi-JSON concatenation detection (MUST run BEFORE json.loads())
# (G4 retry feedback can cause LLM to concatenate old + new JSON under
# one ### FILE: marker. This catches it early.)
#
# CRITICAL ORDERING: json.loads() raises JSONDecodeError on concatenated JSON
# ("Extra data" error), so this check must execute first. If we placed it
# after data = json.loads(content), the line above would raise before the
# check is ever reached, making the check dead code.
if content.count('"$schema"') > 1:
    mf.append({
        "id": "G2.dec.4",
        "file": fp,
        "s": "FAIL",
        "r": f"multiple JSON objects concatenated ({content.count(chr(34) + '$schema' + chr(34))} schemas found)",
    })
    continue  # skip the json.loads() below for this file — it would raise

# Now safe to parse a (single-object) decisions JSON:
data = json.loads(content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/test_g2.py::test_g2_dec4_detects_concatenated_json tests/unit/gates/test_g2.py::test_g2_dec4_passes_single_json -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/gates/test_g2.py src/shenbi/gates/g2.py
git commit -m "feat: add G2.dec.4 multi-JSON concatenation detection"
```

---

### Task 4: Create Dedicated Revision G4 Checker (DecisionsDoc Schema, JSON Result String)

**Files:**
- Create: `src/shenbi/gates/g4/chapter_revision.py`
- Modify: `src/shenbi/gates/g4/generic.py:237` (route `shenbi-chapter-revision` to `make_composite_checker(g4_decisions, g4_chapter_revision)`)
- Test: `tests/unit/gates/g4/test_chapter_revision.py`

**Interfaces:**
- Consumes: Revision decisions JSON file paths; the existing `DecisionsDoc` schema (`contracts/schemas/decisions.py:69-83`, `extra="forbid"`)
- Produces: `g4_chapter_revision(fps, rd, project_dir, repo_root) -> str` returning a JSON result string for `make_composite_checker`

**Critical schema constraint (from spec §3 G4 Revision Checker Upgrade):** Revision decisions files conform to `DecisionsDoc` — they have `selections` and `adjustments` arrays, NOT a `changes` array. `generic.py:237` already routes `shenbi-chapter-revision` to `g4_decisions`, so the LLM is told to produce `selections`/`adjustments`. The new checker MUST validate revision-specific content WITHIN the existing schema — do NOT invent `changes`/`route`/`skip_reason` fields (they would fail `extra="forbid"`).

**Return type (from spec §3 Return type correction):** The function returns a JSON result string matching the G4 checker protocol. `make_composite_checker` (`decisions_validator.py:87`) calls `json.loads(existing_result)` and expects `{"status": "...", "checks": [...], "must_fix": [...]}`. Do NOT return a bare `list[str]` — that breaks `make_composite_checker`. Status values: `PASS` or `HARD_FAIL`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for G4 chapter_revision checker.

Revision decisions conform to DecisionsDoc: selections + adjustments arrays
(NOT a changes array). The checker validates adjustment content semantics
within that schema and returns a JSON result string for make_composite_checker.
"""
import json
import tempfile
from pathlib import Path

from shenbi.gates.g4.chapter_revision import g4_chapter_revision


def _write_json(tmpdir: Path, filename: str, data: dict) -> Path:
    path = tmpdir / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def _parse_result(result: str) -> dict:
    """The checker returns a JSON result string — parse it for assertions."""
    return json.loads(result)


def test_valid_spot_fix_revision_passes():
    """Spot-fix with non-empty adjustments (each rationale >= 20 chars) passes."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(d, "chapter-5-revision-decisions.json", {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {
                    "issue_id": "resonance.sentiment",
                    "severity": "high",
                    "handling": "explicit_callout",
                    "rationale": "Replace parameterized prose with human sensory scene.",
                },
                {
                    "issue_id": "resonance.immersion",
                    "severity": "medium",
                    "handling": "explicit_callout",
                    "rationale": "Remove system-term enumeration, add dialogue setup.",
                },
            ],
            "produced_at": "2026-07-19T00:00:00+00:00",
        })

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "PASS"
        assert parsed["must_fix"] == []


def test_valid_no_op_revision_passes():
    """No-op with empty adjustments but a documented skip in selections passes."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(d, "chapter-5-revision-decisions.json", {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [
                {"target": "no_revision_needed", "selected": [],
                 "basis": "arc_relevance", "severity": "low", "omitted": []}
            ],
            "adjustments": [],
            "produced_at": "2026-07-19T00:00:00+00:00",
        })

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "PASS"


def test_empty_adjustments_without_skip_documentation_fails():
    """Empty adjustments with no skip selection in selections is HARD FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(d, "chapter-5-revision-decisions.json", {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [],
            "produced_at": "2026-07-19T00:00:00+00:00",
        })

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("empty_adjustments" in m for m in parsed["must_fix"])


def test_adjustment_with_thin_rationale_fails():
    """An adjustment whose rationale is < 20 chars is a HARD FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(d, "chapter-5-revision-decisions.json", {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {"issue_id": "x", "severity": "high",
                 "handling": "compensate_via_pacing", "rationale": "too short"},
            ],
            "produced_at": "2026-07-19T00:00:00+00:00",
        })

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("thin_rationale" in m for m in parsed["must_fix"])


def test_invalid_json_fails():
    """JSON syntax error in revision output is reported (g4_decisions also catches it)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = d / "chapter-5-revision-decisions.json"
        path.write_text("{invalid json")

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("invalid_json" in m for m in parsed["must_fix"])


def test_result_is_json_string_compatible_with_composite_checker():
    """Return value is a JSON string parseable into {status, checks, must_fix}."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(d, "chapter-5-revision-decisions.json", {
            "$schema": "shenbi-decisions-v1", "skill": "shenbi-chapter-revision",
            "chapter": 5, "selections": [], "adjustments": [],
            "produced_at": "2026-07-19T00:00:00+00:00",
        })
        result = g4_chapter_revision([str(path)])
        # make_composite_checker (decisions_validator.py:87) does json.loads(existing_result)
        parsed = json.loads(result)
        assert set(parsed.keys()) >= {"status", "checks", "must_fix"}
        assert parsed["status"] in ("PASS", "HARD_FAIL")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_chapter_revision.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
"""G4 checker for shenbi-chapter-revision outputs.

Validates revision-specific content WITHIN the DecisionsDoc schema
(selections/adjustments), NOT against a non-existent `changes` array.
DecisionsDoc has `extra="forbid"`, so the checker must not invent fields.

Returns a JSON result string matching the G4 checker protocol:
make_composite_checker (decisions_validator.py:87) does
json.loads(existing_result) and expects {"status", "checks", "must_fix"}.
"""
from __future__ import annotations

import json
from pathlib import Path

# Minimum rationale length per adjustment entry (the Adjustment model requires
# `rationale` but does not enforce a minimum length).
_MIN_RATIONALE_LEN = 20


def g4_chapter_revision(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """Validate revision decisions for content quality within DecisionsDoc.

    Works WITHIN the existing schema (selections/adjustments). Checks:
        - If ``adjustments`` is empty, ``selections`` MUST document a no-op/
          skip decision (e.g. target contains 'no_revision'/'skip').
        - Each adjustment's ``rationale`` must be >= 20 characters.

    Returns:
        A JSON result string: ``{"status": "PASS"|"HARD_FAIL",
        "checks": [...], "must_fix": [...]}``. This shape is what
        ``make_composite_checker`` expects via ``json.loads(existing_result)``.
    """
    issues: list[str] = []

    for fp in fps or []:
        p = Path(fp)
        if "revision" not in p.name or p.suffix != ".json":
            continue  # Only check revision decisions JSON

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            issues.append(f"G4.rev.invalid_json:{p.name}")
            continue

        if not isinstance(data, dict):
            issues.append(f"G4.rev.not_object:{p.name}")
            continue

        adjustments = data.get("adjustments", [])

        # HARD: if no adjustments, the revision mode must be documented
        # in selections (a no-op/skip decision).
        if not adjustments:
            selections = data.get("selections", [])
            has_skip_selection = any(
                isinstance(s, dict) and (
                    "no_revision" in str(s.get("target", "")).lower()
                    or "skip" in str(s.get("target", "")).lower()
                    or "skip" in str(s.get("basis", "")).lower()
                )
                for s in selections
            )
            if not has_skip_selection:
                issues.append(
                    f"G4.rev.empty_adjustments_no_skip:{p.name} -- "
                    f"revision has zero adjustments and no documented skip reason"
                )

        # HARD: each adjustment must have substantive rationale (>= 20 chars)
        for i, adj in enumerate(adjustments):
            if not isinstance(adj, dict):
                issues.append(f"G4.rev.adjustment_{i}_not_object:{p.name}")
                continue
            rationale = str(adj.get("rationale", ""))
            if len(rationale) < _MIN_RATIONALE_LEN:
                issues.append(
                    f"G4.rev.adjustment_{i}_thin_rationale:{p.name} -- "
                    f"rationale must be >= {_MIN_RATIONALE_LEN} chars, got {len(rationale)}"
                )

    # Return a JSON result string matching the G4 checker protocol.
    # make_composite_checker (decisions_validator.py:87) does
    # json.loads(existing_result) and expects {"status","checks","must_fix"}.
    return json.dumps({
        "status": "PASS" if not issues else "HARD_FAIL",
        "checks": issues,
        "must_fix": issues,
    }, ensure_ascii=False)
```

Then integrate in `src/shenbi/gates/g4/generic.py:237`. The existing routing sends `shenbi-chapter-revision` to `g4_decisions` only. Replace it with a composite checker so BOTH the JSON syntax/schema check AND the revision-content check run:

```python
# In generic.py around line 237, where skill -> checker routing is defined:
from shenbi.gates.g4.decisions_validator import make_composite_checker, g4_decisions
from shenbi.gates.g4.chapter_revision import g4_chapter_revision

# Route shenbi-chapter-revision to BOTH the schema check and the revision-
# content check. make_composite_checker partitions files by extension and
# merges the JSON result strings from both checkers.
"shenbi-chapter-revision": make_composite_checker(g4_decisions, g4_chapter_revision),
```

(Adjust the exact routing-table syntax to match what `grep` finds in `generic.py` at execution time. The key requirement: `shenbi-chapter-revision` runs both `g4_decisions` and `g4_chapter_revision`, and the composite result is what the pipeline consumes.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_chapter_revision.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/gates/g4/test_chapter_revision.py src/shenbi/gates/g4/chapter_revision.py src/shenbi/gates/g4/generic.py
git commit -m "feat: add G4 revision checker (DecisionsDoc adjustments, JSON result string)"
```

---

### Task 5: Ensure Every Revision Route Writes a DecisionsDoc-Compliant Decisions File

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (revision step success handler, around line 1243-1286 — NOT line 1438 which is the resonance path)
- Test: `tests/unit/pipeline/test_revision_decisions_fallback.py`

**Interfaces:**
- Consumes: Revision step completion status
- Produces: Minimal `revision-decisions.json` written for no-revision routes, conforming to `DecisionsDoc`

**Critical schema constraint (from spec §3 Ensure Every Revision Route):** The fallback file MUST conform to `DecisionsDoc` (`extra="forbid"`) — fields `$schema`, `skill`, `chapter`, `selections`, `adjustments`, `produced_at`. It must NOT use `route`/`changes`/`rationale` keys that would fail `g4_decisions` validation. The integration point is the revision step success handler (~line 1243-1286, the `if "chapter-revision" in step.skill:` block), NOT line 1438 (that is the resonance path).

- [ ] **Step 1: Write the failing test**

```python
"""Tests for revision decisions fallback generation.

The fallback must conform to DecisionsDoc (extra="forbid"): $schema, skill,
chapter, selections, adjustments, produced_at. It must NOT use route/changes/
rationale keys.
"""
import json
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import _ensure_revision_decisions_exists


def test_fallback_generates_decisionsdoc_compliant_file_when_missing():
    """Missing revision-decisions.json -> fallback writes a DecisionsDoc file."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters_dir = project_dir / "chapters"
        chapters_dir.mkdir(parents=True)

        _ensure_revision_decisions_exists(project_dir, chapter=5)

        rev_path = chapters_dir / "chapter-5-revision-decisions.json"
        assert rev_path.exists()
        data = json.loads(rev_path.read_text())
        # DecisionsDoc required fields
        assert data["$schema"] == "shenbi-decisions-v1"
        assert data["skill"] == "shenbi-chapter-revision"
        assert data["chapter"] == 5
        assert data["adjustments"] == []
        assert "produced_at" in data
        # The skip decision is documented in selections, not a `route` key
        assert isinstance(data["selections"], list)
        assert any(
            "no_revision" in str(s.get("target", "")).lower()
            for s in data["selections"] if isinstance(s, dict)
        )
        # Must NOT contain forbidden keys
        assert "route" not in data
        assert "changes" not in data
        assert "rationale" not in data


def test_fallback_does_not_overwrite_existing():
    """If revision decisions already exist, fallback does nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters_dir = project_dir / "chapters"
        chapters_dir.mkdir(parents=True)

        existing = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {"issue_id": "x", "severity": "high",
                 "handling": "explicit_callout", "rationale": "Fix the dialogue pacing in scene."}
            ],
            "produced_at": "2026-07-19T00:00:00+00:00",
        }
        rev_path = chapters_dir / "chapter-5-revision-decisions.json"
        rev_path.write_text(json.dumps(existing))

        _ensure_revision_decisions_exists(project_dir, chapter=5)

        data = json.loads(rev_path.read_text())
        # Not overwritten — still has the non-empty adjustments
        assert len(data["adjustments"]) == 1


def test_fallback_only_creates_when_revision_was_routed():
    """Fallback only creates when revision routing was recorded in state."""
    from shenbi.pipeline.chapter_loop import _is_revision_routed
    assert _is_revision_routed(route="no_revision") is True
    assert _is_revision_routed(route="spot_fix") is True
    assert _is_revision_routed(route=None) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_revision_decisions_fallback.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`. The minimal file conforms to `DecisionsDoc` (`extra="forbid"`): `$schema`, `skill`, `chapter`, `selections`, `adjustments`, `produced_at` — NOT `route`/`changes`/`rationale`.

```python
def _is_revision_routed(route: str | None) -> bool:
    """Check if a revision route was actually assigned.

    Returns True for any non-None route, including 'no_revision'.
    """
    return route is not None


def _ensure_revision_decisions_exists(
    project_dir: Path, chapter: int, state=None, log=None,
) -> None:
    """Write a minimal revision decisions file if one does not exist.

    The file conforms to DecisionsDoc (extra="forbid"): $schema, skill,
    chapter, selections, adjustments, produced_at. The skip decision is
    documented in `selections` (not a `route` key). This ensures every
    chapter routed through revision (including no-revision) produces an
    audit-trail artifact.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number.
    """
    rev_path = project_dir / "chapters" / f"chapter-{chapter}-revision-decisions.json"
    if rev_path.exists():
        return

    if state is not None:
        ch_state = state.chapters.get(str(chapter))
        route = getattr(ch_state, "revision_route", None) if ch_state else None
        if not _is_revision_routed(route):
            return  # Chapter was never routed through revision

    from datetime import datetime, timezone
    from shenbi.safe_write import safe_write

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
    if log is not None:
        log.info("revision_decisions_fallback_written", chapter=chapter)
```

Then integrate into the revision step success handler (around line 1243-1286 in `chapter_loop.py`, in the `if "chapter-revision" in step.skill:` block — NOT at line 1438 which is the resonance path):

```python
# In the revision step success handler, after the revision step concludes:
_ensure_revision_decisions_exists(project_dir, chapter, state, log)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_revision_decisions_fallback.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_revision_decisions_fallback.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: ensure every revision route writes a DecisionsDoc-compliant decisions file"
```

---

### Task 6: Add G4 Format Examples for Retry Feedback Enrichment

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `G4_FORMAT_EXAMPLES` dict and `_enrich_g4_feedback()`)
- Test: `tests/unit/pipeline/test_g4_feedback.py`

**Interfaces:**
- Consumes: G4 failure list strings (check IDs)
- Produces: `_enrich_g4_feedback(failures: list[str]) -> str` with format examples appended

- [ ] **Step 1: Write the failing test**

```python
"""Tests for enriched G4 retry feedback."""
from shenbi.pipeline.chapter_loop import _enrich_g4_feedback


def test_enrich_adds_format_example_for_known_check():
    """Known check IDs get format example appended."""
    failures = ["G4.rr.verdict:chapter-1-resonance.md:no_valid_verdict"]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "判定: 通过" in result
    assert "G4.rr.verdict" in result


def test_enrich_adds_detail_table_example():
    """G4.rr.detail_table gets the scoring table format example."""
    failures = ["G4.rr.detail_table:chapter-2-resonance.md:missing_['裁判理由']"]
    result = _enrich_g4_feedback(failures)

    assert "评分明细表格式" in result
    assert "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |" in result


def test_enrich_adds_evidence_example():
    """G4.rr.evidence gets the file:line reference example."""
    failures = ["G4.rr.evidence:chapter-3-resonance.md:no_file_line_ref"]
    result = _enrich_g4_feedback(failures)

    assert "chapter-N.md L45-52" in result or "文件和行号" in result


def test_enrich_handles_unknown_checks():
    """Unknown check IDs get generic feedback without format examples."""
    failures = ["G4.unknown_check:file.md:some_issue"]
    result = _enrich_g4_feedback(failures)

    assert "G4.unknown_check" in result
    # Should not crash or add examples for unknown checks


def test_enrich_handles_multiple_failures():
    """Multiple failures all get documented with their examples."""
    failures = [
        "G4.rr.verdict:ch1-res.md:no_valid_verdict",
        "G4.rr.evidence:ch1-res.md:no_file_line_ref",
    ]
    result = _enrich_g4_feedback(failures)

    assert "校准门判定" in result
    assert "文件和行号" in result or "chapter-N.md" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_g4_feedback.py -v`
Expected: FAIL (ImportError: _enrich_g4_feedback not defined)

- [ ] **Step 3: Write minimal implementation**

Add to `src/shenbi/pipeline/chapter_loop.py`:

```python
# Format examples mapped to G4 check ID prefixes (used for retry feedback)
G4_FORMAT_EXAMPLES: dict[str, str] = {
    "G4.rr.detail_table": (
        "评分明细表格式：\n"
        "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |\n"
        "|------|------|------|--------|------|----------|\n"
        "| 情感落地 | 25 | 30 | 高 | chapter-N.md L45-52 > \"...\" | ... |\n"
        "注意：六列必须完整，不可缺列。"
    ),
    "G4.rr.verdict": (
        "校准门判定必须包含以下行：\n"
        "判定: 通过    （或：判定: 阻断  / 判定: 待人机复核）\n"
        "注意：'判定: ' 后必须有空格，且必须使用中文冒号"
    ),
    "G4.rr.evidence": (
        "证据列每行必须包含文件和行号引用，格式：\n"
        "chapter-N.md L45-52 > \"引用原文\"\n"
        "至少一行包含 Lnn 或 line nn 格式的行号引用。"
    ),
}


def _enrich_g4_feedback(failures: list[str]) -> str:
    """Build enriched retry feedback with format examples for each failed check.

    For each failure in ``failures``, extracts the check ID prefix and
    appends the corresponding format example from ``G4_FORMAT_EXAMPLES``.
    Failures without a known check ID receive generic retry guidance.

    Args:
        failures: List of G4 failure strings (e.g., "G4.rr.verdict:file.md:reason").

    Returns:
        A formatted feedback string suitable for inclusion in retry prompts.
    """
    lines = ["以下 G4 检查失败，请按指定格式修正：", ""]
    for f in failures:
        # Extract check ID prefix (e.g., "G4.rr.verdict" from "G4.rr.verdict:file:reason")
        check_prefix = f.split(":")[0] if ":" in f else f
        lines.append(f"- **{f}**")
        if check_prefix in G4_FORMAT_EXAMPLES:
            lines.append(f"  期望格式：")
            for fmt_line in G4_FORMAT_EXAMPLES[check_prefix].split("\n"):
                lines.append(f"  {fmt_line}")
        else:
            lines.append(f"  (请重新生成此检查的输出以达到标准格式)")
        lines.append("")
    return "\n".join(lines)
```

Then integrate into the retry feedback construction in `_handle_failure` (around line 383 in `chapter_loop.py`). Where retry feedback is assembled:

```python
# In _handle_failure, when building retry feedback for G4 failures:
if g4_failures:
    enriched = _enrich_g4_feedback(g4_failures)
    # Use enriched instead of bare failure list in the retry prompt
    retry_context = enriched
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_g4_feedback.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/pipeline/test_g4_feedback.py src/shenbi/pipeline/chapter_loop.py
git commit -m "feat: add G4 format examples for enriched retry feedback"
```

---

### Task 7: Add Verdict Parsing for the Two Genuine Gaps (**判定** and Verdict:)

**Files:**
- Modify: `src/shenbi/gates/g4/review_resonance.py` (around line 64, verdict matching)
- Test: `tests/unit/gates/g4/test_review_resonance.py` (add supplement-pattern tests)

**Interfaces:**
- Consumes: Resonance audit report content
- Produces: `_match_verdict(text)` that tries the existing pattern first, then the two genuine gap patterns

**What is and is NOT a gap (from spec §3 Add Lenient Parsing):** The existing regex at `review_resonance.py:64` is `r'判定\s*[:：]\s*(\S+)'` — it ALREADY accepts both half-width `:` and full-width `：` with optional whitespace, matches any non-whitespace token (validated against `_VERDICTS`), and is NOT anchored. So `判定: 通过`, `判定：阻断`, `判定:通过` (no space), and `## 判定：通过` (heading prefix) ALL already match. Only TWO genuine gaps remain:
1. `**判定**: 通过` — markdown bold wrapping (`**` breaks the `判定` prefix match)
2. `Verdict: PASS` — English verdict prefix (`判定` is not in the string)

Do NOT add patterns for the colon variant or no-space variant — they already work. Adding them would be redundant and misrepresents the existing code.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/gates/g4/test_review_resonance.py

from shenbi.gates.g4.review_resonance import _match_verdict


def test_match_verdict_standard_already_handled():
    """The existing pattern already matches the standard format."""
    assert _match_verdict("判定: 通过") == "通过"


def test_match_verdict_full_width_colon_already_handled():
    """Full-width colon is already accepted by the existing regex."""
    assert _match_verdict("判定：阻断") == "阻断"


def test_match_verdict_no_space_already_handled():
    """No space after colon is already accepted (\\s* is optional)."""
    assert _match_verdict("判定:通过") == "通过"


def test_match_verdict_bold_format_is_the_genuine_gap():
    """Genuine gap 1: '**判定**: 通过' (markdown bold) needs a supplement pattern."""
    assert _match_verdict("**判定**: 通过") == "通过"
    assert _match_verdict("**判定**：阻断") == "阻断"


def test_match_verdict_english_prefix_is_the_genuine_gap():
    """Genuine gap 2: 'Verdict: <token>' (English prefix) needs a supplement pattern.

    The token is validated against the Chinese verdict set, so an English PASS
    returns None (not in 通过/阻断/待人机复核). But a Verdict: line carrying a
    Chinese verdict token should match.
    """
    # English prefix + Chinese verdict token -> matches the token
    assert _match_verdict("Verdict: 通过") == "通过"
    # English prefix + English token not in verdict set -> None
    assert _match_verdict("Verdict: PASS") is None


def test_match_verdict_none_for_invalid():
    """Invalid verdict returns None."""
    assert _match_verdict("判定: maybe") is None
    assert _match_verdict("something else entirely") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_review_resonance.py::test_match_verdict_bold_format_is_the_genuine_gap -v`
Expected: FAIL (ImportError: `_match_verdict` not defined, or the bold/English cases are not matched by the existing single regex)

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/gates/g4/review_resonance.py`, add a helper that tries the EXISTING pattern first (so all already-handled variants keep working unchanged), then falls back to the TWO genuine gap patterns only.

```python
import re as _re

# The existing pattern (review_resonance.py:64) already handles:
#   - half-width : and full-width ：
#   - optional whitespace (\s*)
#   - any non-whitespace token (validated against _VERDICTS downstream)
#   - not anchored (## 判定：通过 heading-style also matches)
_EXISTING_VERDICT_RE = _re.compile(r"判定\s*[:：]\s*(\S+)")

# Only TWO genuine gaps remain (verified by testing the existing regex):
#   1. **判定**: 通过  (markdown bold wrapping breaks the 判定 prefix match)
#   2. Verdict: <token>  (English verdict prefix)
_GAP_VERDICT_PATTERNS = [
    _re.compile(r"\*\*判定\*\*\s*[:：]\s*(\S+)"),   # markdown bold
    _re.compile(r"Verdict\s*[:：]\s*(\S+)"),        # English prefix
]


def _match_verdict(text: str) -> str | None:
    """Match a resonance verdict token, trying the existing pattern first.

    The existing regex already covers the colon/full-width/no-space/heading
    variants. This helper adds ONLY the two genuine gaps: markdown bold
    (``**判定**``) and English prefix (``Verdict:``). The matched token is
    returned as-is; membership validation against the verdict set is the
    caller's responsibility (preserving the existing behavior).

    Args:
        text: Text content of the resonance report.

    Returns:
        The matched verdict token string, or ``None``.
    """
    match = _EXISTING_VERDICT_RE.search(text)
    if match:
        return match.group(1)
    for pattern in _GAP_VERDICT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None
```

Then update the verdict matching in `g4_review_resonance` (around line 64) to call `_match_verdict`, keeping the downstream `_VERDICTS` membership check so a non-verdict token still yields no verdict:

```python
# Replace the existing verdict extraction (around line 62-69):
# Old:
#     verdict_match = re.search(r"判定\s*[:：]\s*(\S+)", content)
#     if verdict_match:
#         for v in _VERDICTS:
#             if verdict_match.group(1).startswith(v):
#                 verdict = v
#                 break
# New: reuse _match_verdict (which tries existing pattern + the 2 gaps),
# then keep the existing _VERDICTS membership check.
verdict_token = _match_verdict(content)
if verdict_token:
    for v in _VERDICTS:
        if verdict_token.startswith(v):
            verdict = v
            break
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_review_resonance.py -v`
Expected: PASS (all verdict tests, including the bold and English-prefix gaps)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/gates/g4/test_review_resonance.py src/shenbi/gates/g4/review_resonance.py
git commit -m "feat: match the two genuine verdict gaps (**判定** and Verdict:) in resonance G4"
```

---
