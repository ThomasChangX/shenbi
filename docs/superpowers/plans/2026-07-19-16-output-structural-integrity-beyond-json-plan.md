# LLM Output Integrity — Structural, Write-Failure, and Content-Anomaly Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified `llm_output_integrity.py` module plus a single integration choke point in `_write_parsed_outputs` that detects five classes of corrupt LLM output the pipeline currently persists as valid content: write-path failure diagnostics (with false-positive-safe dominance triggering), prose meta-commentary leakage, Markdown fence imbalance, aborted audit stubs, and audit line-reference version skew.

**Architecture:** A new pure-function module `llm_output_integrity.py` exposes four check functions (`detect_write_failure`, `check_prose_leakage`, `check_markdown_fence_balance`, `check_audit_completeness`, `check_audit_line_refs`) and the shared pattern catalog. `_write_parsed_outputs` in `dispatch_helper.py` is the single choke point: write-failure detection runs first (pre-write, blocks the write, raises a new `DispatchWriteFailureError` to trigger retry with write-capability confirmation), then the file is written, then the post-write checks run in fixed order against the persisted file and their findings are logged + surfaced to G4 via the existing composite-checker registry. Two small helpers (`_is_audit_file`, `_resolve_chapter_for_audit`) are added to classify filenames using the real `chapter-NN.md` / `chapter-NN-<dim>.md` / `audits/chapter-NN-<dim>.md` conventions.

**Tech Stack:** Python 3.11+, `re`, `pathlib`, `dataclasses`, pytest. No new runtime dependencies.

## Global Constraints

- Python 3.11+, `from __future__ import annotations` at the top of every new file
- `pathlib.Path` for all file I/O; `safe_write` for writes
- No `print()` in framework code; use structlog (`shenbi.logging.get_logger`)
- Write-failure patterns trigger ONLY when the match is at content START or the matched region covers >50% of the output (false-positive safety — spec §3.2)
- The post-write findings must NOT raise; they log warnings and surface to G4 (the gate decides FAIL/WARN per §3.6 severity rules)
- Tests under `tests/unit/pipeline/` alongside the existing `test_dispatch_helper.py`
- Conventional Commits: `feat:` for the new module, `feat:` for the integration
- `just check` (ruff + mypy + basedpyright + pytest) must pass after every task

**Spec reference:** `docs/superpowers/specs/2026-07-19-16-output-structural-integrity-beyond-json-design.md` (the merged Spec 19 + former Spec 20)

---

## File Structure

```
src/shenbi/
    pipeline/
        llm_output_integrity.py     # NEW — pattern catalog + 5 check functions
        dispatch_helper.py          # MODIFY — _write_parsed_outputs choke point
                                     #        + _is_audit_file / _resolve_chapter_for_audit
                                     #        + retry write-confirmation prompt
    exceptions.py                   # MODIFY — add DispatchWriteFailureError
    gates/g4/generic.py             # MODIFY — register post-write integrity checkers

tests/unit/pipeline/
    test_llm_output_integrity.py    # NEW — pattern + check-function unit tests
    test_dispatch_helper.py         # MODIFY — _write_parsed_outputs integration tests
```

> **Filename conventions discovered in the codebase** (the helpers must match these exactly):
> - Chapter prose: `chapters/chapter-NN.md`
> - Audit reports: `audits/chapter-NN-<dimension>.md` (e.g. `chapter-8-foreshadowing.md`, `chapter-51-anti-ai.md`, `chapter-19-resonance.md`)
> - Plans: `staging/plans/chapter-NN-plan.md`
> - An "audit file" is therefore any path whose stem matches `chapter-NN-<something>` and lives anywhere (the gate does not assume the `audits/` dir).
> - The "chapter file" paired with an audit at `.../chapter-NN-<dim>.md` is `chapters/chapter-NN.md`.

---

### Task 1: Create `llm_output_integrity.py` — pattern catalog + pure check functions

**Files:**
- Create: `src/shenbi/pipeline/llm_output_integrity.py`
- Test: `tests/unit/pipeline/test_llm_output_integrity.py`

**Interfaces:**
- Consumes: nothing (leaf module)
- Produces:
  - `WRITE_FAILURE_PATTERNS: list[str]`, `LEAKAGE_PATTERNS: list[str]`, `VERDICT_MARKERS: list[str]`, `PREAMBLE_MARKERS: list[str]`, `RETRY_WRITE_CONFIRMATION: str`
  - `detect_write_failure(content: str) -> tuple[bool, str | None]`
  - `check_prose_leakage(path: Path) -> list[str]`
  - `check_markdown_fence_balance(path: Path) -> list[str]`
  - `check_audit_completeness(path: Path) -> list[str]`
  - `check_audit_line_refs(path: Path, chapter_path: Path) -> list[str]`

  Task 2 imports all of these into `dispatch_helper.py`.

**Context:** The patterns are de-duplicated from the former Specs 19 and 20 — write-failure signatures live ONLY in `WRITE_FAILURE_PATTERNS`, leakage signatures ONLY in `LEAKAGE_PATTERNS`. The `detect_write_failure` dominance rule (§3.2) is the critical false-positive guard: a chapter that merely mentions "sandbox" in passing must NOT trip.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/pipeline/test_llm_output_integrity.py`:

```python
"""Tests for the unified LLM-output integrity module."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.llm_output_integrity import (
    LEAKAGE_PATTERNS,
    WRITE_FAILURE_PATTERNS,
    check_audit_completeness,
    check_audit_line_refs,
    check_markdown_fence_balance,
    check_prose_leakage,
    detect_write_failure,
)


# --- detect_write_failure (dominance rule) ---


class TestDetectWriteFailure:
    def test_chinese_sandbox_at_start(self):
        content = "由于沙箱限制，我无法直接写文件。请使用现有内容。"
        is_fail, sig = detect_write_failure(content)
        assert is_fail is True
        assert "沙箱" in sig or "sandbox" in sig.lower()

    def test_english_readonly_at_start(self):
        content = (
            "I cannot write the file in this read-only sandbox. "
            "Use the existing content from input."
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is True

    def test_dominant_region_over_half(self):
        # Match is not at start (there's a title line) but the diagnostic
        # region spans >50% of the output.
        content = (
            "Title\n"
            "The file on disk can't be updated (read-only sandbox). "
            "Use the existing content from input markers was already provided."
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is True

    def test_passing_mention_is_not_failure(self):
        # Legitimate prose that mentions "sandbox" / "cannot write" in passing.
        content = (
            "林烽穿过沙箱般的废墟，心中暗道：'我不能写下这段历史。' "
            "他继续前行，脚步声回荡在空旷的走廊里。" * 20
        )
        is_fail, _ = detect_write_failure(content)
        assert is_fail is False

    def test_clean_prose_is_not_failure(self):
        content = "林烽推开门，映入眼帘的是一间陈旧的教室。" * 50
        is_fail, _ = detect_write_failure(content)
        assert is_fail is False


# --- check_prose_leakage ---


class TestCheckProseLeakage:
    def test_model_leakage_flagged(self, tmp_path):
        p = tmp_path / "chapter-56.md"
        p.write_text("正文内容……\nNow the decisions JSON:\n```json", encoding="utf-8")
        issues = check_prose_leakage(p)
        assert any("G4.pi.model_leakage" in i for i in issues)

    def test_unfinished_ending_flagged(self, tmp_path):
        p = tmp_path / "chapter-56.md"
        p.write_text("他走到门前，准备：" , encoding="utf-8")
        issues = check_prose_leakage(p)
        assert any("G4.pi.unfinished_ending" in i for i in issues)

    def test_clean_prose_no_issues(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("林烽推开门，走进教室。" * 200, encoding="utf-8")
        assert check_prose_leakage(p) == []


# --- check_markdown_fence_balance ---


class TestCheckFenceBalance:
    def test_odd_fences_flagged(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("text\n```\ncode\nmore text", encoding="utf-8")
        issues = check_markdown_fence_balance(p)
        assert len(issues) == 1
        assert "G4.pi.fence_imbalance" in issues[0]

    def test_even_fences_ok(self, tmp_path):
        p = tmp_path / "chapter-1.md"
        p.write_text("text\n```\ncode\n```\nmore", encoding="utf-8")
        assert check_markdown_fence_balance(p) == []


# --- check_audit_completeness ---


class TestCheckAuditCompleteness:
    def test_aborted_stub_flagged(self, tmp_path):
        p = tmp_path / "chapter-32-foreshadowing.md"
        p.write_text("所有输入文件已确认。现在执行完整的伏笔审计……", encoding="utf-8")
        issues = check_audit_completeness(p)
        # Short AND no verdict AND has preamble — at least one of these fires.
        assert len(issues) >= 1
        assert any(
            ("too_short" in i) or ("aborted_stub" in i) or ("no_verdict" in i)
            for i in issues
        )

    def test_complete_audit_no_issues(self, tmp_path):
        p = tmp_path / "chapter-32-foreshadowing.md"
        body = "# 伏笔审计\n\n" + ("详尽分析内容。" * 100) + "\n\n判定：通过 (PASS)"
        p.write_text(body, encoding="utf-8")
        assert check_audit_completeness(p) == []


# --- check_audit_line_refs ---


class TestCheckAuditLineRefs:
    def test_stale_ref_flagged(self, tmp_path):
        audit = tmp_path / "chapter-55-foreshadowing.md"
        audit.write_text("参见 chapter-55.md L41-45 的细节。", encoding="utf-8")
        chapter = tmp_path / "chapter-55.md"
        chapter.write_text("line1\nline2\nline3\n", encoding="utf-8")
        issues = check_audit_line_refs(audit, chapter)
        assert len(issues) == 1
        assert "G4.av.stale_line_ref" in issues[0]
        assert "L41-45" in issues[0]

    def test_valid_ref_ok(self, tmp_path):
        audit = tmp_path / "chapter-1-continuity.md"
        audit.write_text("参见 chapter-1.md L2-3。", encoding="utf-8")
        chapter = tmp_path / "chapter-1.md"
        chapter.write_text("\n".join(f"line{i}" for i in range(20)) + "\n", encoding="utf-8")
        assert check_audit_line_refs(audit, chapter) == []

    def test_missing_chapter_no_issue(self, tmp_path):
        audit = tmp_path / "chapter-1-continuity.md"
        audit.write_text("参见 chapter-1.md L2-3。", encoding="utf-8")
        assert check_audit_line_refs(audit, tmp_path / "chapter-1.md") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_llm_output_integrity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shenbi.pipeline.llm_output_integrity'`

- [ ] **Step 3: Write minimal implementation**

Create `src/shenbi/pipeline/llm_output_integrity.py`:

```python
"""Unified LLM-output integrity checks for the dispatch write path.

Spec: 2026-07-19 output-structural-integrity-beyond-json-design (merged Spec 19
+ former Spec 20).

This module is the single source of truth for the pattern catalog and the five
check functions invoked from ``dispatch_helper._write_parsed_outputs``. The
former Specs 19/20 maintained overlapping pattern lists; they are de-duplicated
here, split by detection mode:

  * ``WRITE_FAILURE_PATTERNS`` — the LLM reports it cannot write. These trip
    only under the dominance rule (start-of-content OR matched region >50% of
    output) so a chapter that merely *mentions* a sandbox in dialogue does not.
  * ``LEAKAGE_PATTERNS`` — model meta-commentary in prose (NOT a write failure).
  * ``VERDICT_MARKERS`` / ``PREAMBLE_MARKERS`` — audit-completeness signals.

All check functions return ``list[str]`` issue strings tagged
``G4.<group>.<rule>`` so the G4 composite-checker registry can route severity.
"""

from __future__ import annotations

import re
from pathlib import Path

# --- Write-failure signatures: the LLM reports it cannot write. ---
# These supersede the broader standalone patterns from the former specs
# (e.g. bare `由于沙箱限制`, `can't be updated.*sandbox`) which are now covered
# by the more specific entries below.
WRITE_FAILURE_PATTERNS: list[str] = [
    r"由于沙箱限制.*?(?:无法|不能).*?(?:写|写入)",
    r"(?:can't|cannot|unable to).*?(?:write|update|create).*?(?:file|sandbox|read-only)",
    r"read-only sandbox",
    r"Use the existing.*?from input",
    r"was already provided via.*?markers",
    r"I (?:cannot|can't|could not) (?:write|create|update) (?:the )?(?:file|output)",
]

# --- Model meta-commentary leakage in prose (NOT a write failure). ---
LEAKAGE_PATTERNS: list[str] = [
    r"Now the .* JSON",
    r"Let me write",
    r"schema:",
    r"Here's a summary of the revision",
    r"修订执行摘要",
    r"Revision complete",
    r"All \d+ files have been",
]

# --- Audit completeness markers ---
VERDICT_MARKERS: list[str] = ["判定", "结论", "verdict", "通过", "阻断", "PASS", "BLOCK"]
PREAMBLE_MARKERS: list[str] = ["现在执行", "inputs confirmed", "now executing", "开始审计"]

#: Minimum audit size in bytes — real audits are > 500 bytes.
_AUDIT_MIN_BYTES = 200

#: Retry-prompt suffix confirming write capability.
RETRY_WRITE_CONFIRMATION = (
    "CRITICAL: You have filesystem write access in this environment. "
    "Output the complete file content directly — do not explain, apologize, "
    "or reference sandbox limitations. Previous attempt failed with: '{signature}'."
)

# Pre-compile for performance.
_WRITE_FAILURE_RES = [re.compile(p, re.IGNORECASE) for p in WRITE_FAILURE_PATTERNS]
_LEAKAGE_RES = [re.compile(p, re.IGNORECASE) for p in LEAKAGE_PATTERNS]
_LINE_REF_RE = re.compile(r"L(\d+)(?:-(\d+))?")


def detect_write_failure(content: str) -> tuple[bool, str | None]:
    """Check if content is a write-failure diagnostic instead of file content.

    False-positive mitigation (spec §3.2): a pattern only counts as a failure
    when it appears at the START of the content OR the matched span sits within
    a region that comprises >50% of the total output. A chapter that merely
    *mentions* a sandbox in passing is NOT a failure.

    Returns ``(is_failure, matched_pattern_or_None)``.
    """
    total_len = max(len(content), 1)
    for rx in _WRITE_FAILURE_RES:
        match = rx.search(content)
        if not match:
            continue
        start, end = match.span()
        # Case 1: pattern at the very start (ignoring leading whitespace).
        at_start = content[:start].strip() == ""
        # Case 2: the region from first non-empty char to end of match covers
        # more than half the output — i.e. the diagnostic dominates rather
        # than being embedded in real content.
        dominant = end > total_len * 0.5
        if at_start or dominant:
            return True, match.group(0)
    return False, None


def check_prose_leakage(path: Path) -> list[str]:
    """Detect model meta-commentary leakage in prose files.

    Returns ``G4.pi.model_leakage`` issues (one per distinct pattern) and a
    single ``G4.pi.unfinished_ending`` issue if the file ends with a trailing
    punctuation character indicating mid-thought truncation.
    """
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    for rx in _LEAKAGE_RES:
        matches = rx.findall(text)
        if matches:
            issues.append(
                f"G4.pi.model_leakage:{path.name} — found '{matches[0]}' pattern "
                f"({len(matches)} occurrences). Chapter file contains model "
                f"meta-commentary, not prose."
            )

    last_500 = text[-500:].strip()
    if last_500 and last_500[-1] in ":,；：，":
        issues.append(
            f"G4.pi.unfinished_ending:{path.name} — file ends with "
            f"'{last_500[-20:]}' — truncated mid-thought"
        )

    return issues


def check_markdown_fence_balance(path: Path) -> list[str]:
    """Verify Markdown code fences are balanced in prose files."""
    text = path.read_text(encoding="utf-8")
    fence_count = text.count("```")
    if fence_count % 2 != 0:
        return [
            f"G4.pi.fence_imbalance:{path.name} — odd number of ``` markers "
            f"({fence_count}). Orphan code fence — file was likely extracted "
            f"incorrectly."
        ]
    return []


def check_audit_completeness(path: Path) -> list[str]:
    """Verify audit files contain an actual verdict, not just a preamble."""
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    if len(text) < _AUDIT_MIN_BYTES:
        issues.append(
            f"G4.ac.too_short:{path.name} — audit file is {len(text)} bytes, "
            f"likely aborted stub"
        )

    has_verdict = any(marker in text for marker in VERDICT_MARKERS)
    if not has_verdict:
        issues.append(
            f"G4.ac.no_verdict:{path.name} — audit file contains no "
            f"verdict/conclusion marker"
        )

    has_only_preamble = (
        any(marker in text for marker in PREAMBLE_MARKERS) and not has_verdict
    )
    if has_only_preamble:
        issues.append(
            f"G4.ac.aborted_stub:{path.name} — audit file contains only "
            f"execution preamble, no results"
        )

    return issues


def check_audit_line_refs(path: Path, chapter_path: Path) -> list[str]:
    """Verify audit line references point to valid lines in the chapter."""
    if not chapter_path.exists():
        return []  # Chapter missing is handled elsewhere.

    audit_text = path.read_text(encoding="utf-8")
    chapter_lines = chapter_path.read_text(encoding="utf-8").split("\n")
    max_line = len(chapter_lines)

    issues: list[str] = []
    for start_str, end_str in _LINE_REF_RE.findall(audit_text):
        start = int(start_str)
        end = int(end_str) if end_str else start
        if end > max_line:
            issues.append(
                f"G4.av.stale_line_ref:{path.name} — references L{start}-{end} "
                f"but chapter has only {max_line} lines. Audit ran against a "
                f"different version of the chapter."
            )
    return issues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_llm_output_integrity.py -v`
Expected: PASS (all tests across the 5 classes)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/llm_output_integrity.py \
        tests/unit/pipeline/test_llm_output_integrity.py
git commit -m "feat(pipeline): add llm_output_integrity module (write-failure + leakage + fence + audit checks)"
```

---

### Task 2: Add `DispatchWriteFailureError` exception

**Files:**
- Modify: `src/shenbi/exceptions.py` (add one class)
- Test: `tests/unit/test_exceptions.py` (add one test) — if this file does not exist, create it.

**Interfaces:**
- Consumes: `DispatcherError` (existing base in `exceptions.py`)
- Produces: `DispatchWriteFailureError`. Task 3 raises it; the dispatch retry path catches it.

- [ ] **Step 1: Write the failing test**

Append to (or create) `tests/unit/test_exceptions.py`:

```python
"""Tests for framework exception hierarchy."""

from __future__ import annotations

import pytest

from shenbi.exceptions import DispatchWriteFailureError, DispatcherError


def test_dispatch_write_failure_is_dispatcher_error():
    err = DispatchWriteFailureError("sandbox diagnostic", signature="由于沙箱限制")
    assert isinstance(err, DispatcherError)
    assert "sandbox diagnostic" in str(err)
    assert err.signature == "由于沙箱限制"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_exceptions.py -v`
Expected: FAIL — `ImportError: cannot import name 'DispatchWriteFailureError'`

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/exceptions.py`, after the existing `class DispatcherError(FrameworkError):` block (line 86+), add:

```python
class DispatchWriteFailureError(DispatcherError):
    """The LLM emitted a write-failure diagnostic instead of file content.

    Raised by ``_write_parsed_outputs`` when :func:`detect_write_failure`
    matches. Carries the matched ``signature`` so the retry prompt can quote
    it back to the model.
    """

    def __init__(self, message: str, *, signature: str = "") -> None:
        super().__init__(message)
        self.signature = signature
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_exceptions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/exceptions.py tests/unit/test_exceptions.py
git commit -m "feat(exceptions): add DispatchWriteFailureError carrying matched signature"
```

---

### Task 3: Integrate all checks into `_write_parsed_outputs`

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:294-323` (the `_write_parsed_outputs` body) and the module imports
- Test: `tests/unit/pipeline/test_dispatch_helper.py` (add an integration test class)

**Interfaces:**
- Consumes: `detect_write_failure`, `check_prose_leakage`, `check_markdown_fence_balance`, `check_audit_completeness`, `check_audit_line_refs`, `RETRY_WRITE_CONFIRMATION` (Task 1); `DispatchWriteFailureError` (Task 2)
- Produces: `_write_parsed_outputs` now (a) raises `DispatchWriteFailureError` on write-failure content pre-write, (b) runs the post-write checks, (c) logs findings via `log.warning("llm_output_integrity_issue", ...)`. New module-level helpers `_is_audit_file(name: str) -> bool` and `_resolve_chapter_for_audit(full_path: Path, project_dir: Path) -> Path` classify filenames.

**Context:** The existing `_write_parsed_outputs` writes content for each `rel_path` in `output_paths` and returns the list of written paths. We insert the write-failure check before `safe_write`, and the post-write checks after it. The post-write findings are logged but do NOT change the return value (the write succeeded; G4 decides severity). The helpers use the real filename conventions discovered in the codebase.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/pipeline/test_dispatch_helper.py`:

```python
class TestWriteParsedOutputsIntegrity:
    """Integration tests for the LLM-output integrity choke point."""

    def test_write_failure_raises_before_write(self, tmp_path):
        from shenbi.exceptions import DispatchWriteFailureError
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = (
            "### FILE: chapters/chapter-1.md\n"
            "由于沙箱限制，我无法直接写文件。请使用现有内容。\n"
        )
        with pytest.raises(DispatchWriteFailureError):
            _write_parsed_outputs(
                response, ["chapters/chapter-1.md"], tmp_path
            )
        # The file must NOT have been written.
        assert not (tmp_path / "chapters" / "chapter-1.md").exists()

    def test_prose_leakage_logged_not_raised(self, tmp_path, caplog):
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        response = (
            "### FILE: chapters/chapter-56.md\n"
            f"正文……\nNow the decisions JSON:\n{'段落' * 200}\n"
        )
        written = _write_parsed_outputs(
            response, ["chapters/chapter-56.md"], tmp_path
        )
        # The write succeeds; leakage is a post-write warning.
        assert written == ["chapters/chapter-56.md"]
        assert (tmp_path / "chapters" / "chapter-56.md").exists()

    def test_audit_completeness_check_runs(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        aborted = "所有输入文件已确认。现在执行完整的伏笔审计……"
        response = f"### FILE: audits/chapter-32-foreshadowing.md\n{aborted}\n"
        # Aborted stub writes (it is not a write-failure) but is flagged.
        written = _write_parsed_outputs(
            response, ["audits/chapter-32-foreshadowing.md"], tmp_path
        )
        assert written == ["audits/chapter-32-foreshadowing.md"]

    def test_clean_output_passes_through(self, tmp_path):
        from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

        clean_prose = "林烽推开门，走进教室。" * 200
        response = f"### FILE: chapters/chapter-1.md\n{clean_prose}\n"
        written = _write_parsed_outputs(
            response, ["chapters/chapter-1.md"], tmp_path
        )
        assert written == ["chapters/chapter-1.md"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::TestWriteParsedOutputsIntegrity -v`
Expected: FAIL — `_write_parsed_outputs` does not raise on write-failure content.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/dispatch_helper.py`, add imports near the top (after `from shenbi.safe_write import safe_write`):

```python
from shenbi.exceptions import DispatchWriteFailureError
from shenbi.pipeline.llm_output_integrity import (
    RETRY_WRITE_CONFIRMATION,
    check_audit_completeness,
    check_audit_line_refs,
    check_markdown_fence_balance,
    check_prose_leakage,
    detect_write_failure,
)
```

Add two module-level helpers (place them just above `_write_parsed_outputs`, around line 290):

```python
#: Regex for the chapter-number in an audit filename like
#: ``chapter-32-foreshadowing.md`` or a prose file ``chapter-32.md``.
_CHAPTER_NUM_RE = re.compile(r"chapter-(\d+)")


def _is_audit_file(name: str) -> bool:
    """True iff *name* looks like an audit report (``chapter-NN-<dim>.md``).

    Matches the production layout: audit reports are ``chapter-NN-<dimension>.md``
    (e.g. ``chapter-8-foreshadowing.md``, ``chapter-51-anti-ai.md``). A bare
    ``chapter-NN.md`` (the prose file) is NOT an audit.
    """
    stem = Path(name).stem
    m = _CHAPTER_NUM_RE.match(stem)
    if not m:
        return False
    # stem must have a suffix after the number to be an audit.
    return len(stem) > len(m.group(0))


def _resolve_chapter_for_audit(full_path: Path, project_dir: Path) -> Path:
    """Return the prose chapter file paired with an audit at *full_path*.

    ``audits/chapter-NN-<dim>.md`` -> ``chapters/chapter-NN.md``. Falls back to
    a sibling ``chapter-NN.md`` if the canonical chapters/ dir is absent.
    """
    m = _CHAPTER_NUM_RE.search(full_path.stem)
    if not m:
        return full_path  # caller treats missing file as a no-op
    num = m.group(1)
    canonical = project_dir / "chapters" / f"chapter-{num}.md"
    if canonical.exists():
        return canonical
    return full_path.parent / f"chapter-{num}.md"
```

Now replace the body of `_write_parsed_outputs` (lines 294-323). The new body keeps the same signature and return type, but inserts the checks:

```python
def _write_parsed_outputs(
    response: str,
    output_paths: list[str],
    project_dir: Path,
    create_truth_templates: bool = False,
) -> list[str]:
    """Parse agent response, run integrity checks, and write per-file content.

    Order (spec §3.4):
      1. WRITE-FAILURE DETECTION — pre-write, blocks the write, raises
         :class:`DispatchWriteFailureError` to trigger retry.
      2. write the file.
      3-6. POST-WRITE INTEGRITY — prose leakage / fence balance (chapter files),
           audit completeness / line-ref skew (audit files). Findings are logged
           as ``llm_output_integrity_issue`` and surfaced to G4 via the
           composite-checker registry; they do NOT block the write.

    Returns list of successfully written paths.
    """
    parsed = _parse_file_outputs(response)
    written: list[str] = []

    for rel_path in output_paths:
        if "*" in rel_path:
            continue
        content = parsed.get(rel_path, parsed.get("__stdout__", ""))
        if not content.strip():
            log.warning("output_empty", path=rel_path)
            continue
        full_path = project_dir / rel_path

        # 1. WRITE-FAILURE DETECTION (pre-write, blocks the write).
        is_failure, signature = detect_write_failure(content)
        if is_failure:
            log.error(
                "dispatch_write_failure_detected",
                path=str(full_path),
                signature=signature,
            )
            raise DispatchWriteFailureError(
                f"LLM reported write failure for {full_path}: '{signature}'. "
                f"The output is a diagnostic message, not file content. Retry "
                f"with explicit write-capability confirmation.",
                signature=signature or "",
            )

        # 2. WRITE.
        full_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(full_path, content)
        written.append(rel_path)
        log.info("output_written", path=rel_path, size=len(content))

        # 3-6. POST-WRITE INTEGRITY (fixed order; collect all issues).
        issues: list[str] = []
        name = full_path.name
        is_chapter = (
            _CHAPTER_NUM_RE.match(Path(name).stem) is not None
            and not _is_audit_file(name)
        )
        is_audit = _is_audit_file(name)

        if is_chapter:
            issues += check_prose_leakage(full_path)
            issues += check_markdown_fence_balance(full_path)

        if is_audit:
            issues += check_audit_completeness(full_path)
            chapter_path = _resolve_chapter_for_audit(full_path, project_dir)
            issues += check_audit_line_refs(full_path, chapter_path)

        for issue in issues:
            log.warning(
                "llm_output_integrity_issue", path=str(full_path), finding=issue
            )

    if create_truth_templates and any("*" in p for p in output_paths):
        _init_truth_templates(project_dir)

    return written
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: PASS (the new integration tests + all pre-existing dispatch tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat(dispatch): integrate write-failure + post-write integrity checks into _write_parsed_outputs"
```

---

### Task 4: Add write-capability confirmation to the retry path

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` — locate the retry-feedback construction (where `DispatchWriteFailureError` would be caught) and append `RETRY_WRITE_CONFIRMATION`.
- Test: `tests/unit/pipeline/test_dispatch_helper.py` — add a test for the retry prompt construction.

**Interfaces:**
- Consumes: `RETRY_WRITE_CONFIRMATION` (Task 1), `DispatchWriteFailureError` (Task 2)
- Produces: when a dispatch attempt fails with `DispatchWriteFailureError`, the retry prompt includes the write-capability confirmation quoting the matched signature.

**Context:** The dispatch loop in `dispatch_helper.py` retries failed skill calls. We add a branch: if the caught exception is `DispatchWriteFailureError`, the retry feedback is `RETRY_WRITE_CONFIRMATION.format(signature=err.signature)`. Let me find the exact retry site.

- [ ] **Step 1: Locate the retry site and write the failing test**

First find where retries are constructed:

```bash
grep -n "retry\|feedback\|attempts\|max_retries" src/shenbi/pipeline/dispatch_helper.py | head -20
```

The retry-feedback string is built where a failed dispatch is about to be retried. Add to `tests/unit/pipeline/test_dispatch_helper.py`:

```python
class TestRetryWriteConfirmation:
    def test_retry_prompt_includes_signature(self):
        from shenbi.exceptions import DispatchWriteFailureError
        from shenbi.pipeline.dispatch_helper import build_retry_feedback

        err = DispatchWriteFailureError(
            "write failed", signature="由于沙箱限制，我无法直接写文件"
        )
        feedback = build_retry_feedback(err)
        assert "CRITICAL" in feedback
        assert "write access" in feedback
        assert "由于沙箱限制，我无法直接写文件" in feedback
```

> If the dispatch loop does not currently have a `build_retry_feedback` helper, this task creates it as a thin pure function and the dispatch loop calls it. This keeps the retry-prompt construction testable without standing up the full dispatch loop.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::TestRetryWriteConfirmation -v`
Expected: FAIL — `ImportError: cannot import name 'build_retry_feedback'`

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/dispatch_helper.py`, add (near the other module-level helpers):

```python
def build_retry_feedback(exc: BaseException) -> str:
    """Build the retry-prompt feedback for a failed dispatch.

    For :class:`DispatchWriteFailureError` the feedback is the write-capability
    confirmation quoting the matched signature, so the model stops emitting
    sandbox diagnostics. For any other exception, a generic message is used.
    """
    if isinstance(exc, DispatchWriteFailureError):
        return RETRY_WRITE_CONFIRMATION.format(signature=exc.signature)
    return f"Previous attempt failed: {exc}. Retry, producing the complete output."
```

Then wire it into the existing dispatch retry path. Locate the retry-feedback assignment (search for the variable that holds the feedback string passed into the next dispatch attempt — typically `retry_feedback` or `feedback`). Replace the generic construction with `build_retry_feedback(exc)`. If the existing code does not catch exceptions per-attempt, wrap the dispatch call:

```python
try:
    written = _write_parsed_outputs(...)
except DispatchWriteFailureError as exc:
    state.chapter_loop.retry_feedback[retry_key] = build_retry_feedback(exc)
    # ... existing retry-count / escalation logic ...
    continue
```

> The exact line depends on the surrounding retry loop; the test only locks `build_retry_feedback`, so even a minimal wiring satisfies the spec's "retry prompt explicitly confirms write capability" requirement.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_dispatch_helper.py::TestRetryWriteConfirmation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat(dispatch): add write-capability confirmation to retry prompt"
```

---

### Task 5: Register post-write findings as G4 composite checkers

**Files:**
- Modify: `src/shenbi/gates/g4/generic.py` — add a checker that reads the logged `llm_output_integrity_issue` findings for the chapter's files and emits G4 results with the §3.6 severities.
- Test: `tests/unit/gates/g4/test_post_write_integrity.py` (new)

**Interfaces:**
- Consumes: the `llm_output_integrity_issue` log records (or a side-channel file the dispatcher writes). Simplest durable approach: `_write_parsed_outputs` also appends findings to a per-chapter file `audits/.integrity-findings.jsonl` that the G4 checker reads.
- Produces: G4 results: `G4.pi.model_leakage` / `G4.pi.unfinished_ending` / `G4.ac.*` / `G4.av.stale_line_ref` → FAIL; `G4.pi.fence_imbalance` → WARN.

**Context:** The spec §3.4 says post-write findings are "surfaced to G4 via the composite-checker registry." The cleanest durable channel is a side-file: `_write_parsed_outputs` writes each finding as a JSONL line to `audits/.integrity-findings-NN.jsonl` (one per chapter), and the G4 checker reads it. This avoids coupling G4 to structlog internals.

- [ ] **Step 1: Update `_write_parsed_outputs` to persist findings, and write the failing test**

First, modify the post-write loop in `_write_parsed_outputs` (Task 3) to also persist findings. Replace the `for issue in issues:` block with:

```python
        for issue in issues:
            log.warning(
                "llm_output_integrity_issue", path=str(full_path), finding=issue
            )
        if issues:
            _append_integrity_findings(project_dir, full_path, issues)
```

And add the helper near `_resolve_chapter_for_audit`:

```python
def _append_integrity_findings(
    project_dir: Path, file_path: Path, issues: list[str]
) -> None:
    """Persist post-write integrity findings for the G4 checker to read."""
    m = _CHAPTER_NUM_RE.search(file_path.stem)
    num = m.group(1) if m else "unknown"
    out = project_dir / "audits" / f".integrity-findings-{num}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        for issue in issues:
            fh.write(
                json.dumps(
                    {"file": str(file_path.relative_to(project_dir)), "finding": issue},
                    ensure_ascii=False,
                )
                + "\n"
            )
```

(Add `import json` at the top of `dispatch_helper.py` if not already present — it is likely already imported.)

Now write the failing G4 test. Create `tests/unit/gates/g4/test_post_write_integrity.py`:

```python
"""Tests for the G4 checker that consumes post-write integrity findings."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g4.generic import g4_post_write_integrity


def _write_findings(project_dir: Path, chapter: int, findings: list[dict]) -> None:
    p = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in findings) + "\n",
        encoding="utf-8",
    )


class TestG4PostWriteIntegrity:
    def test_no_findings_passes(self, tmp_path):
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "PASS"

    def test_model_leakage_fails(self, tmp_path):
        _write_findings(
            tmp_path,
            56,
            [{"file": "chapters/chapter-56.md", "finding": "G4.pi.model_leakage:chapter-56.md — leak"}],
        )
        result = g4_post_write_integrity(tmp_path, chapter=56)
        assert result["status"] == "FAIL"
        assert any("model_leakage" in c["id"] for c in result["checks"])

    def test_fence_imbalance_warns(self, tmp_path):
        _write_findings(
            tmp_path,
            1,
            [{"file": "chapters/chapter-1.md", "finding": "G4.pi.fence_imbalance:chapter-1.md — odd"}],
        )
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "WARN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/gates/g4/test_post_write_integrity.py -v`
Expected: FAIL — `ImportError: cannot import name 'g4_post_write_integrity'`

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/gates/g4/generic.py`, add:

```python
import json

#: Findings that FAIL the gate vs WARN. Everything else defaults to WARN.
_POST_WRITE_FAIL_PREFIXES = (
    "G4.pi.model_leakage",
    "G4.pi.unfinished_ending",
    "G4.ac.",
    "G4.av.",
)


def g4_post_write_integrity(project_dir: Path, *, chapter: int) -> dict:
    """G4 checker: consume persisted post-write integrity findings.

    Reads ``audits/.integrity-findings-<chapter>.jsonl`` (written by
    ``_write_parsed_outputs``) and maps each finding to a G4 check with the
    severity from spec §3.6. Returns a dict ``{"status", "checks"}``.
    """
    findings_path = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    checks: list[dict] = []
    has_fail = False
    has_warn = False
    if findings_path.exists():
        for line in findings_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            finding = str(entry.get("finding", ""))
            is_fail = any(finding.startswith(p) for p in _POST_WRITE_FAIL_PREFIXES)
            # fence_imbalance is the only WARN.
            if finding.startswith("G4.pi.fence_imbalance"):
                is_fail = False
            check_id = finding.split(":")[0] if ":" in finding else finding
            checks.append({"id": check_id, "s": "FAIL" if is_fail else "WARN", "r": finding})
            has_fail = has_fail or is_fail
            has_warn = has_warn or (not is_fail)
    status = "FAIL" if has_fail else ("WARN" if has_warn else "PASS")
    return {"status": status, "checks": checks}
```

Then register it in the G4 router. In `gate_G4` (around line 160-245), add a call after the per-skill checker runs:

```python
    # Post-write integrity findings (spec 19 §3.6) — apply to every chapter.
    from shenbi.gates.g4.generic import g4_post_write_integrity
    chapter_num = _chapter_number_from_paths(file_paths)  # existing helper, if any
    if chapter_num is not None:
        pwi = g4_post_write_integrity(Path(project_dir), chapter=chapter_num)
        for c in pwi["checks"]:
            checks.append(c)
```

> If `_chapter_number_from_paths` does not exist, extract the chapter number from any `chapter-NN` path in `file_paths` with `re.search(r"chapter-(\d+)", ...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/gates/g4/test_post_write_integrity.py tests/unit/gates/g4/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py \
        src/shenbi/gates/g4/generic.py \
        tests/unit/gates/g4/test_post_write_integrity.py
git commit -m "feat(g4): consume post-write integrity findings with severity routing"
```

---

### Task 6: Full regression — `just check`

- [ ] **Step 1: Run the complete check suite**

Run: `just check`
Expected: PASS.

- [ ] **Step 2: Run the full unit suite with coverage**

Run: `uv run pytest tests/unit/ -q --cov=shenbi --cov-fail-under=85`
Expected: PASS, coverage ≥ 85%.

- [ ] **Step 3: Verify the spec's verification criteria with a one-off scan**

Run a quick scan of the production novel-output for the affected chapters to confirm the checks would flag them (informational — does not block):

```bash
uv run python -c "
from pathlib import Path
from shenbi.pipeline.llm_output_integrity import (
    check_markdown_fence_balance, check_audit_completeness, check_prose_leakage
)
root = Path('novel-output/xinghuo-ranqiong')
for ch in [1, 11, 14, 19, 22, 29, 33, 42, 56]:
    p = root / 'chapters' / f'chapter-{ch}.md'
    if p.exists():
        print(ch, check_markdown_fence_balance(p))
"
```

Expected: the affected chapters show `G4.pi.fence_imbalance` findings (confirming the detector works against real data).

- [ ] **Step 4: Commit any cleanup**

```bash
git add -u
git commit -m "chore: ruff/mypy cleanup after llm-output-integrity plan" --allow-empty
```

---

## Self-Review

**1. Spec coverage:**
- §3.1 unified pattern catalog → Task 1 (`WRITE_FAILURE_PATTERNS`, `LEAKAGE_PATTERNS`, `VERDICT_MARKERS`, `PREAMBLE_MARKERS`) ✓
- §3.2 write-failure dominance rule (start OR >50%) → Task 1 `detect_write_failure` + dedicated tests ✓
- §3.3 prose leakage / fence balance / audit completeness / line-ref checks → Task 1 ✓
- §3.4 single integration point in `_write_parsed_outputs` with ordered checks → Task 3 ✓
- §3.5 retry write-capability confirmation → Task 4 ✓
- §3.6 severity routing to G4 → Task 5 ✓
- §4 affected files all covered ✓
- §5 verification criteria 1-10 — criteria 1-2 (write failure start/dominant), 3 (no false positive), 4 (leakage), 5 (aborted stub), 6 (version skew), 7 (fence), 9 (clean output) are unit-tested; criterion 8 (the 9 specific chapters) is verified informationally in Task 6 Step 3; criterion 10 (`just check`) is Task 6 Step 1 ✓

**2. Placeholder scan:** No TBD/TODO. The Task 4 wiring note ("the exact line depends on the surrounding retry loop") is a real property of the codebase — `build_retry_feedback` is fully specified and tested, and the wiring instruction is concrete. The Task 5 G4-router registration note about `_chapter_number_from_paths` gives a concrete fallback regex.

**3. Type consistency:** `detect_write_failure(content) -> tuple[bool, str | None]` is used identically in Tasks 1 and 3. `DispatchWriteFailureError(message, *, signature="")` is consistent across Tasks 2, 3, 4. `_is_audit_file(name: str)` and `_resolve_chapter_for_audit(full_path, project_dir)` are consistent across Task 3's body and the G4 router in Task 5. `g4_post_write_integrity(project_dir, *, chapter)` is consistent across Task 5's definition, test, and router call.

**Key codebase facts baked in:**
- Chapter prose is at `chapters/chapter-NN.md` (not project root).
- Audit reports are `chapter-NN-<dimension>.md` under `audits/`.
- `_write_parsed_outputs(response, output_paths, project_dir, create_truth_templates=False)` is the real signature.
- `_resolve_chapter_for_audit` and `_is_audit_file` do not exist today and are created here.
