# 推理控制层审计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地推理控制层 audit spec 的 P0 修复——finish_reason=length 截断检测 + drafting max_tokens cap 校准 + score/discriminative-review 温度覆盖；以及低风险的 P1 文档订正（pro→flash drift）和 P2 退避抖动加大。

**Architecture:** 改动集中在 3 层：(1) `_call_llm_streaming` 从 final chunk 读 `finish_reason`，返回新增第 4 元素；(2) `_dispatch_via_api` 在 tenacity `@retry` 之外新增 cap-raise 循环（length → 提 max_tokens 重发 1 次，content_filter → hard fail）；(3) `executor_config.toml` 加 score-*/判别队列温度覆盖 + drafting max_tokens 提升。P1/P2 的文档订正和抖动常量改为独立 task。

**Tech Stack:** Python 3.11+ / OpenAI SDK streaming / tomllib config / structlog / pytest

## Global Constraints

- **AGENTS.md**: Gate 函数无副作用；框架代码无 `print()`；`pathlib.Path` for file I/O；structlog for logging
- **basedpyright strict**: 所有新代码必须通过 strict type check（`reportMissingTypeArgument`、`reportArgumentType` 等）
- **ruff**: `src/` 有 per-file-ignore，`tools/` 没有——magic values 须提常量
- **G4 是唯一质量裁判**: 所有采样参数变更以 gate 仍 PASS 为前提
- **API probe 前置**: drafting max_tokens 提升前须 probe 确认 `deepseek-v4-flash` 接受目标值（若不接受，2.2 转为"须拆章"超出本 spec）
- **本 plan 只覆盖可离线实现的代码层改动**：G4 round 对比验证（需真实 API 调用）留为 spec 验证标准，不在本 plan 的 task 范围内（无法在 CI 中跑真实 LLM dispatch）

## AC 覆盖表

| Spec AC | Task | Test |
|---|---|---|
| §6: finish_reason 检测 (length→提 cap / content_filter→hard fail) | T1 (read finish_reason) + T2 (cap-raise loop) | T1 test mock chunk with finish_reason; T2 test mock _call_llm_streaming_with_retry returning length/content_filter |
| §6: score-* 温度 0/3→3/3 (0.1) | T4 | T4 test config parse |
| §6: drafting 截断率 AVG 96%→0 | T3 (API probe guard + config) + T1+T2 (detection) | T2 test cap-raise on length |
| §6: review 判别队列 0/9→9/9 (0.1-0.2) | T4 | T4 test config parse |
| §5.2: pro→flash doc drift 订正 | T5 | T5 grep verify |
| §5.3: 退避抖动加大 | T6 | T6 test backoff range |
| §5.2: pricing.py 同步 | T7 (stretch, blocked on 2.4 pilot, 仅加 fail-loud guard) | T7 test unknown model raises |

---

### Task 1: `_call_llm_streaming` 读取 `finish_reason`（infra）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1371-1415` (`_call_llm_streaming`)
- Test: `tests/pipeline/test_dispatch_helper_finish_reason.py` (Create)

**Interfaces:**
- Consumes: OpenAI streaming chunk structure (`chunk.choices[0].finish_reason`)
- Produces: `_call_llm_streaming` return type changes from `tuple[str, str | None, Any]` to `tuple[str, str | None, Any, str | None]` — 4th element is `finish_reason: str | None` (values: `"length"`, `"content_filter"`, `"stop"`, `"tool_calls"`, or `None` if not available)
- **Breaking**: All callers of `_call_llm_streaming` must be updated. Only caller is `_call_llm_streaming_with_retry` (:1428) which must also pass through the 4th element.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for finish_reason detection in _call_llm_streaming (spec §2.9)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from shenbi.pipeline.dispatch_helper import _call_llm_streaming


def _make_chunk(content: str | None = None, finish_reason: str | None = None, usage=None) -> Any:
    """Build a fake OpenAI streaming chunk."""
    delta = SimpleNamespace(content=content)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


def test_finish_reason_length_captured():
    """When the final chunk has finish_reason='length', it must be returned."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="Hello "),
            _make_chunk(content="world"),
            _make_chunk(content=None, finish_reason="length"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "length"
    assert result == "Hello world"


def test_finish_reason_stop_captured():
    """Normal completion has finish_reason='stop'."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="Done"),
            _make_chunk(content=None, finish_reason="stop"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "stop"


def test_finish_reason_content_filter_captured():
    """content_filter finish_reason must be surfaced (spec §5.1 C2)."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            _make_chunk(content="some "),
            _make_chunk(content=None, finish_reason="content_filter"),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason == "content_filter"


def test_finish_reason_none_when_no_choices():
    """When chunks have no choices, finish_reason stays None."""
    client = MagicMock()
    client.chat.completions.create.return_value = iter(
        [
            SimpleNamespace(choices=[], usage=None),
        ]
    )
    result, stop_reason, usage, finish_reason = _call_llm_streaming(
        client, "test-model", [{"role": "user", "content": "hi"}]
    )
    assert finish_reason is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_dispatch_helper_finish_reason.py -v`
Expected: FAIL — `ValueError: too many values to unpack` (current returns 3-tuple, test unpacks 4)

- [ ] **Step 3: Implement finish_reason capture in `_call_llm_streaming`**

Modify `_call_llm_streaming` (`dispatch_helper.py:1371-1415`):

```python
def _call_llm_streaming(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    early_stop_patterns: list[str] | None = None,
    **kwargs: Any,
) -> tuple[str, str | None, Any, str | None]:
    """Stream LLM response with optional early-stop patterns.

    Returns (collected_text, stop_reason, usage, finish_reason) where:
    - stop_reason: None for normal completion or early_stop description string
    - usage: token usage object from the API response (or None)
    - finish_reason: API's finish_reason from the final chunk (e.g. "length",
      "content_filter", "stop", "tool_calls"), or None if unavailable.
      Spec §2.9: this is the truncation detection signal.
    """
    collected: list[str] = []
    stop_reason: str | None = None
    usage: Any = None
    finish_reason: str | None = None
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
        **kwargs,
    )
    for chunk in stream:
        # Collect usage from final chunk (when stream_options include_usage is set)
        if hasattr(chunk, "usage") and chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices:
            choice = chunk.choices[0]
            # Spec §2.9: capture finish_reason from the final chunk.
            # Use getattr (not attribute access) because existing test fake chunks
            # (test_dispatch_usage_capture.py, test_retry.py) build SimpleNamespace
            # or MagicMock choices that may not have finish_reason set.
            chunk_finish = getattr(choice, "finish_reason", None)
            if chunk_finish is not None:
                finish_reason = chunk_finish
            delta_content = getattr(choice.delta, "content", None)
            if delta_content:
                collected.append(choice.delta.content)
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
        log.info("streaming_early_stop", reason=stop_reason)
    if finish_reason == "length":
        log.warning("length_truncation_detected", model=model)
    # Fallback: try stream.usage if not captured from individual chunks
    if usage is None and hasattr(stream, "usage") and stream.usage is not None:
        usage = stream.usage
    return result, stop_reason, usage, finish_reason
```

Key changes:
1. Return type: `tuple[str, str | None, Any]` → `tuple[str, str | None, Any, str | None]`
2. New local: `finish_reason: str | None = None`
3. In the chunk loop: `if chunk.choices:` guard (was `if chunk.choices and chunk.choices[0].delta.content:` — the `and` gate structurally skipped the final chunk where `delta.content` is None but `finish_reason` arrives). Split into `if chunk.choices:` + nested `if choice.delta.content:`. **This is the critical fix — the old code's truthiness gate on `delta.content` prevented finish_reason from ever being observed.**
4. Log `length_truncation_detected` warning when finish_reason == "length"
5. Return 4th element

- [ ] **Step 4: Update `_call_llm_streaming_with_retry` to pass through 4th element**

Modify `_call_llm_streaming_with_retry` (`dispatch_helper.py:1428-1449`):

```python
def _call_llm_streaming_with_retry(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    early_stop_patterns: list[str] | None = None,
    **kwargs: Any,
) -> tuple[str, str | None, Any, str | None]:
    """Stream LLM response with retry on transient failures.

    Retries: 429 (rate limit), 5xx (server errors), timeouts.
    Does NOT retry: 400, 401, 403 (client errors).

    Returns (collected_text, stop_reason, usage, finish_reason).
    """
    return _call_llm_streaming(
        client,
        model,
        messages,
        early_stop_patterns=early_stop_patterns,
        **kwargs,
    )
```

Changes: return type annotation updated; the `return` statement is unchanged (it uses `**kwargs` passthrough and tuple unpacking happens naturally).

- [ ] **Step 5: Update `_dispatch_via_api` caller to receive 4th element**

Modify `_dispatch_via_api` (`dispatch_helper.py:1515`):

```python
        output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
```

(Add `, finish_reason` to the unpacking.)

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/pipeline/test_dispatch_helper_finish_reason.py -v`
Expected: 4 PASS

- [ ] **Step 7: Run full dispatch_helper test suite to verify no regressions**

Run: `pytest tests/pipeline/test_dispatch_helper_*.py -v`
Expected: All existing tests PASS (they unpack 3-tuple from _call_llm_streaming_with_retry — **these will break** if they mock the return. Check and update any test that mocks the return value.)

- [ ] **Step 8: Fix any broken tests that mock the old 3-tuple return**

Search for ALL tests that interact with the streaming chain (not just by name — structurally coupled tests exist):
```bash
grep -rn "_call_llm_streaming\|_dispatch_via_api\|chat.completions.create\|_fake_chunk\|SimpleNamespace(delta" tests/
```
Key files to check:
- `tests/pipeline/test_retry.py:37,54,93` — unpacks 3-tuple from `_call_llm_streaming_with_retry`. Update to 4-tuple (append `_` for unused finish_reason).
- `tests/unit/pipeline/test_dispatch_usage_capture.py:10-14` — builds `SimpleNamespace(choices=[SimpleNamespace(delta=...)])` WITHOUT `finish_reason`. The `getattr(choice, "finish_reason", None)` guard in Step 3 handles this, but verify no AttributeError leaks.

Update any mock that returns a 3-tuple to return a 4-tuple (append `None` as finish_reason).

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_finish_reason.py
git commit -m "feat(dispatch): capture finish_reason from streaming chunks (spec §2.9)

_call_llm_streaming now reads choices[0].finish_reason from the final
chunk. The old delta.content truthiness gate structurally skipped the
final chunk (where content=None but finish_reason arrives). Return type
expanded to 4-tuple: (text, stop_reason, usage, finish_reason).
_call_llm_streaming_with_retry and _dispatch_via_api updated to unpack."
```

---

### Task 2: cap-raise 循环 + content_filter hard fail in `_dispatch_via_api`（infra）

**⚠ Prerequisite: T1 must land first.** T2's cap-raise code consumes the `finish_reason` 4th element from T1's return-type change. Do not reorder.

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1514-1567` (`_dispatch_via_api` streaming section)
- Test: `tests/pipeline/test_dispatch_helper_cap_raise.py` (Create)

**Interfaces:**
- Consumes: `finish_reason` from T1's 4th return element; `_get_skill_max_tokens(skill)` for initial cap
- Produces: `_dispatch_via_api` behavior: on `finish_reason="length"`, raises max_tokens to min(initial×2, model_output_ceiling×0.9) and resends **once** (outside tenacity); on `finish_reason="content_filter"`, returns `DispatchResult(False, ...)` immediately without retry

- [ ] **Step 1: Write the failing test**

```python
"""Tests for finish_reason-driven cap-raise and content_filter hard-fail (spec §5.1)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
from pathlib import Path

from shenbi.pipeline.dispatch_helper import _dispatch_via_api, DispatchResult


def test_length_truncation_triggers_cap_raise_resend(monkeypatch):
    """finish_reason='length' → raise max_tokens and resend once (not same-params)."""
    # Track the max_tokens used in each call
    max_tokens_used: list[int] = []

    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        max_tokens_used.append(kwargs.get("max_tokens", 16384))
        if call_count[0] == 1:
            # First call: truncated
            return ("truncated output...", None, MagicMock(), "length")
        # Second call (cap-raised): complete
        return ("complete output", None, MagicMock(), "stop")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    # Mock _build_skill_prompt to avoid file I/O
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    # Mock _write_parsed_outputs to avoid file writes
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._write_parsed_outputs",
        lambda *a, **kw: True,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._parse_structured_output",
        lambda text: MagicMock(files=[]),
    )

    result = _dispatch_via_api("shenbi-chapter-drafting", Path("/tmp/proj"), "test prompt")

    assert call_count[0] == 2  # exactly 2 calls: original + 1 cap-raise resend
    assert max_tokens_used[1] > max_tokens_used[0]  # cap was raised


def test_content_filter_is_hard_fail(monkeypatch):
    """finish_reason='content_filter' → immediate DispatchResult(False), no resend."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        return ("filtered...", None, MagicMock(), "content_filter")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )

    result = _dispatch_via_api("shenbi-chapter-drafting", Path("/tmp/proj"), "test prompt")

    assert call_count[0] == 1  # no resend
    assert result.success is False
    assert "content_filter" in result.stderr


def test_cap_raise_capped_at_model_ceiling(monkeypatch):
    """When cap is already at ceiling (raised_cap <= original_cap), fail-fast with NO resend."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        return ("truncated...", None, MagicMock(), "length")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    # Set ceiling = drafting's configured max_tokens so raised_cap (min(cap*2, ceiling))
    # == ceiling == original_cap → raised_cap <= original_cap → fail-fast, NO resend.
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._MODEL_OUTPUT_CEILING",
        32768,  # == drafting's max_tokens after T3
    )

    result = _dispatch_via_api("shenbi-chapter-drafting", Path("/tmp/proj"), "test prompt")

    assert call_count[0] == 1  # fail-fast BEFORE any resend (raised_cap <= original_cap)
    assert result.success is False
    assert "ceiling" in result.stderr.lower()


def test_cap_raise_persistent_length_fail_fast(monkeypatch):
    """After cap-raise resend, if STILL length → fail-fast (spec §5.1: max 1 resend)."""
    call_count = [0]

    def mock_streaming_with_retry(client, model, messages, **kwargs):
        call_count[0] += 1
        # Always returns length — even after cap-raise
        return ("still truncated...", None, MagicMock(), "length")

    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry",
        mock_streaming_with_retry,
    )
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._build_skill_prompt",
        lambda *a, **kw: ("sys", "user", []),
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._write_parsed_outputs",
        lambda *a, **kw: True,
    )
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._parse_structured_output",
        lambda text: MagicMock(files=[]),
    )
    # Ceiling high enough that cap-raise DOES fire (65536 > drafting's 32768)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper._MODEL_OUTPUT_CEILING",
        65536,
    )

    result = _dispatch_via_api("shenbi-chapter-drafting", Path("/tmp/proj"), "test prompt")

    assert call_count[0] == 2  # original + exactly 1 cap-raise resend (then fail-fast)
    assert result.success is False
    assert "still exceeds" in result.stderr.lower() or "persistent" in result.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_dispatch_helper_cap_raise.py -v`
Expected: FAIL — `_MODEL_OUTPUT_CEILING` doesn't exist; cap-raise logic doesn't exist

- [ ] **Step 3: Add model output ceiling constant and cap-raise logic**

Add constant near the top of `dispatch_helper.py` (after `_DEFAULT_MODEL` at :67):

```python
#: Hard ceiling for max_tokens cap-raise (spec §5.1 C1, §7 iron rule #2).
#: The cap-raise on finish_reason=length will not exceed this × 0.9
#: (spec mandates 0.9 safety factor below the ceiling).
#: Must be > drafting's configured max_tokens (32768 after T3) so that
#: int(65536 * 0.9) = 58982 > 32768 and the cap-raise has headroom to fire.
#: If the model's actual output limit is lower, the API will 400 and the
#: error surfaces via the existing except block.
_MODEL_OUTPUT_CEILING = 65536
```

Modify `_dispatch_via_api` streaming section (`dispatch_helper.py:1514-1533`):

```python
try:
    output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
        client,
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=_get_skill_temperature(skill),
        max_tokens=_get_skill_max_tokens(skill),
        timeout=api_timeout,
    )
except Exception as exc:
    _handle_timeout_gracefully(skill, chapter)
    log.error("api_call_failed", skill=skill, error=str(exc))
    return DispatchResult(False, -1, "", f"API call failed: {exc}")

# Spec §5.1: finish_reason-driven cap-raise (outside tenacity @retry).
if finish_reason == "content_filter":
    log.error("content_filter_blocked", skill=skill)
    return DispatchResult(False, -1, "", "content_filter: output blocked by provider safety filter")

if finish_reason == "length":
    original_cap = _get_skill_max_tokens(skill)
    raised_cap = min(original_cap * 2, int(_MODEL_OUTPUT_CEILING * 0.9))
    if raised_cap <= original_cap:
        # Cap already at ceiling — can't raise further.
        log.error(
            "length_truncation_at_ceiling",
            skill=skill,
            cap=original_cap,
            ceiling=_MODEL_OUTPUT_CEILING,
        )
        return DispatchResult(
            False,
            -1,
            "",
            f"length_truncation: output exceeded max_tokens={original_cap} and cap "
            f"is at model ceiling {_MODEL_OUTPUT_CEILING}. Chapter too long — "
            f"consider splitting (spec §2.9 fail-fast).",
        )
    log.warning(
        "length_truncation_cap_raise",
        skill=skill,
        original_cap=original_cap,
        raised_cap=raised_cap,
    )
    try:
        output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
            client,
            model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=_get_skill_temperature(skill),
            max_tokens=raised_cap,
            timeout=api_timeout,
        )
    except Exception as exc:
        _handle_timeout_gracefully(skill, chapter)
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")

    # After cap-raise, if STILL length → fail-fast (spec §5.1: max 1 resend).
    if finish_reason == "length":
        log.error(
            "length_truncation_persistent",
            skill=skill,
            raised_cap=raised_cap,
        )
        return DispatchResult(
            False,
            -1,
            "",
            f"length_truncation: output still exceeds raised cap={raised_cap}. "
            f"Chapter too long for model output limit — consider splitting.",
        )
    if finish_reason == "content_filter":
        log.error("content_filter_blocked_after_cap_raise", skill=skill)
        return DispatchResult(
            False,
            -1,
            "",
            "content_filter: output blocked by provider safety filter (after cap-raise)",
        )
# If we reach here (no length/content_filter, or cap-raise succeeded with
# finish_reason="stop"), output_text is valid — fall through to the existing
# _parse_structured_output / _write_parsed_outputs block at dispatch_helper.py:1542+.
# No code change needed in that downstream block — it uses the (possibly
# reassigned) output_text variable naturally.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_dispatch_helper_cap_raise.py -v`
Expected: 3 PASS

- [ ] **Step 5: Run full pipeline test suite for regressions**

Run: `pytest tests/pipeline/ -v -x`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_cap_raise.py
git commit -m "feat(dispatch): cap-raise on length truncation + content_filter hard fail

Spec §5.1/§2.9: when finish_reason='length', raise max_tokens to
min(cap×2, ceiling×0.9) and resend exactly once (outside tenacity).
If still truncated → fail-fast 'chapter too long'. When
finish_reason='content_filter' → immediate DispatchResult(False).
_MODEL_OUTPUT_CEILING=32768 constant bounds cap-raise (C1 fix)."
```

---

### Task 3: drafting `max_tokens` config + API probe guard（leaf）

**Files:**
- Modify: `executor_config.toml:5-7` (drafting override)
- Test: `tests/pipeline/test_executor_config.py` (Create or extend)

**Interfaces:**
- Consumes: spec §2.2 — drafting output AVG 15,787 tokens (96% of 16384 cap)
- Produces: `executor_config.toml` drafting `max_tokens` raised to 32768 (conservative P99 estimate; will be re-calibrated post-probe)

**Note**: The API probe (spec §2.2 验证 step 1) requires a live API call and cannot run in CI. This task only sets the config value + adds a documentation comment about the probe requirement. The actual probe is a manual pre-deployment step.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for executor_config.toml drafting max_tokens (spec §2.2)."""

from __future__ import annotations

import tomllib
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_drafting_max_tokens_raised():
    """drafting max_tokens must be >16384 (was 16384 = no-op override, spec §2.2)."""
    config_path = _PROJECT_ROOT / "executor_config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    drafting = config["overrides"]["shenbi-chapter-drafting"]
    assert drafting["max_tokens"] > 16384, (
        f"drafting max_tokens={drafting['max_tokens']} should be raised "
        f"above default 16384 to prevent truncation (spec §2.2: AVG output 96% of cap)"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_executor_config.py::test_drafting_max_tokens_raised -v`
Expected: FAIL — current drafting max_tokens = 16384 (not > 16384)

- [ ] **Step 3: Raise drafting max_tokens in config**

Modify `executor_config.toml:5-7`:

```toml
[overrides."shenbi-chapter-drafting"]
temperature = 0.85
# Spec §2.2: drafting AVG output 15,787 tokens (96% of old 16384 cap).
# Raised to 32768 to eliminate truncation. PRE-DEPLOYMENT: probe
# `deepseek-v4-flash` with max_tokens=32768 to confirm model accepts it.
# If model hard-limits below 32768, root cause shifts to "chapter too long"
# (prompt-content layer, out of scope — see spec §2.9 fail-fast).
max_tokens = 32768
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_executor_config.py::test_drafting_max_tokens_raised -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add executor_config.toml tests/pipeline/test_executor_config.py
git commit -m "feat(config): raise drafting max_tokens 16384→32768 (spec §2.2)

AVG drafting output was 96% of the 16384 cap → frequent truncation.
Raised to 32768 CONDITIONAL on API probe confirming deepseek-v4-flash
accepts max_tokens=32768. If probe fails, root cause shifts to
'chapter too long' (prompt-content layer, see spec §2.9 fail-fast)."
```

---

### Task 4: score-* + 判别队列 review 温度覆盖（leaf）

**Files:**
- Modify: `executor_config.toml` (add 12 overrides: 3 score + 9 discriminative review)
- Test: `tests/pipeline/test_executor_config.py` (extend)

**Interfaces:**
- Consumes: spec §2.1 — 3 score-* + 9 discriminative review skills at default 0.7
- Produces: `executor_config.toml` overrides for 12 skills at temperature 0.1

- [ ] **Step 1: Write the failing test**

```python
def test_score_skills_have_low_temperature():
    """All 3 score-* skills must have temperature ≤0.2 (spec §2.1 P0)."""
    config_path = _PROJECT_ROOT / "executor_config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    overrides = config.get("overrides", {})
    for skill in ("shenbi-score-arc", "shenbi-score-stratum", "shenbi-score-volume"):
        assert skill in overrides, f"{skill} missing temperature override"
        temp = overrides[skill]["temperature"]
        assert temp <= 0.2, f"{skill} temperature={temp} should be ≤0.2"


def test_discriminative_review_queue_has_low_temperature():
    """9 discriminative review skills must have temperature ≤0.2 (spec §2.1 P0)."""
    config_path = _PROJECT_ROOT / "executor_config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    overrides = config.get("overrides", {})
    discriminative = [
        "shenbi-review-memo-compliance",
        "shenbi-review-world-rules",
        "shenbi-review-arc-payoff",
        "shenbi-review-pov",
        "shenbi-review-era",
        "shenbi-review-fanfic",
        "shenbi-review-sensitivity",
        "shenbi-review-spinoff",
        "shenbi-review-dialogue",
    ]
    for skill in discriminative:
        assert skill in overrides, f"{skill} missing temperature override"
        temp = overrides[skill]["temperature"]
        assert temp <= 0.2, f"{skill} temperature={temp} should be ≤0.2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_executor_config.py::test_score_skills_have_low_temperature tests/pipeline/test_executor_config.py::test_discriminative_review_queue_has_low_temperature -v`
Expected: FAIL — these skills have no overrides

- [ ] **Step 3: Add 12 temperature overrides to executor_config.toml**

Append to `executor_config.toml`:

```toml
# Spec §2.1 P0: score-* (most deterministic task) + discriminative review queue.
# Evaluative queue (texture/reader-pull/highpoint/pacing/long-span/motivation/
# character/group-craft) deferred to P1 pilot. Aggregator queue (group-character/
# group-factual/group-plan/foreshadowing) deferred to plan-stage decision.

[overrides."shenbi-score-arc"]
temperature = 0.1

[overrides."shenbi-score-stratum"]
temperature = 0.1

[overrides."shenbi-score-volume"]
temperature = 0.1

[overrides."shenbi-review-memo-compliance"]
temperature = 0.1

[overrides."shenbi-review-world-rules"]
temperature = 0.1

[overrides."shenbi-review-arc-payoff"]
temperature = 0.1

[overrides."shenbi-review-pov"]
temperature = 0.15

[overrides."shenbi-review-era"]
temperature = 0.1

[overrides."shenbi-review-fanfic"]
temperature = 0.1

[overrides."shenbi-review-sensitivity"]
temperature = 0.1

[overrides."shenbi-review-spinoff"]
temperature = 0.15

[overrides."shenbi-review-dialogue"]
temperature = 0.15
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_executor_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add executor_config.toml tests/pipeline/test_executor_config.py
git commit -m "feat(config): add temperature overrides for score-* + discriminative reviews

Spec §2.1 P0: 3 score-* at 0.1 + 9 discriminative review at 0.1-0.15.
Evaluative (8) + aggregator (4) queues deferred to P1/plan (spec §2.1)."
```

---

### Task 5: 订正归档 plan 文档 pro→flash drift（leaf）

**Files:**
- Modify: `docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md` (18 occurrences of "deepseek-v4-pro")
- Test: grep verification (no Python test — doc-only)

**Interfaces:**
- Consumes: spec §2.5 — archived plan writes "deepseek-v4-pro" but code is "deepseek-v4-flash"
- Produces: doc consistency (code is source of truth)

- [ ] **Step 1: Verify the drift exists**

Run: `grep -c "deepseek-v4-pro" docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md`
Expected: 18

- [ ] **Step 2: Replace all occurrences**

Run:
```bash
sed -i '' 's/deepseek-v4-pro/deepseek-v4-flash/g' docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md
```

Also fix the test function name and the pro pricing line. The actual format uses `1_000_000` with spaces (verified at line 134: `"input": 1.10 / 1_000_000`):
```bash
sed -i '' 's/test_default_model_is_deepseek_v4_pro/test_default_model_is_deepseek_v4_flash/g' docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md
sed -i '' 's/"input": 1.10 \/ 1_000_000, "output": 4.40 \/ 1_000_000/"input": 0.14 \/ 1_000_000, "output": 0.28 \/ 1_000_000/g' docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md
```
**Note:** If the sed pattern doesn't match (format may vary), verify line 134 manually and edit with the Edit tool instead.

- [ ] **Step 3: Verify the fix**

Run: `grep -c "deepseek-v4-pro" docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md`
Expected: 0

Run: `grep -c "deepseek-v4-flash" docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md`
Expected: ≥18

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/archive/2026-07-19-03-pipeline-cost-and-token-accounting-plan.md
git commit -m "docs(archive): correct pro→flash model drift in cost plan (spec §2.5)

Archived plan wrote deepseek-v4-pro (\$1.10/\$4.40) but code uses
deepseek-v4-flash (\$0.14/\$0.28) since the flash downgrade. Code is
source of truth — 18 occurrences corrected + prices + test name."
```

---

### Task 6: parallel_dispatch 退避抖动加大（leaf）

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:34` (`RETRY_JITTER`)
- Test: `tests/pipeline/test_parallel_dispatch_backoff.py` (Create)

**Interfaces:**
- Consumes: spec §5.3 / §2.8 — jitter 0-1s too small to decorrelate 4 workers
- Produces: `RETRY_JITTER` raised from 1.0 to 2.0 (= `RETRY_BACKOFF_BASE`), making jitter same-magnitude as backoff base

- [ ] **Step 1: Write the failing test**

```python
"""Tests for parallel_dispatch backoff jitter (spec §5.3)."""

from __future__ import annotations

from shenbi.pipeline.parallel_dispatch import RETRY_JITTER, RETRY_BACKOFF_BASE


def test_jitter_same_magnitude_as_base():
    """Jitter range must be ≥ backoff base to decorrelate workers (spec §5.3/§2.8).

    Old: RETRY_JITTER=1.0, RETRY_BACKOFF_BASE=2.0 → jitter was half the base,
    workers near-lockstep. Fix: jitter ≥ base so workers decorrelate.
    """
    assert RETRY_JITTER >= RETRY_BACKOFF_BASE, (
        f"RETRY_JITTER={RETRY_JITTER} should be ≥ RETRY_BACKOFF_BASE={RETRY_BACKOFF_BASE} "
        f"to decorrelate parallel workers (spec §2.8 thundering herd fix)"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_parallel_dispatch_backoff.py -v`
Expected: FAIL — RETRY_JITTER=1.0 < RETRY_BACKOFF_BASE=2.0

- [ ] **Step 3: Raise RETRY_JITTER**

Modify `parallel_dispatch.py:33-34`:

```python
#: Random jitter range for backoff (seconds, uniform [0, jitter]).
#: Spec §5.3/§2.8: jitter must be same-magnitude as RETRY_BACKOFF_BASE
#: to decorrelate parallel workers (old 1.0 was half the base → near-lockstep).
RETRY_JITTER = 2.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_parallel_dispatch_backoff.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/parallel_dispatch.py tests/pipeline/test_parallel_dispatch_backoff.py
git commit -m "fix(parallel): widen backoff jitter 1.0→2.0 to decorrelate workers (spec §2.8)

Old jitter (0-1s) was half the backoff base (2^attempt) → workers
near-lockstep on 429. Raised to 2.0 (= RETRY_BACKOFF_BASE) so jitter
is same-magnitude. Token bucket dropped (YAGNI for 4 workers, spec §5.3)."
```

---

### Task 7: pricing.py fail-loud on unknown model（leaf, stretch）

**Note:** This task adds a fail-loud guard to `estimate_cost` when a model has no PRICING entry. The actual pilot model routing (spec §2.4) requires live API + G4 validation and is **out of scope** for this plan. This task only adds the guard so that when routing is eventually added, cost accounting won't silently fall back.

**Files:**
- Modify: `src/shenbi/cost/pricing.py:39-52` (`estimate_cost`)
- Test: `tests/unit/test_pricing_fail_loud.py` (Create)

**Interfaces:**
- Consumes: spec §5.2 I3 — `estimate_cost` silently falls back to DEFAULT_PRICING_MODEL for unknown models
- Produces: `estimate_cost` raises `ValueError` for unknown models (instead of silent fallback); existing callers that pass `None` or the default model are unaffected

- [ ] **Step 1: Write the failing test**

```python
"""Tests for pricing.py fail-loud on unknown model (spec §5.2 I3)."""

from __future__ import annotations

import pytest

from shenbi.cost.pricing import estimate_cost


def test_known_model_succeeds():
    """The default model must still work."""
    cost = estimate_cost({"prompt_tokens": 1000, "completion_tokens": 500})
    assert cost > 0


def test_unknown_model_raises():
    """Unknown models must raise ValueError, not silently fall back (spec I3)."""
    with pytest.raises(ValueError, match="unknown model"):
        estimate_cost(
            {"prompt_tokens": 1000, "completion_tokens": 500},
            model="deepseek-v4-pro",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pricing_fail_loud.py -v`
Expected: FAIL — `test_unknown_model_raises` fails because current code silently falls back

- [ ] **Step 3: Add fail-loud guard**

Modify `pricing.py:39-52`:

```python
def estimate_cost(usage: dict[str, Any], model: str | None = None) -> float:
    """Estimate USD cost for a usage dict.

    Args:
        usage: dict with 'prompt_tokens' and 'completion_tokens' (int).
        model: explicit model name; None resolves from env/default.

    Raises:
        ValueError: if the resolved model has no PRICING entry (spec §5.2 I3).
    """
    resolved = resolve_model(model)
    if resolved not in PRICING:
        raise ValueError(
            f"unknown model '{resolved}': no PRICING entry. "
            f"Add it to PRICING or use a known model. "
            f"Known: {list(PRICING.keys())}"
        )
    rates = PRICING[resolved]
    input_cost = int(usage.get("prompt_tokens", 0)) * rates["input"]
    output_cost = int(usage.get("completion_tokens", 0)) * rates["output"]
    return input_cost + output_cost
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_pricing_fail_loud.py -v`
Expected: 2 PASS

- [ ] **Step 5: Delete the old fallback test and guard the ledger hot-path**

The existing test `tests/unit/cost/test_pricing.py:73-78` `test_unknown_model_falls_back_to_default` encodes the OLD silent-fallback contract. It MUST be deleted — it will fail after Step 3.

```bash
# Delete the old test (it tested the silent-fallback behavior we're removing):
# Open tests/unit/cost/test_pricing.py and DELETE the test_unknown_model_falls_back_to_default method (lines 73-78).
```

**Unconditionally guard the ledger hot-path**: `src/shenbi/cost/ledger.py:62` calls `estimate_cost(usage, resolved)` with no try/except. If `SHENBI_LLM_MODEL` env var is set to an unregistered model, this now raises `ValueError`, crashing the dispatch. Add a guard:

Modify `src/shenbi/cost/ledger.py:62`:

```python
total_tokens = (int(usage.get("total_tokens", 0)),)
estimated_cost_usd = (_safe_estimate_cost(usage, resolved),)
```

Add helper function before the `TokenLedger` class (or at module top after imports):

```python
def _safe_estimate_cost(usage: dict[str, Any], model: str) -> float:
    """Estimate cost, returning 0.0 on unknown model instead of crashing (spec §5.2 I3).

    The ledger is a hot-path side-effect of dispatch — it must never crash
    the pipeline. estimate_cost raises ValueError for unknown models; here
    we catch and log so a misconfigured SHENBI_LLM_MODEL doesn't break dispatch.
    """
    try:
        return estimate_cost(usage, model)
    except ValueError:
        log.warning("ledger_unknown_model_no_pricing", model=model)
        return 0.0
```

**Note**: `test_estimate.py:58` (`test_unknown_model_uses_default_no_crash`) tests `warn_if_over_budget`, NOT `estimate_cost` — it uses its own `MODEL_CONTEXT_LIMITS.get()` fallback and is unaffected by this change.

- [ ] **Step 6: Run all pricing tests to verify**

Run: `pytest tests/ -v -k "pricing or cost or estimate or ledger" -x`
Expected: All PASS (old fallback test deleted; new fail-loud test passes; ledger guard works; existing callers work with known model)

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/cost/pricing.py src/shenbi/cost/ledger.py tests/unit/test_pricing_fail_loud.py tests/unit/cost/test_pricing.py
git commit -m "fix(pricing): fail-loud on unknown model + guard ledger hot-path

Spec §5.2 I3: estimate_cost silently fell back to flash pricing for
unknown models. Now raises ValueError. Ledger._safe_estimate_cost wraps
the call so a misconfigured SHENBI_LLM_MODEL doesn't crash dispatch.
Prepares for per-skill model routing (spec §2.4)."
```

---

## Self-Review

**1. Spec coverage:**
- §2.9 (finish_reason=length) → T1 (capture) + T2 (cap-raise) ✓
- §2.1 (temperature: score + discriminative) → T4 ✓
- §2.2 (drafting max_tokens) → T3 ✓
- §2.5 (pro→flash drift) → T5 ✓
- §2.8 (jitter) → T6 ✓
- §2.4 (pricing guard) → T7 (stretch) ✓
- §2.1 evaluative queue → deferred to P1 pilot (needs live API) ✓
- §2.1 aggregator queue → deferred to plan-stage ✓
- §2.3 (top_p/penalty) → P2, not in this plan (low ROI, needs A/B round) ✓
- §2.6/2.7 (incremental retry) → P1, deferred (prompt-content layer, needs Cluster C decision) ✓
- §2.10 (SharedAuditContext) → explicit non-defect (§5.4) ✓

**2. Placeholder scan:** No TBD/TODO/"add appropriate" found. All steps have concrete code.

**3. Type consistency:**
- `_call_llm_streaming` returns `tuple[str, str | None, Any, str | None]` consistently in T1 def, T1 `_call_llm_streaming_with_retry` passthrough, T1 `_dispatch_via_api` unpacking, T2 mock returns ✓
- `DispatchResult(success, returncode, stdout, stderr)` used consistently ✓
- `_MODEL_OUTPUT_CEILING` defined in T2 step 3, referenced in T2 tests ✓
