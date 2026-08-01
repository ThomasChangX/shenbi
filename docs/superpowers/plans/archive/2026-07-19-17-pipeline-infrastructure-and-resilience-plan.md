# Pipeline Infrastructure and Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the sole remaining P0 blocker (P0.5: end-to-end validated run -- `novel-output/` exists but is untracked and `progress.json` is frozen), add crash recovery (signal handlers + atexit + checkpoint-on-step), implement 6 P1 engineering practices (retry, streaming, structured output, temperature config, scoring independence, golden set), resolve 6 P2 consistency issues, apply 5 runtime optimizations, and add comprehensive observability (per-step timing, token tracking, word count stability, progress tracking, state machine healing, dynamic timeouts). **P0.1-P0.4 are ALL ALREADY FIXED in the current code (verified) -- no tasks re-implement them.**

**Architecture:** P0.1-P0.4 (phase_runner gate path, shenbi-progress writes, rollback stub, codex_api branch) are ALREADY FIXED and excluded from this plan. The sole remaining P0 is P0.5: `novel-output/` already exists on disk but is UNTRACKED (not committed), and `progress.json` is frozen at Genesis for the entire run -- the fix adds a `.gitignore` exception so artifacts are auditable and fixes `progress.json` materialization. Crash recovery (`crash_recovery.py`) registers signal handlers (SIGTERM/SIGINT), an atexit hook, and a checkpoint-on-step boundary check, to save state and create emergency snapshots. P1 engineering practices layer tenacity retry, JSON mode, streaming, and per-skill temperature config onto `dispatch_helper.py`. Runtime optimizations reduce per-step waste (META strip, genre-config cache, truth-index rebuild, pipeline-state compaction, world file freshness). Observability adds `time.monotonic()` per-step timing, `response.usage` tracking, `MARK_DONE` trace events (NOT emitted by the chapter loop today -- root cause of frozen `progress.json`), and `_heal_current_step()` for state machine recovery (the `_advance` root cause is `state.chapter_loop.current_step = ""` at `chapter_loop.py:510`). Dynamic timeout must address ALL THREE paths: CLI subprocess, API path (no timeout currently), and IDE-CLI (`_IDE_AGENT_TIMEOUT = 900` hardcoded at `dispatch_helper.py:47`) -- scaling with chapter size (base 300s + 30s/KB, capped at 1800s).

**Tech Stack:** Python 3.11+, pathlib, structlog, json, tenacity, pydantic, signal, atexit, threading, time, unicodedata

## Global Constraints
1. `just check` full pass at every stage
2. P0.1-P0.4 are ALL ALREADY FIXED (phase_runner gate path, shenbi-progress writes, rollback stub, codex_api branch) -- do NOT re-implement them
3. P0.5: `novel-output/` exists but is untracked -- add `.gitignore` exception so artifacts are auditable; fix `progress.json` materialization (currently frozen at Genesis)
4. Internal mode scoring raises `DispatcherError` (P1.2)
5. API path output parsing uses 0 regex (P1.3)
6. 429 responses auto-retry 3 times with exponential backoff (P1.4)
7. Different skills use different temperatures as configured (P1.6)
8. `kill -TERM <pid>` saves pipeline state + creates emergency snapshot before exit (signal handlers + atexit + checkpoint-on-step)
9. `pipeline resume` correctly recovers from emergency shutdown state
10. Audit skill inputs do not contain `<!--META-BEGIN-->` blocks
11. `truth-index.json` mtime updates after volume boundary
12. Simulated 100-chapter `pipeline-state.json` < 100KB
13. Pipeline logs contain per-step timing with skill-level granularity
14. `progress.json` updates after each chapter completion during mini-pipeline (MARK_DONE events emitted by chapter loop, which they are NOT today)
15. Unit test: `step_index=9, current_step=""` auto-heals to correct skill (root cause: `_advance` sets `current_step=""` at `chapter_loop.py:510`)
16. 10KB chapter timeout ~600s; 38KB chapter timeout ~1440s; never exceeds 1800s -- applied to ALL THREE paths (CLI subprocess, API path, IDE-CLI)

---

## Task 1: Verify P0.1-P0.4 Are Already Fixed (no implementation)

> **Spec-aligned note (Spec 7 §2.1):** P0.1 (phase_runner gate path), P0.2 (shenbi-progress writes), P0.3 (rollback stub), and P0.4 (codex_api branch) are ALL ALREADY FIXED in the current codebase (verified 2026-07-15). This task is a one-time verification only -- do NOT re-implement any of them.

- [ ] **1a. Verify P0.1:** `src/shenbi/phase_runner.py:54-75` -- `run_gate()` already invokes `python -m shenbi.gates.cli` (line 64) and catches `(json.JSONDecodeError, ValueError, OSError)` (line 70). No `tests/validate-gate.py` reference remains.
- [ ] **1b. Verify P0.2:** `src/shenbi/dispatcher/modes/codex.py:20-48` -- `_record_completion` writes `progress.json` directly via `safe_write`; no `shenbi-progress` subprocess call and no entry point to register.
- [ ] **1c. Verify P0.3:** `src/shenbi/pipeline/cli.py:783-803` -- `cmd_rollback` returns `1`; the `rollback` subparser is not registered in `main()` (subparsers: init, next, status, review, resume, chapters).
- [ ] **1d. Verify P0.4:** `src/shenbi/dispatcher/executor.py:164-174,230-239` -- `dispatch()` has only a `codex` branch with `internal` fallback; no `codex-api` branch exists. `grep -r "codex.api\|codex_api" src/shenbi/dispatcher/executor.py` returns nothing.
- [ ] **1e.** No commit (verification only). If any check fails, the original audit was stale -- record the discrepancy rather than silently re-fixing.

---

## Task 2: P0.5 -- End-to-End Real Run Configuration

> **Spec-aligned note (Spec 7 §2.1 P0.5):** `novel-output/` ALREADY EXISTS on disk but is UNTRACKED (suppressed by `.gitignore`), and `progress.json` is frozen at Genesis for the entire run. The fix is NOT "create empty output" -- it is (a) add a `.gitignore` exception so artifacts become auditable via git history, and (b) fix `progress.json` materialization (see Task 12 -- the chapter loop does not emit `MARK_DONE` events today). `tests/rounds/` was deleted (commit `b978d3cc`).

**Files:**
- `.gitignore` -- add exception for `novel-output/` (which already exists on disk but is untracked)

- [ ] **2a.** Add to `.gitignore` (make the existing `novel-output/` untracked directory auditable):
  ```gitignore
  # Allow novel output for auditable pipeline verification (novel-output/ already
  # exists on disk but is currently untracked -- this makes artifacts auditable
  # via git history).
  !novel-output/
  !novel-output/**
  ```

- [ ] **2b.** Set required environment variables:
  ```bash
  # Required environment variables (set before running pipeline):
  #   SHENBI_LLM_API_KEY  — Your LLM API key
  #   SHENBI_LLM_BASE_URL — LLM API base URL
  #   SHENBI_LLM_MODEL    — Model name (e.g., deepseek-v4-flash)
  ```

- [ ] **2c.** Run 5-chapter canary test:
  ```bash
  python -m shenbi.pipeline.cli next --project-dir novel-output/xinghuo-ranqiong --max-chapters 5
  ```

- [ ] **2d.** Verify artifacts exist AND are now git-tracked: `pipeline-state.json`, `genesis/`, `chapters/`, `truth/`, `audits/`, `gate-markers/`.

- [ ] **2e.** Confirm `progress.json` updates during the run (depends on Task 12 `MARK_DONE` events being emitted; if still frozen after Task 12, revisit).

- [ ] **2f. Commit:** `build: make novel-output/ auditable via .gitignore exception and verify end-to-end run`

---

## Task 3: P1.4 -- Add Retry with Exponential Backoff

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- add tenacity retry decorator
- `src/shenbi/pipeline/dispatch_helper.py` -- add tenacity retry decorator

**TDD Cycle:**

- [ ] **3a. Write test:** Create `tests/pipeline/test_retry.py`
  ```python
  """Test tenacity retry with exponential backoff on LLM calls."""
  import pytest
  import httpx
  from unittest.mock import MagicMock, patch, call
  from tenacity import RetryError
  from shenbi.pipeline.dispatch_helper import _call_llm_with_retry

  class TestLLMRetry:
      def test_retries_on_429(self):
          """Should retry on HTTP 429 (rate limit)."""
          mock_client = MagicMock()
          mock_client.chat.completions.create.side_effect = [
              httpx.HTTPStatusError("rate limit",
                  request=MagicMock(), response=MagicMock(status_code=429)),
              httpx.HTTPStatusError("rate limit",
                  request=MagicMock(), response=MagicMock(status_code=429)),
              MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
          ]

          result = _call_llm_with_retry(
              mock_client, "test-model", [{"role": "user", "content": "hi"}]
          )
          assert result is not None
          assert mock_client.chat.completions.create.call_count == 3

      def test_retries_on_5xx(self):
          """Should retry on HTTP 500/502/503."""
          mock_client = MagicMock()
          mock_client.chat.completions.create.side_effect = [
              httpx.HTTPStatusError("server error",
                  request=MagicMock(), response=MagicMock(status_code=500)),
              MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
          ]

          result = _call_llm_with_retry(
              mock_client, "test-model", [{"role": "user", "content": "hi"}]
          )
          assert mock_client.chat.completions.create.call_count == 2

      def test_gives_up_after_3_failures(self):
          """Should raise after 3 consecutive failures."""
          mock_client = MagicMock()
          mock_client.chat.completions.create.side_effect = (
              httpx.HTTPStatusError("error",
                  request=MagicMock(), response=MagicMock(status_code=429))
          )

          with pytest.raises((RetryError, httpx.HTTPStatusError)):
              _call_llm_with_retry(
                  mock_client, "test-model", [{"role": "user", "content": "hi"}]
              )

      def test_no_retry_on_4xx_non_429(self):
          """Should NOT retry on 400/401/403 (client errors)."""
          mock_client = MagicMock()
          mock_client.chat.completions.create.side_effect = (
              httpx.HTTPStatusError("bad request",
                  request=MagicMock(), response=MagicMock(status_code=400))
          )

          with pytest.raises(httpx.HTTPStatusError):
              _call_llm_with_retry(
                  mock_client, "test-model", [{"role": "user", "content": "hi"}]
              )
          assert mock_client.chat.completions.create.call_count == 1

      def test_retries_on_timeout(self):
          """Should retry on timeout."""
          mock_client = MagicMock()
          mock_client.chat.completions.create.side_effect = [
              httpx.TimeoutException("timeout"),
              MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
          ]

          result = _call_llm_with_retry(
              mock_client, "test-model", [{"role": "user", "content": "hi"}]
          )
          assert mock_client.chat.completions.create.call_count == 2
  ```

- [ ] **3b. Run test -- confirm FAIL.**

- [ ] **3c. Implement** in `src/shenbi/pipeline/dispatch_helper.py`:
  ```python
  from tenacity import (
      retry,
      stop_after_attempt,
      wait_exponential_jitter,
      retry_if_exception_type,
  )
  import httpx

  _RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

  def _is_retryable(exception: Exception) -> bool:
      """Determine if an HTTP error is retryable."""
      if isinstance(exception, httpx.TimeoutException):
          return True
      if isinstance(exception, httpx.HTTPStatusError):
          return exception.response.status_code in _RETRYABLE_STATUSES
      return False

  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential_jitter(initial=1, max=30),
      retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
      before_sleep=lambda retry_state: logger.warning(
          "llm_retry",
          attempt=retry_state.attempt_number,
          exception=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
      ),
  )
  def _call_llm_with_retry(client, model, messages, **kwargs):
      """Call LLM API with exponential backoff retry on transient failures.

      Retries: 429 (rate limit), 5xx (server errors), timeouts.
      Does NOT retry: 400, 401, 403 (client errors).
      """
      return client.chat.completions.create(
          model=model, messages=messages, **kwargs
      )
  ```

- [ ] **3d. Run test -- confirm PASS.**

- [ ] **3e. Commit:** `feat(p1): add tenacity retry with exponential backoff for LLM API calls`

---

## Task 4: P1.3 -- JSON Mode + Pydantic Structured Output

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- add JSON mode output parsing

- [ ] **4a. Implement** in `dispatch_helper.py`:
  ```python
  from pydantic import BaseModel, ValidationError


  class FileOutput(BaseModel):
      path: str
      content: str


  class SkillOutput(BaseModel):
      files: list[FileOutput] = []
      decisions: dict | None = None


  def _parse_structured_output(raw_content: str) -> SkillOutput:
      """Parse LLM response via JSON mode (Pydantic).

      Falls back to ### FILE: regex parsing for CLI backend.
      """
      try:
          return SkillOutput.model_validate_json(raw_content)
      except (ValidationError, json.JSONDecodeError):
          # Fallback: regex parse ### FILE: markers
          return _parse_file_markers(raw_content)


  def _parse_file_markers(raw_content: str) -> SkillOutput:
      """Legacy ### FILE: regex fallback parser."""
      files = []
      pattern = re.compile(r'###\s*FILE:\s*(.+?)\n(.*?)(?=###\s*FILE:|\Z)', re.DOTALL)
      for match in pattern.finditer(raw_content):
          files.append(FileOutput(
              path=match.group(1).strip(),
              content=match.group(2).strip(),
          ))
      return SkillOutput(files=files)
  ```

  Update the API dispatch path to use `response_format={"type": "json_object"}`:
  ```python
  response = client.chat.completions.create(
      model=model,
      messages=messages,
      response_format={"type": "json_object"},
      temperature=temp,
      max_tokens=max_tok,
  )
  output = _parse_structured_output(response.choices[0].message.content)
  ```

- [ ] **4b. Verify:** grep confirms API path uses 0 regex for primary parsing -- `_parse_file_markers` is fallback only.

- [ ] **4c. Run `just check` -- confirm full pass.**

- [ ] **4d. Commit:** `feat(p1): add JSON mode + Pydantic structured output with regex fallback`

---

## Task 5: P1.5 and P1.6 -- Streaming + Per-Skill Temperature Config

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- add streaming and temperature config
- `executor_config.toml` -- NEW config file (does NOT exist yet -- create it; per Spec 6 §5.4 it externalizes the hardcoded `_API_TEMPERATURE = 0.7` at `dispatch_helper.py:49`)

- [ ] **5a. Create** `executor_config.toml`:
  ```toml
  [default]
  temperature = 0.7
  max_tokens = 16384

  [overrides."shenbi-chapter-drafting"]
  temperature = 0.85
  max_tokens = 16384

  [overrides."shenbi-chapter-revision"]
  temperature = 0.6

  [overrides."shenbi-review-continuity"]
  temperature = 0.2

  [overrides."shenbi-review-anti-ai"]
  temperature = 0.15

  [overrides."shenbi-review-resonance"]
  temperature = 0.1

  [overrides."shenbi-foreshadowing-lifecycle"]
  temperature = 0.5
  ```

- [ ] **5b. Implement** config loading in `dispatch_helper.py`:
  ```python
  import tomllib
  from pathlib import Path

  _executor_config: dict | None = None

  def _load_executor_config() -> dict:
      """Load executor_config.toml, caching in memory."""
      global _executor_config
      if _executor_config is not None:
          return _executor_config
      # Use existing _PROJECT_ROOT from dispatch_helper.py:37 instead of navigating upward
      config_path = _PROJECT_ROOT / "executor_config.toml"
      if config_path.exists():
          with open(config_path, 'rb') as f:
              _executor_config = tomllib.load(f)
      else:
          _executor_config = {}
      return _executor_config


  def _get_skill_temperature(skill_name: str) -> float:
      """Get temperature for a skill from executor_config.toml."""
      config = _load_executor_config()
      overrides = config.get('overrides', {})
      if skill_name in overrides:
          return overrides[skill_name].get(
              'temperature',
              config.get('default', {}).get('temperature', 0.7)
          )
      return config.get('default', {}).get('temperature', 0.7)


  def _get_skill_max_tokens(skill_name: str) -> int:
      """Get max_tokens for a skill from executor_config.toml."""
      config = _load_executor_config()
      overrides = config.get('overrides', {})
      if skill_name in overrides:
          return overrides[skill_name].get(
              'max_tokens',
              config.get('default', {}).get('max_tokens', 16384)
          )
      return config.get('default', {}).get('max_tokens', 16384)
  ```

- [ ] **5c. Implement** streaming in `dispatch_helper.py`:
  ```python
  def _call_llm_streaming(client, model, messages,
                          early_stop_patterns=None, **kwargs):
      """Stream LLM response with optional early-stop patterns."""
      collected = []
      stop_reason = None
      stream = client.chat.completions.create(
          model=model, messages=messages, stream=True, **kwargs
      )
      for chunk in stream:
          if chunk.choices and chunk.choices[0].delta.content:
              delta = chunk.choices[0].delta.content
              collected.append(delta)
              if early_stop_patterns:
                  text_so_far = "".join(collected)
                  for pat in early_stop_patterns:
                      if pat in text_so_far:
                          stop_reason = f"early_stop: matched '{pat[:30]}'"
                          break
                  if stop_reason:
                      break
      result = "".join(collected)
      if stop_reason:
          logger.info("streaming_early_stop", reason=stop_reason)
      return result, stop_reason
  ```

- [ ] **5d. Delete** `_API_TEMPERATURE` and `_API_MAX_TOKENS` constants from `dispatch_helper.py`.

- [ ] **5e. Run `just check` -- confirm full pass.**

- [ ] **5f. Commit:** `feat(p1): add streaming with early-stop, per-skill temperature config via executor_config.toml`

---

## Task 6: P1.2 and P1.8 -- Scoring Independence + Golden Evaluation Set

**Files:**
- `src/shenbi/dispatcher/modes/internal.py` -- hard-reject scoring in internal mode
- `tests/golden/` -- new directory for golden evaluation set

- [ ] **6a. Implement** in `src/shenbi/dispatcher/modes/internal.py`:
  ```python
  raise DispatcherError(
      "internal mode has no LLM backend, cannot score. "
      "Set SHENBI_LLM_API_KEY to use API mode."
  )
  ```

- [ ] **6b. Create** `tests/golden/` directory with README:
  ```markdown
  # Golden Evaluation Set

  Contains 10-20 chapters from real pipeline output (P0.5),
  human-scored per rubric. Used for regression testing and
  scoring calibration.

  ## Files
  - `chapter-N-original.md`: Original chapter output
  - `chapter-N-scores.json`: Human-assigned scores per rubric dimension
  - `calibration-report.md`: Pearson/Spearman correlation with automated scoring
  ```

- [ ] **6c. Commit:** `feat(p1): hard-reject internal mode scoring, create golden evaluation set directory`

---

## Task 7: P2.1 -- CJK Zero-Width Normalization

**Files:**
- `src/shenbi/contracts/fields.py` -- add zero-width stripping and NFKC normalization

- [ ] **7a. Write test:** Create `tests/contracts/test_cjk_normalization.py`
  ```python
  """Test CJK zero-width and NFKC normalization in fields.py."""
  import pytest
  import unicodedata
  from shenbi.contracts.fields import _normalize_ws

  class TestCJKNormalization:
      def test_normalizes_ideographic_space(self):
          text = "第一章\u3000开始"
          result = _normalize_ws(text)
          assert "\u3000" not in result

      def test_strips_zero_width_non_joiner(self):
          text = "测试\u200c文本"
          result = _normalize_ws(text)
          assert "\u200c" not in result

      def test_strips_zero_width_space(self):
          text = "测试\u200b文本"
          result = _normalize_ws(text)
          assert "\u200b" not in result

      def test_strips_byte_order_mark(self):
          text = "\ufeff测试文本"
          result = _normalize_ws(text)
          assert "\ufeff" not in result

      def test_strips_zero_width_joiner(self):
          text = "测试\u200d文本"
          result = _normalize_ws(text)
          assert "\u200d" not in result

      def test_applies_nfkc_normalization(self):
          # Fullwidth ASCII 'A' (U+FF21) should normalize to 'A' (U+0041)
          text = "\uff21BC"
          result = _normalize_ws(text)
          assert "ABC" in result

      def test_collapses_multiple_spaces(self):
          text = "第一章   第二章"
          result = _normalize_ws(text)
          assert "第一章 第二章" in result

      def test_strips_leading_trailing_whitespace(self):
          text = "  测试文本  "
          result = _normalize_ws(text)
          assert result == "测试文本"

      def test_preserves_normal_text(self):
          text = "第一章 废料场"
          result = _normalize_ws(text)
          assert result == "第一章 废料场"
  ```

- [ ] **7b. Run test -- confirm FAIL.**

- [ ] **7c. Implement** in `src/shenbi/contracts/fields.py:23-24`:
  ```python
  import re
  import unicodedata

  def _normalize_ws(text: str) -> str:
      """Normalize whitespace and CJK-specific characters.

      - Replace ideographic space (U+3000) with ASCII space
      - Remove zero-width characters (U+200B, U+FEFF, U+200C, U+200D)
      - Apply NFKC normalization (handles fullwidth ASCII, etc.)
      - Collapse multiple whitespace to single space
      - Strip leading/trailing whitespace
      """
      text = text.replace("\u3000", " ")
      text = "".join(
          c for c in text
          if c not in ("\u200b", "\ufeff", "\u200c", "\u200d")
      )
      text = unicodedata.normalize("NFKC", text)
      text = re.sub(r"\s+", " ", text).strip()
      return text
  ```

- [ ] **7d. Run test -- confirm PASS.**

- [ ] **7e. Commit:** `fix(p2): add CJK zero-width normalization and NFKC to fields._normalize_ws`

---

## Task 8: P2.2-P2.6 -- Remaining Consistency Fixes

**Files:**
- `src/shenbi/contracts/schemas/decisions.py` -- unify Severity literal
- `src/shenbi/scoring.py` -- use `TEST_PASS` constant
- `src/shenbi/contracts/legacy.py` -- fix docstring
- `src/shenbi/gates/g7.py`, `g_dispatch.py`, `g_reconcile.py`, `g_transition.py`, `g0.py` -- deferred PASS to UNIMPLEMENTED
- `docs/getting-started/first-novel.md` -- remove stale placeholder claim

- [ ] **8a. P2.2 -- Unify Severity literal** in `src/shenbi/contracts/schemas/decisions.py`:
  ```python
  from typing import Literal

  Severity = Literal["low", "medium", "high"]

  class Selection(BaseModel):
      severity: Severity = "low"

  class Adjustment(BaseModel):
      severity: Severity  # was: str
  ```

  **CRITICAL -- extend the `Selection._p25` validator:** Adding `"medium"` to the
  `Severity` Literal alone is NOT sufficient. The existing `Selection` model has
  a pydantic validator (named `_p25`, a private validator method) that branches
  on the severity value and currently only handles the `"high"` and `"low"`
  cases (e.g. it sets a p25 priority/weight for those two and falls through or
  raises on anything else). After widening the literal, that validator MUST be
  extended to also branch on `"medium"` (typically interpolating between the
  high and low weights), otherwise any `Selection` carrying
  `severity: "medium"` will fail validation / produce a wrong priority. Read the
  `_p25` validator body in `decisions.py` first, then add the `"medium"` branch
  before running `just check`.

- [ ] **8b. P2.3 -- Use TEST_PASS constant** in `src/shenbi/scoring.py`:
  ```python
  from shenbi.contracts.thresholds import TEST_PASS

  # Replace hardcoded 90 with TEST_PASS
  # Before: if score >= 90: return "PASS"
  # After:
  if score >= TEST_PASS:
      return "PASS"
  ```

- [ ] **8c. P2.4 -- Fix legacy.py docstring** at `src/shenbi/contracts/legacy.py:1`:
  ```python
  """Canonical contract loader and validator.

  Despite historical naming (originally a legacy compatibility layer),
  this is the current single source of truth consumed by all gates,
  dispatchers, and pipeline components.
  """
  ```

- [ ] **8d. P2.5 -- Deferred PASS to UNIMPLEMENTED** in 5 gate files:
  Change pattern in each file from:
  ```python
  c.append({"id": "G7.2", "s": "PASS", "note": "deferred"})
  ```
  To:
  ```python
  from shenbi.gates.shared import unimplemented
  c.append(unimplemented("G7.2", "skill-traces check not yet implemented"))
  ```
  Affected: `g7.py:108-112`, `g_dispatch.py:67-69`, `g_reconcile.py:74-76`, `g_transition.py:66-91`, `g0.py:237-238`.

- [ ] **8e. P2.6 -- Fix first-novel.md** at `docs/getting-started/first-novel.md:231-233`:
  Remove or update the claim that orchestration is "a placeholder."

- [ ] **8f. Run `just check` -- confirm full pass.**

- [ ] **8g. Commit:** `fix(p2): unify Severity literal, use TEST_PASS, fix legacy docstring, deferred PASS to UNIMPLEMENTED, fix stale docs`

---

## Task 9: Crash Recovery -- Signal Handlers, atexit, and Checkpoint-on-Step

> **Spec-aligned note (Spec 7 §3.4):** Crash recovery combines three mechanisms: (1) signal handlers for SIGTERM/SIGINT that set `shutdown_requested = True` and run emergency cleanup, (2) an `atexit` hook for normal exits with unsaved changes, and (3) a checkpoint-on-step boundary check in the chapter loop so shutdown occurs between steps, never mid-LLM-call. On signal: mark current step `EMERGENCY_SHUTDOWN_AT_{step.skill}`, save state, create emergency snapshot, clear staging, then re-raise for correct exit code.

**Files:**
- `src/shenbi/pipeline/crash_recovery.py` -- new file (signal handlers + atexit + cleanup)
- `src/shenbi/pipeline/chapter_loop.py` -- checkpoint-on-step boundary check
- `src/shenbi/pipeline/cli.py` -- emergency shutdown recovery in `cmd_resume`

- [ ] **9a. Write test:** Create `tests/pipeline/test_crash_recovery.py`
  ```python
  """Test crash recovery signal handlers, emergency cleanup, and shutdown flag."""
  import signal
  import pytest
  import tempfile
  from pathlib import Path
  from unittest.mock import MagicMock, patch, call
  from shenbi.pipeline.crash_recovery import (
      register_emergency_handlers,
      is_shutdown_requested,
      _emergency_cleanup,
      _handle_emergency_signal,
  )

  class TestSignalHandlers:
      def test_registers_sigterm_and_sigint(self):
          with patch('signal.signal') as mock_signal:
              register_emergency_handlers(Path('/tmp'), MagicMock())
              assert mock_signal.call_count >= 2
              signals_registered = [c[0][0] for c in mock_signal.call_args_list]
              assert signal.SIGTERM in signals_registered
              assert signal.SIGINT in signals_registered

      def test_registers_atexit(self):
          with patch('atexit.register') as mock_atexit:
              register_emergency_handlers(Path('/tmp'), MagicMock())
              mock_atexit.assert_called_once()

  class TestShutdownFlag:
      def test_initially_false(self):
          import shenbi.pipeline.crash_recovery as cr
          cr._shutdown_requested = False
          assert not is_shutdown_requested()

      def test_set_on_signal(self):
          import shenbi.pipeline.crash_recovery as cr
          cr._shutdown_requested = True
          assert is_shutdown_requested()

  class TestEmergencyCleanup:
      def test_saves_pipeline_state(self, tmp_path):
          state = MagicMock()
          _emergency_cleanup(tmp_path, state)
          # Should attempt to save state
          # (save_state from shenbi.pipeline.machine is called if available)

      def test_cleanup_failure_does_not_prevent_exit(self, tmp_path):
          state = MagicMock()
          state.save.side_effect = RuntimeError("disk full")
          # Should not raise -- emergency cleanup is best-effort
          try:
              _emergency_cleanup(tmp_path, state)
          except Exception:
              pytest.fail("_emergency_cleanup should not raise on failure")
  ```

- [ ] **9b. Run test -- confirm FAIL.**

- [ ] **9c. Implement** `src/shenbi/pipeline/crash_recovery.py`:
  ```python
  """Crash recovery: signal handlers, emergency snapshots, graceful shutdown.

  Handles SIGTERM, SIGINT, and atexit to preserve pipeline state and create
  emergency snapshots before exit. The chapter loop checks is_shutdown_requested()
  at step boundaries to avoid interrupting an active LLM call.
  """
  from __future__ import annotations

  import atexit
  import signal
  import shutil
  from pathlib import Path
  from typing import TYPE_CHECKING

  import structlog

  if TYPE_CHECKING:
      from shenbi.pipeline.state import PipelineState

  logger = structlog.get_logger(__name__)

  # Module-level state for signal handlers
_shutdown_requested = False
_emergency_flag = False
_emergency_state: dict = {}


def is_shutdown_requested() -> bool:
    """Check if emergency shutdown has been requested.

    Called by chapter loop at step boundaries.
    """
    return _shutdown_requested


def register_emergency_handlers(
    project_dir: Path, state: 'PipelineState'
) -> None:
    """Register signal handlers and atexit hook for crash recovery.

    Must be called at pipeline startup, before the chapter loop begins.
    """
    _emergency_state['project_dir'] = project_dir
    _emergency_state['pipeline_state'] = state

    signal.signal(signal.SIGTERM, _handle_emergency_signal)
    signal.signal(signal.SIGINT, _handle_emergency_signal)
    atexit.register(_emergency_cleanup)


def _handle_emergency_signal(signum, frame):
    """Signal handler: ONLY sets atomic flag. No I/O, no locks."""
    global _emergency_flag
    _emergency_flag = True


def _check_emergency_flag(project_dir):
    """Called at step boundaries in main loop. Performs cleanup if flag set."""
    global _emergency_flag
    if _emergency_flag:
        _emergency_flag = False
        try:
            _emergency_cleanup(project_dir)
        except Exception:
            pass  # Best-effort cleanup


def _emergency_cleanup(project_dir: Path | None = None) -> None:
    """Best-effort emergency cleanup: save state, create snapshot, clear staging.

    Called by both _check_emergency_flag and atexit (for normal exits with unsaved data).
    All operations wrapped in try/except -- failure must not prevent process exit.
    """
    if project_dir is None:
        project_dir = _emergency_state.get('project_dir')
    state = _emergency_state.get('pipeline_state')

      if not project_dir or not state:
          return

      logger.info("emergency_cleanup_started")

      # 1. Mark current step
      try:
          if hasattr(state, 'chapter_loop') and state.chapter_loop:
              cl = state.chapter_loop
              current_skill = getattr(cl, 'current_step', '') or 'unknown'
              cl.current_step = f"EMERGENCY_SHUTDOWN_AT_{current_skill}"
      except Exception:
          pass

      # 2. Save pipeline state
      try:
          from shenbi.pipeline.machine import save_state
          save_state(project_dir, state)
          logger.info("pipeline_state_saved")
      except Exception as e:
          logger.error("pipeline_state_save_failed", error=str(e))

      # 3. Create emergency snapshot
      try:
          chapter = getattr(state.chapter_loop, 'current_chapter', 0)
          _snapshot_chapter_files(project_dir, chapter, label="emergency")
          logger.info("emergency_snapshot_created")
      except Exception as e:
          logger.error("emergency_snapshot_failed", error=str(e))

      # 4. Clear staging
      try:
          staging_dir = project_dir / 'staging'
          if staging_dir.exists():
              shutil.rmtree(staging_dir)
              logger.info("staging_cleared")
      except Exception:
          pass


  def _snapshot_chapter_files(
      project_dir: Path, chapter: int, label: str = "emergency"
  ) -> None:
      """Create a snapshot of current chapter files.

      Copies chapter-N.md to chapter-N-{label}.md for recovery.
      """
      if chapter <= 0:
          return

      chapter_path = project_dir / 'chapters' / f'chapter-{chapter}.md'
      if not chapter_path.exists():
          return

      snapshot_dir = project_dir / 'snapshots'
      snapshot_dir.mkdir(parents=True, exist_ok=True)

      snap_path = snapshot_dir / f'chapter-{chapter}-{label}.md'
      shutil.copy2(chapter_path, snap_path)
  ```

- [ ] **9d. Integrate** into `src/shenbi/pipeline/chapter_loop.py`:
  ```python
  from shenbi.pipeline.crash_recovery import _check_emergency_flag

  def run_chapter_loop(state):
      """Run the per-chapter step loop with shutdown awareness."""
      for step in CHAPTER_STEPS:
          # Check emergency flag at every step boundary
          _check_emergency_flag(state.project_dir)

          if not _should_run_step(state, step):
              continue

          result = run_chapter_step(state, step)
          if not result.success:
              # Handle step failure
              pass
  ```

- [ ] **9e. Integrate** resume logic in `src/shenbi/pipeline/cli.py`:
  ```python
  def cmd_resume(args):
      """Resume pipeline from last saved state."""
      from shenbi.pipeline.machine import load_state, save_state
      state = load_state(args.project_dir)

      # Heal emergency shutdown state
      cl = state.chapter_loop
      if cl.current_step and cl.current_step.startswith("EMERGENCY_SHUTDOWN"):
          logger.warning("resuming_from_emergency_shutdown",
                         chapter=cl.current_chapter)
          if cl.step_index < len(CHAPTER_STEPS):
              cl.current_step = CHAPTER_STEPS[cl.step_index].skill
          else:
              cl.current_step = ""
          save_state(args.project_dir, state)

      # Validate state consistency
      _validate_state_consistency(state)

      # Continue loop
      run_chapter_loop(state)
  ```

- [ ] **9f. Run test -- confirm PASS.**

- [ ] **9g. Commit:** `feat(recovery): add crash recovery with signal handlers, emergency snapshots, and shutdown-aware loop`

---

## Task 10: Runtime Optimizations (5 items)

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- META strip, genre-config cache
- `src/shenbi/pipeline/chapter_loop.py` -- truth-index rebuild, world file freshness
- `src/shenbi/pipeline/state.py` -- pipeline-state compaction

- [ ] **10a. Runtime Opt 1: META block stripping** in `dispatch_helper.py`:
  ```python
  _META_PATTERN = re.compile(r'<!--META-BEGIN-->.*?<!--META-END-->', re.DOTALL)

  def _strip_meta_for_non_drafting(skill_name: str, text: str) -> str:
      """Strip META blocks from chapter text for non-drafting LLM calls.

      Only drafting and revision skills need META blocks.
      All other skills (auditors, state-settling, etc.) receive stripped text.
      Saves 16-31% input per non-drafting call.
      """
      if skill_name in ('shenbi-chapter-drafting', 'shenbi-chapter-revision'):
          return text
      return _META_PATTERN.sub('', text)
  ```

- [ ] **10b. Runtime Opt 2: Genre-config caching** in `dispatch_helper.py`:
  ```python
  _genre_config_cache: dict[int, dict] = {}

  def _load_genre_config_cached(project_dir: Path, chapter: int) -> dict:
      """Load genre-config.json with per-chapter cache. ~7 disk I/O -> 1."""
      if chapter in _genre_config_cache:
          return _genre_config_cache[chapter]
      config_path = project_dir / 'config' / 'genre-config.json'
      config = json.loads(config_path.read_text(encoding='utf-8'))
      _genre_config_cache[chapter] = config
      return config
  ```

- [ ] **10c. Runtime Opt 3: Truth-index periodic rebuild** in `chapter_loop.py:_complete_chapter`:
  ```python
  def _maybe_rebuild_truth_index(project_dir: Path, chapter: int) -> None:
      """Rebuild truth-index at volume boundaries or every 15 chapters."""
      if chapter % 15 == 0 or _is_volume_boundary(project_dir, chapter):
          from shenbi.pipeline.truth_index import rebuild_index
          rebuild_index(project_dir)
          logger.info("truth_index_rebuilt", chapter=chapter)
  ```

- [ ] **10d. Runtime Opt 4: Pipeline-state compaction** in `src/shenbi/pipeline/state.py`:
  ```python
  def compact_pipeline_state(state: PipelineState) -> None:
      """Archive old chapter states and prune retry feedback.

      Reduces ~236KB (at 100 chapters) to ~80KB.
      """
      if not hasattr(state, 'chapter_loop'):
          return

      cl = state.chapter_loop
      current = cl.current_chapter

      # Archive chapter states beyond last 10
      if hasattr(cl, 'chapter_states'):
          keys_to_archive = [
              k for k in cl.chapter_states
              if k.isdigit() and int(k) < current - 10
          ]
          for k in keys_to_archive:
              _archive_chapter_state(state.project_dir, k, cl.chapter_states.pop(k))

      # Prune retry_feedback to last 30 entries
      if hasattr(state, 'retry_feedback') and len(state.retry_feedback) > 30:
          state.retry_feedback = state.retry_feedback[-30:]
  ```

- [ ] **10e. Runtime Opt 5: World file freshness** in `chapter_loop.py:_complete_chapter`:
  ```python
  def _check_world_file_freshness(project_dir: Path, chapter: int) -> None:
      """Check if locations.md needs updating at volume boundaries."""
      if not _is_volume_boundary(project_dir, chapter):
          return

      locations_path = project_dir / 'world' / 'locations.md'
      if not locations_path.exists():
          return

      # Compare against SCR-extracted locations from last 10 chapters
      # NOTE: The scr_extractor import is lazy (inside function body). This module
      # is delivered by Plan 18. If Plan 17 executes first, the scr_extractor
      # feature will silently degrade until Plan 18 ships. This is intentional --
      # no hard dependency.
      from shenbi.pipeline.scr_extractor import extract_scr
      recent_locations = set()
      for ch in range(max(1, chapter - 10), chapter):
          try:
              scr = extract_scr(project_dir, ch)
              for ref in scr.world_refs:
                  if ref.get('category') == 'location':
                      recent_locations.add(ref['element'])
          except Exception:
              continue

      current_locations_text = locations_path.read_text(encoding='utf-8')
      missing = [
          loc for loc in recent_locations
          if loc not in current_locations_text
      ]
      if missing:
          logger.warning("world_file_stale_locations",
                         chapter=chapter,
                         missing_locations=missing[:10])
  ```

- [ ] **10f. Run `just check` -- confirm full pass.**

- [ ] **10g. Commit:** `perf(pipeline): apply 5 runtime optimizations (META strip, genre-cache, truth-index, state-compact, world-freshness)`

---

## Task 11: Observability -- Per-Step Timing, Token Tracking, Word Count, Progress

**Files:**
- `src/shenbi/pipeline/chapter_loop.py` -- per-step timing, word count stability
- `src/shenbi/pipeline/dispatch_helper.py` -- token tracking (already started in Plan 6 Task 7)

- [ ] **11a. Per-step timing** in `chapter_loop.py:run_chapter_step`:
  ```python
  import time

  def run_chapter_step(state, step: StepDef) -> StepResult:
      """Execute a single pipeline step with timing instrumentation."""
      step_start = time.monotonic()
      try:
          # ... execute step ...
          result = _dispatch_skill(state, step)
          return StepResult(success=True)
      except Exception as e:
          return StepResult(success=False, error=str(e))
      finally:
          elapsed = time.monotonic() - step_start
          logger.info("step_timing",
                      chapter=state.chapter_loop.current_chapter,
                      step=step.skill,
                      elapsed_seconds=round(elapsed, 1))
          _record_step_timing(state, step.skill, elapsed)
  ```

  Add timing summary at chapter completion:
  ```python
  def _print_timing_summary(state) -> None:
      """Print per-skill timing summary at end of pipeline."""
      if not hasattr(state, 'step_timings'):
          return
      logger.info("timing_summary_header")
      for skill, times in sorted(state.step_timings.items()):
          if times:
              avg = sum(times) / len(times)
              mn = min(times)
              mx = max(times)
              logger.info("timing_summary_row",
                          skill=skill,
                          calls=len(times),
                          avg_seconds=round(avg, 1),
                          min_seconds=round(mn, 1),
                          max_seconds=round(mx, 1))
  ```

- [ ] **11b. Word count stability** -- add bounds in chapter planning/drafting prompts and G4 post-write check:
  ```python
  def _check_word_count_bounds(chapter_text: str) -> list[str]:
      """G4 word count bounds check. WARN outside 4000-15000 range."""
      issues = []
      # Count Chinese characters
      chinese_chars = sum(1 for c in chapter_text if '\u4e00' <= c <= '\u9fff')
      if chinese_chars < 4000:
          issues.append(f"G4.word_count:below_floor -- {chinese_chars} chars (min 4000)")
      if chinese_chars > 15000:
          issues.append(f"G4.word_count:above_ceiling -- {chinese_chars} chars (max 15000)")
      return issues
  ```

- [ ] **11c. Run `just check` -- confirm full pass.**

- [ ] **11d. Commit:** `feat(observability): add per-step timing, word count bounds, and timing summary`

---

## Task 12: Progress Tracking Fix -- Emit MARK_DONE Events

> **Spec-aligned note (Spec 7 §2.7):** `MARK_DONE` trace events are NOT emitted by the chapter loop today (`_record_step_done` at `chapter_loop.py:443-451` updates in-memory `PipelineState` but never writes a trace event). Since `progress.json` is a trace-derived view (`trace/materialize.py:31-101`), the missing events are the root cause of `progress.json` being frozen at Genesis for the entire 40-hour run. This task adds the `MARK_DONE` emission.

**Files:**
- `src/shenbi/pipeline/chapter_loop.py:_record_step_done` -- emit MARK_DONE events

- [ ] **12a. Implement** in `chapter_loop.py:_record_step_done`:
  ```python
  def _record_step_done(state, chapter: int, skill_name: str) -> None:
      """Record step completion and emit MARK_DONE trace event."""
      # Existing in-memory update
      ch_state = state.chapter_loop.chapter_states.setdefault(str(chapter), {})
      steps = ch_state.setdefault('steps_done', [])
      if skill_name not in steps:
          steps.append(skill_name)

      # NEW: Emit MARK_DONE trace event for progress tracking
      #
      # API CORRECTION: shenbi.trace.writer does NOT export a module-level
      # write_event() function. The real API is the TraceWriter class:
      #   TraceWriter(round_dir).append(actor=..., actor_role=..., action=..., target=..., ...)
      # Construct one TraceWriter per emission (it is cheap; the underlying
      # writer reuses the per-round JSONL handle) and call .append().
      try:
          from shenbi.trace.writer import TraceWriter, ActorRole
          from datetime import datetime, timezone
          from pathlib import Path
          # The trace is organized per round under <project_dir>/trace/ (the
          # round dir). TraceWriter resolves its JSONL file from round_dir.
          round_dir = Path(state.project_dir) / "trace"
          round_dir.mkdir(parents=True, exist_ok=True)
          writer = TraceWriter(round_dir)
          writer.append(
              actor="pipeline",
              actor_role=ActorRole.SYSTEM,
              action="MARK_DONE",
              target=f"chapter-{chapter}",
              skill=skill_name,
              payload={"chapter": chapter, "timestamp": datetime.now(timezone.utc).isoformat()},
          )
      except Exception as e:
          logger.warning("mark_done_event_failed",
                         skill=skill_name, chapter=chapter, error=str(e))
  ```

  Materialize progress every 5 steps or at chapter completion:
  ```python
  def _maybe_materialize_progress(state, chapter: int) -> None:
      """Materialize progress.json from trace events."""
      steps_done = len(
          state.chapter_loop.chapter_states.get(str(chapter), {}).get('steps_done', [])
      )
      if steps_done % 5 == 0:
          try:
              from shenbi.trace.materialize import materialize_progress
              # API CORRECTION: materialize_progress requires the total_skills
              # keyword argument (the real signature is
              # materialize_progress(project_dir, total_skills)). Gather the
              # count of declared skills from the active CHAPTER_STEPS list.
              # (Import lazily to avoid a circular import at module load.)
              from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
              total_skills = [step.skill for step in CHAPTER_STEPS]  # list[str], not int
              materialize_progress(state.project_dir, total_skills=total_skills)
          except Exception:
              pass
  ```

  Auto-rebuild progress on resume if trace has events but progress.json is stale:
  ```python
  def _auto_rebuild_progress_if_stale(project_dir: Path) -> None:
      """Rebuild progress.json if trace events exist but progress is stale."""
      progress_path = project_dir / 'progress.json'
      trace_dir = project_dir / 'trace'

      if not trace_dir.exists():
          return

      trace_events = list(trace_dir.glob('*.jsonl'))
      if not trace_events:
          return

      if not progress_path.exists():
          logger.info("auto_rebuilding_progress_from_trace")
          from shenbi.trace.materialize import materialize_progress
          # API CORRECTION: materialize_progress requires total_skills kwarg.
          from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
          materialize_progress(project_dir, total_skills=len(CHAPTER_STEPS))
          return

      # Check staleness: trace has newer events than progress.json
      trace_mtime = max(p.stat().st_mtime for p in trace_events)
      if trace_mtime > progress_path.stat().st_mtime:
          logger.info("progress_stale_rebuilding_from_trace")
          from shenbi.trace.materialize import materialize_progress
          # API CORRECTION: materialize_progress requires total_skills kwarg.
          from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
          materialize_progress(project_dir, total_skills=len(CHAPTER_STEPS))
  ```

- [ ] **12b. Run `just check` -- confirm full pass.**

- [ ] **12c. Commit:** `fix(progress): emit MARK_DONE trace events and auto-rebuild progress.json on resume`

---

## Task 13: State Machine -- Heal current_step Corruption

**Files:**
- `src/shenbi/pipeline/state.py` -- `_heal_current_step()`, `_validate_state_consistency()`
- `src/shenbi/pipeline/chapter_loop.py` -- `_advance` sets `current_step`

- [ ] **13a. Write test:** Create `tests/pipeline/test_state_machine_heal.py`
  ```python
  """Test state machine current_step healing and validation."""
  import pytest
  from unittest.mock import MagicMock
  from shenbi.pipeline.state import (
      _heal_current_step,
      _validate_state_consistency,
  )
  from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

  class TestHealCurrentStep:
      def test_heals_empty_current_step_with_valid_index(self):
          state = MagicMock()
          state.chapter_loop.current_step = ""
          state.chapter_loop.step_index = 5  # Valid index

          _heal_current_step(state, CHAPTER_STEPS)
          assert state.chapter_loop.current_step != ""
          assert state.chapter_loop.current_step == CHAPTER_STEPS[5].skill

      def test_no_change_when_current_step_already_set(self):
          state = MagicMock()
          state.chapter_loop.current_step = "shenbi-chapter-drafting"
          state.chapter_loop.step_index = 4

          _heal_current_step(state, CHAPTER_STEPS)
          assert state.chapter_loop.current_step == "shenbi-chapter-drafting"

      def test_handles_step_index_beyond_list(self):
          state = MagicMock()
          state.chapter_loop.current_step = ""
          state.chapter_loop.step_index = 999  # Beyond list

          _heal_current_step(state, CHAPTER_STEPS)
          assert state.chapter_loop.current_step == "chapter_complete"

      def test_step_index_zero_with_empty_step(self):
          state = MagicMock()
          state.chapter_loop.current_step = ""
          state.chapter_loop.step_index = 0

          _heal_current_step(state, CHAPTER_STEPS)
          # At step 0, current_step maps to first step
          assert state.chapter_loop.current_step == CHAPTER_STEPS[0].skill

  class TestValidateStateConsistency:
      def test_detects_and_heals_corrupt_state(self):
          state = MagicMock()
          state.chapter_loop.current_step = ""
          state.chapter_loop.step_index = 9

          _validate_state_consistency(state, CHAPTER_STEPS)
          # Should auto-heal
          assert state.chapter_loop.current_step != ""

      def test_passes_consistent_state(self):
          state = MagicMock()
          state.chapter_loop.current_step = "shenbi-state-settling"
          state.chapter_loop.step_index = 7

          # Should not raise, should not change
          _validate_state_consistency(state, CHAPTER_STEPS)
          assert state.chapter_loop.current_step == "shenbi-state-settling"
  ```

- [ ] **13b. Run test -- confirm FAIL.**

- [ ] **13c. Implement** in `src/shenbi/pipeline/state.py`:
  ```python
  def _heal_current_step(state, CHAPTER_STEPS: list) -> None:
      """Heal current_step from step_index when current_step is empty.

      Fixes the known corruption bug: _advance sets step_index
      but not current_step, leaving it as "".
      """
      cl = state.chapter_loop
      if cl.current_step:
          return  # Already set, nothing to heal

      if cl.step_index <= 0:
          return  # Not yet started

      if cl.step_index < len(CHAPTER_STEPS):
          cl.current_step = CHAPTER_STEPS[cl.step_index].skill
      else:
          cl.current_step = "chapter_complete"

      logger.warning("healed_current_step",
                     step_index=cl.step_index,
                     new_current_step=cl.current_step)


  def _validate_state_consistency(state, CHAPTER_STEPS: list) -> list[str]:
      """Validate pipeline state consistency at resume. Heals if possible.

      Checks:
      - step_index > 0 but current_step is empty -> heal
      - step_index out of range -> clamp
      """
      issues = []
      cl = state.chapter_loop

      if not cl.current_step and cl.step_index > 0:
          issues.append(
              f"state_inconsistent: step_index={cl.step_index} "
              f"but current_step='' -- auto-healing"
          )
          _heal_current_step(state, CHAPTER_STEPS)

      if cl.step_index > len(CHAPTER_STEPS):
          issues.append(
              f"step_index={cl.step_index} exceeds CHAPTER_STEPS length "
              f"({len(CHAPTER_STEPS)}) -- clamping"
          )
          cl.step_index = len(CHAPTER_STEPS)
          cl.current_step = "chapter_complete"

      return issues
  ```

- [ ] **13d. Fix** `_advance` in `chapter_loop.py` (root cause: line 510 sets `state.chapter_loop.current_step = ""` -- never set to the next skill) to explicitly set `current_step`:
  ```python
  def _advance(state, CHAPTER_STEPS: list) -> None:
      """Advance to next step, setting both step_index and current_step.

      Root cause of the corruption: the existing _advance at chapter_loop.py:510
      sets step_index but leaves current_step = "". Fix: set both together.
      """
      cl = state.chapter_loop
      cl.step_index += 1

      # Explicitly set current_step alongside step_index
      if cl.step_index < len(CHAPTER_STEPS):
          cl.current_step = CHAPTER_STEPS[cl.step_index].skill
      else:
          cl.current_step = "chapter_complete"
  ```

- [ ] **13e. Run test -- confirm PASS.**

- [ ] **13f. Commit:** `fix(state): heal current_step corruption -- _advance sets both step_index and current_step`

---

## Task 14: Dynamic Timeout (all 3 paths)

> **Spec-aligned note (Spec 7 §3.5 Dynamic timeout):** The hardcoded 900s only applies to ONE of three dispatch paths. The fix MUST address ALL THREE: (a) **CLI subprocess** path (`subprocess.run(..., timeout=...)` -- currently 900s), (b) **API path** (`_dispatch_via_api` -- passes NO timeout to `client.chat.completions.create` today; the `_call_llm` retry wrapper from Task 3 handles transient errors but enforces no wall-clock ceiling), (c) **IDE-CLI path** (`_IDE_AGENT_TIMEOUT = 900` hardcoded at `dispatch_helper.py:47`, used at line 512). All three must scale with chapter size using the same `_compute_dispatch_timeout` formula.

**Files:**
- `src/shenbi/pipeline/dispatch_helper.py` -- `_compute_dispatch_timeout()` applied to all 3 paths

- [ ] **14a. Implement** dynamic timeout:
  ```python
  def _compute_dispatch_timeout(
      skill_name: str,
      chapter_path: Path | None = None,
  ) -> int:
      """Compute adaptive dispatch timeout based on chapter size.

      base = 300s (5 min)
      extra = 30s per KB of chapter size
      cap = 1800s (30 min)
      state-settling gets 2x multiplier.

      Applied to ALL THREE dispatch paths (CLI subprocess, API, IDE-CLI).
      """
      base = 300
      extra = 0

      if chapter_path and chapter_path.exists():
          chapter_size_kb = chapter_path.stat().st_size / 1024
          extra = int(chapter_size_kb * 30)

      timeout = min(base + extra, 1800)

      # state-settling is the heaviest step -- double timeout
      if skill_name == "shenbi-state-settling":
          timeout = min(int(timeout * 2.0), 1800)

      return timeout


  def _handle_timeout_gracefully(skill_name: str, chapter: int) -> None:
      """Graceful degradation on timeout.

      Save partial LLM output, log WARN (not HARD failure).
      """
      logger.warning("dispatch_timeout",
                     skill=skill_name,
                     chapter=chapter,
                     resolution="saving_partial_output")
      # Reuse previous truth file versions for incomplete updates
      # This is logged for observability; actual handling depends on skill
  ```

- [ ] **14b. Wire `_compute_dispatch_timeout` into all THREE paths:**
  ```python
  # (a) CLI subprocess path -- replace the hardcoded 900s:
  timeout = _compute_dispatch_timeout(skill_name, chapter_path)
  r = subprocess.run(cmd, ..., timeout=timeout)

  # (b) API path -- currently passes NO timeout; add it:
  timeout = _compute_dispatch_timeout(skill_name, chapter_path)
  response = client.chat.completions.create(
      model=model, messages=messages, timeout=timeout
  )

  # (c) IDE-CLI path -- replace the hardcoded _IDE_AGENT_TIMEOUT (line 47,
  #     used at line 512). Scale _IDE_AGENT_TIMEOUT with chapter size using
  #     the same formula instead of the constant 900:
  ide_timeout = _compute_dispatch_timeout(skill_name, chapter_path)
  ```

- [ ] **14c. Run `just check` -- confirm full pass.**

- [ ] **14d. Commit:** `feat(dispatch): add dynamic timeout across all 3 paths (CLI subprocess, API, IDE-CLI) scaling with chapter size`

---

## Task 15: End-to-End Verification

- [ ] **15a.** Run `just check` full suite -- confirm PASS.
- [ ] **15b.** Confirm P0.1-P0.4 remain fixed (verification only -- already fixed in current code, see Task 1):
  - `shenbi-phase start` does not raise FileNotFoundError (P0.1 -- run_gate uses `shenbi.gates.cli` + OSError catch)
  - `pipeline --help` does not show `rollback` (P0.3)
  - `grep -r "codex.api\|codex_api" src/shenbi/dispatcher/executor.py` returns nothing (P0.4)
- [ ] **15c.** Run crash recovery test (signal handlers + atexit + checkpoint-on-step):
  - Start pipeline, send SIGTERM mid-run
  - Verify pipeline state saved, emergency snapshot created
  - Resume and verify recovery from emergency shutdown
- [ ] **15d.** Run 3-chapter mini-pipeline:
  - Verify per-step timing in logs
  - Verify token usage in logs
  - Verify `progress.json` updates after each chapter (confirms MARK_DONE events now emitted)
- [ ] **15e.** Verify dynamic timeout across ALL 3 paths: check 10KB chapter gets ~600s, 38KB gets ~1440s for the CLI subprocess, API, and IDE-CLI paths.
- [ ] **15f.** Verify 100-chapter simulated state compaction < 100KB.

- [ ] **15g. Commit:** `test: end-to-end verification of pipeline infrastructure and resilience`
