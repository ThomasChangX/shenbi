# Pipeline Cost and Token Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture `response.usage` token counts on every API dispatch, persist them to a JSONL ledger, estimate USD cost against the actual configured model, warn on pre-flight context overflow, and expose a `shenbi-cost` report CLI.

**Architecture:** Five layers. (1) `dispatch_helper._dispatch_via_api` reads `response.usage` (free data the API already returns) and records it. (2) A new `src/shenbi/cost/ledger.py` appends one JSONL record per call and summarizes by skill/chapter/total. (3) `src/shenbi/cost/pricing.py` maps model name → per-million input/output rates and computes cost; the model is read from the same env var (`SHENBI_LLM_MODEL`, default `deepseek-v4-pro`) the dispatch path uses, so pricing matches what actually ran. (4) A pre-flight token estimator warns when an assembled prompt exceeds 80% of the model context limit. (5) A `shenbi-cost` console script prints the per-skill/per-chapter/total report. No `cost/` package exists yet — it is created here.

**Tech Stack:** Python 3.11+, pathlib, pydantic/dataclasses, structlog, pytest, OpenAI SDK (read-only)

## Global Constraints

- The pricing module MUST price against the model that actually ran. The dispatch path resolves the model as `os.environ.get("SHENBI_LLM_MODEL", "deepseek-v4-pro")` (confirmed in `src/shenbi/pipeline/dispatch_helper.py` constants `_ENV_LLM_MODEL`/`_DEFAULT_MODEL`). Do NOT hardcode gpt-4o pricing — the default model is `deepseek-v4-pro`. Record the resolved model name in each ledger record so pricing is unambiguous (spec §3.1, §3.3).
- Token usage is captured ONLY on the API path (`_dispatch_via_api`). The IDE-CLI path (`_dispatch_via_ide`) and legacy subprocess path do not return `response.usage`; they record nothing (or a `None`/skipped record), and the report must tolerate missing records.
- The ledger is append-only JSONL at `project_dir/cost/token-ledger.jsonl` (spec §3.2). Each record is self-contained so partial writes never corrupt aggregation.
- Token estimation is a rough heuristic (~4 chars/token English, ~1.5 chars/token CJK); it is a warning signal, not a hard gate (spec §3.4).
- `just check` must pass fully after each task. New console script registered in `pyproject.toml [project.scripts]`.

---

### Task 1: Pricing module keyed to the actual configured model

**Files:**
- Create: `src/shenbi/cost/__init__.py`
- Create: `src/shenbi/cost/pricing.py`
- Test: `tests/unit/cost/test_pricing.py`

**Interfaces:**
- Consumes: nothing (pure rates table + arithmetic)
- Produces: `PRICING: dict[str, dict[str, float]]` (USD per 1M tokens), `DEFAULT_PRICING_MODEL = "deepseek-v4-pro"`, `estimate_cost(usage: dict, model: str | None = None) -> float`, `resolve_model(model: str | None = None) -> str`. Later tasks import `estimate_cost` and `resolve_model`.

**Context:** The spec's snippet hardcodes `gpt-4o`, but the repo's default model is `deepseek-v4-pro`. This task establishes the correct default and makes the model explicit. `resolve_model` mirrors the dispatch path's resolution so the same env var drives both dispatch and pricing. Rates are placeholder values structured so they can be updated when real 2026-07 rates are confirmed; the test pins the structure and the default-model wiring, not the exact USD.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cost/test_pricing.py
"""Tests for the pricing module (spec §3.3)."""
from __future__ import annotations

import pytest

from shenbi.cost.pricing import (
    DEFAULT_PRICING_MODEL,
    PRICING,
    estimate_cost,
    resolve_model,
)


class TestPricingTable:
    def test_default_model_is_deepseek_v4_pro(self):
        # The repo default model is deepseek-v4-pro (dispatch_helper._DEFAULT_MODEL),
        # NOT gpt-4o. Pricing must default to the model that actually runs.
        assert DEFAULT_PRICING_MODEL == "deepseek-v4-pro"

    def test_pricing_has_default_model(self):
        assert DEFAULT_PRICING_MODEL in PRICING

    def test_each_entry_has_input_and_output_rates(self):
        for model, rates in PRICING.items():
            assert "input" in rates, f"{model} missing input rate"
            assert "output" in rates, f"{model} missing output rate"
            assert rates["input"] >= 0
            assert rates["output"] >= 0


class TestResolveModel:
    def test_explicit_model_wins(self, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_MODEL", "gpt-4o")
        assert resolve_model("deepseek-v4-pro") == "deepseek-v4-pro"

    def test_env_used_when_none(self, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_MODEL", "some-other-model")
        assert resolve_model(None) == "some-other-model"

    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("SHENBI_LLM_MODEL", raising=False)
        assert resolve_model(None) == DEFAULT_PRICING_MODEL


class TestEstimateCost:
    def test_zero_tokens_zero_cost(self):
        assert estimate_cost({"prompt_tokens": 0, "completion_tokens": 0}) == 0.0

    def test_known_model_uses_its_rates(self, monkeypatch):
        monkeypatch.delenv("SHENBI_LLM_MODEL", raising=False)
        rates = PRICING[DEFAULT_PRICING_MODEL]
        usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
        expected = rates["input"] * usage["prompt_tokens"] + rates["output"] * usage["completion_tokens"]
        assert estimate_cost(usage) == pytest.approx(expected)

    def test_unknown_model_falls_back_to_default(self):
        # An unknown model must not crash; it prices against the default.
        usage = {"prompt_tokens": 10, "completion_tokens": 10}
        # Should not raise:
        cost = estimate_cost(usage, model="brand-new-model-x")
        assert cost >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_pricing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.cost'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/cost/__init__.py
"""Pipeline cost + token accounting (spec 16)."""
```

```python
# src/shenbi/cost/pricing.py
"""USD pricing per 1M tokens, keyed to the model that actually ran (spec §3.3).

The dispatch path resolves the model as
``os.environ.get("SHENBI_LLM_MODEL", "deepseek-v4-pro")`` — see
``shenbi.pipeline.dispatch_helper`` constants ``_ENV_LLM_MODEL`` /
``_DEFAULT_MODEL``. Pricing MUST use that same default so cost reflects what
ran; do NOT hardcode gpt-4o here.
"""
from __future__ import annotations

import os
from typing import Any

# The model the dispatch path defaults to (mirrors dispatch_helper._DEFAULT_MODEL).
DEFAULT_PRICING_MODEL = "deepseek-v4-pro"

#: USD per 1,000,000 tokens. Update rates when confirmed for the deployment.
#: Unknown models fall back to the default entry (never crash on cost).
PRICING: dict[str, dict[str, float]] = {
    "deepseek-v4-pro": {"input": 1.10 / 1_000_000, "output": 4.40 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
}

# Env var name — must match shenbi.pipeline.dispatch_helper._ENV_LLM_MODEL.
_ENV_LLM_MODEL = "SHENBI_LLM_MODEL"


def resolve_model(model: str | None = None) -> str:
    """Resolve the model to price: explicit arg > env var > default.

    Mirrors the dispatch path's resolution so pricing matches the run.
    """
    if model is not None:
        return model
    return os.environ.get(_ENV_LLM_MODEL, DEFAULT_PRICING_MODEL)


def estimate_cost(usage: dict[str, Any], model: str | None = None) -> float:
    """Estimate USD cost for a usage dict.

    Args:
        usage: dict with 'prompt_tokens' and 'completion_tokens' (int).
        model: explicit model name; None resolves from env/default.

    Unknown models fall back to the DEFAULT_PRICING_MODEL entry.
    """
    resolved = resolve_model(model)
    rates = PRICING.get(resolved, PRICING[DEFAULT_PRICING_MODEL])
    input_cost = int(usage.get("prompt_tokens", 0)) * rates["input"]
    output_cost = int(usage.get("completion_tokens", 0)) * rates["output"]
    return input_cost + output_cost
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/test_pricing.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/__init__.py src/shenbi/cost/pricing.py tests/unit/cost/test_pricing.py
git commit -m "feat(cost): add pricing module keyed to actual configured model

Spec 16 §3.3. Default model is deepseek-v4-pro (mirrors dispatch_helper),
NOT gpt-4o. estimate_cost falls back to default for unknown models."
```

---

### Task 2: TokenLedger JSONL persistence + summarization

**Files:**
- Create: `src/shenbi/cost/ledger.py`
- Test: `tests/unit/cost/test_ledger.py`

**Interfaces:**
- Consumes: `estimate_cost`, `resolve_model` from `shenbi.cost.pricing`
- Produces: `TokenUsageRecord` (dataclass), `TokenLedger(project_dir)` with `.record(skill, chapter, usage, model=None)`, `.summarize() -> dict`, `.iter_records() -> Iterator[TokenUsageRecord]`. Task 3 (dispatch capture) and Task 5 (report CLI) consume these.

**Context:** Spec §3.2. JSONL is append-only so concurrent/partial writes never corrupt aggregation (each record is a full line). `summarize` aggregates by skill, by chapter, and total — and exposes average per chapter. The ledger path is `project_dir/cost/token-ledger.jsonl`. The record includes the resolved model so a run that mixed models can be priced accurately.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cost/test_ledger.py
"""Tests for the TokenLedger JSONL persistence (spec §3.2)."""
from __future__ import annotations

import json
from pathlib import Path

from shenbi.cost.ledger import TokenLedger, TokenUsageRecord


class TestRecord:
    def test_record_appends_one_jsonl_line(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record(
            skill="shenbi-chapter-drafting",
            chapter=1,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            model="deepseek-v4-pro",
        )
        lines = led.ledger_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["skill"] == "shenbi-chapter-drafting"
        assert rec["chapter"] == 1
        assert rec["prompt_tokens"] == 100
        assert rec["completion_tokens"] == 50
        assert rec["total_tokens"] == 150
        assert "estimated_cost_usd" in rec
        assert "model" in rec
        assert "timestamp" in rec

    def test_multiple_records_append(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        for ch in range(3):
            led.record("s", ch, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
        assert len(led.ledger_path.read_text().splitlines()) == 3


class TestSummarize:
    def test_summarize_aggregates_by_skill_and_chapter(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record("drafting", 1, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        led.record("drafting", 2, {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300})
        led.record("review", 1, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50})

        s = led.summarize()
        assert s["total"]["prompt_tokens"] == 330
        assert s["total"]["completion_tokens"] == 170
        assert s["total"]["total_tokens"] == 500
        assert s["total"]["calls"] == 3
        # by skill
        assert set(s["by_skill"]) == {"drafting", "review"}
        assert s["by_skill"]["drafting"]["total_tokens"] == 450
        # by chapter
        assert set(s["by_chapter"]) == {"1", "2"}
        assert s["by_chapter"]["1"]["total_tokens"] == 200  # 150 + 50

    def test_summarize_empty_ledger(self, tmp_path: Path):
        s = TokenLedger(tmp_path).summarize()
        assert s["total"]["calls"] == 0
        assert s["total"]["total_tokens"] == 0
        assert s["by_skill"] == {}


class TestIterRecords:
    def test_iter_records_tolerates_blank_line(self, tmp_path: Path):
        led = TokenLedger(tmp_path)
        led.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        # append a blank/corrupt line to simulate partial write
        with led.ledger_path.open("a", encoding="utf-8") as f:
            f.write("\n")
        records = list(led.iter_records())
        assert len(records) == 1
        assert isinstance(records[0], TokenUsageRecord)
        assert records[0].skill == "s"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.cost.ledger'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/cost/ledger.py
"""Append-only JSONL token usage ledger (spec §3.2).

Each API dispatch appends one self-contained record. Aggregation reads all
lines; a partial/corrupt line is skipped, never crashing the report.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from shenbi.cost.pricing import estimate_cost, resolve_model
from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class TokenUsageRecord:
    timestamp: str
    skill: str
    chapter: int
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class TokenLedger:
    """Persistent append-only token usage ledger."""

    def __init__(self, project_dir: Path | str) -> None:
        self.project_dir = Path(project_dir)
        self.ledger_path = self.project_dir / "cost" / "token-ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def record(
        self,
        skill: str,
        chapter: int,
        usage: dict[str, Any],
        model: str | None = None,
    ) -> TokenUsageRecord:
        """Append a usage record. Returns the record written."""
        resolved = resolve_model(model)
        rec = TokenUsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            skill=skill,
            chapter=chapter,
            model=resolved,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            estimated_cost_usd=estimate_cost(usage, resolved),
        )
        with self._write_lock:
            with self.ledger_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def iter_records(self) -> Iterator[TokenUsageRecord]:
        """Yield records, skipping blank/corrupt lines."""
        if not self.ledger_path.exists():
            return
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                log.warning("ledger_skipped_corrupt_line", line_preview=line[:80])
                continue
            try:
                yield TokenUsageRecord(**data)
            except TypeError:
                log.warning("ledger_skipped_malformed_record", line_preview=line[:80])
                continue

    def summarize(self) -> dict[str, Any]:
        """Aggregate token usage by skill, by chapter, and total."""
        by_skill: dict[str, dict[str, int | float]] = {}
        by_chapter: dict[str, dict[str, int | float]] = {}
        totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "estimated_cost_usd": 0.0,
        }

        def _bump(bucket: dict, key: str, rec: TokenUsageRecord) -> None:
            entry = bucket.setdefault(
                key,
                {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "calls": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            entry["prompt_tokens"] += rec.prompt_tokens
            entry["completion_tokens"] += rec.completion_tokens
            entry["total_tokens"] += rec.total_tokens
            entry["calls"] += 1
            entry["estimated_cost_usd"] += rec.estimated_cost_usd

        for rec in self.iter_records():
            _bump(by_skill, rec.skill, rec)
            _bump(by_chapter, str(rec.chapter), rec)
            totals["prompt_tokens"] += rec.prompt_tokens
            totals["completion_tokens"] += rec.completion_tokens
            totals["total_tokens"] += rec.total_tokens
            totals["calls"] += 1
            totals["estimated_cost_usd"] += rec.estimated_cost_usd

        return {"total": totals, "by_skill": by_skill, "by_chapter": by_chapter}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/test_ledger.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/ledger.py tests/unit/cost/test_ledger.py
git commit -m "feat(cost): add append-only JSONL TokenLedger with summarize()

Spec 16 §3.2. One record per dispatch at cost/token-ledger.jsonl. summarize()
aggregates by skill/chapter/total; corrupt lines skipped not fatal."
```

---

### Task 3: Capture response.usage in _dispatch_via_api

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:431-459` (after the API response, capture usage + record to ledger)
- Test: `tests/unit/pipeline/test_dispatch_usage_capture.py`

**Interfaces:**
- Consumes: `TokenLedger` from `shenbi.cost.ledger`, `extract_chapter` (already used in this function)
- Produces: every successful API dispatch appends a ledger record with prompt/completion/total tokens + resolved model. A `usage` summary is also emitted via structlog (`llm_token_usage`).

**Context:** Today `_dispatch_via_api` reads `response.choices[0].message.content` but discards `response.usage` (spec §2.1). The capture must be defensive: some OpenAI-compatible endpoints omit `usage`; guard with `getattr`. The model is already resolved locally as `model = os.environ.get(_ENV_LLM_MODEL, _DEFAULT_MODEL)` (line 429) — reuse that variable for the ledger record. `extract_chapter(prompt)` is already called at the top of the function; reuse the local `chapter`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_dispatch_usage_capture.py
"""Tests that _dispatch_via_api records response.usage to the ledger (spec §3.1)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _fake_response(content: str, usage=None):
    """Build an object shaped like the OpenAI ChatCompletion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=usage,
    )


class TestUsageCapture:
    def test_usage_recorded_on_success(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-pro")

        usage = SimpleNamespace(prompt_tokens=111, completion_tokens=222, total_tokens=333)
        # NOTE: _write_parsed_outputs expects "### FILE: <path>" markers
        # (see dispatch_helper._parse_file_outputs).
        fake_resp = _fake_response(
            "### FILE: chapters/chapter-1.md\nbody\n", usage=usage
        )

        with patch("shenbi.pipeline.dispatch_helper.OpenAI") as mock_openai, \
                patch(
                    "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                    return_value=("sys", "user", ["chapters/chapter-1.md"]),
                ):
            mock_openai.return_value.chat.completions.create.return_value = fake_resp
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")

        ledger = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8")
        rec = json.loads(ledger.strip().splitlines()[-1])
        assert rec["skill"] == "shenbi-chapter-drafting"
        assert rec["prompt_tokens"] == 111
        assert rec["completion_tokens"] == 222
        assert rec["total_tokens"] == 333
        assert rec["model"] == "deepseek-v4-pro"

    def test_missing_usage_does_not_crash(self, tmp_path: Path, monkeypatch):
        """An endpoint that omits response.usage must not break dispatch."""
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        fake_resp = _fake_response(
            "### FILE: chapters/chapter-1.md\nbody\n", usage=None
        )
        with patch("shenbi.pipeline.dispatch_helper.OpenAI") as mock_openai, \
                patch(
                    "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                    return_value=("sys", "user", ["chapters/chapter-1.md"]),
                ):
            mock_openai.return_value.chat.completions.create.return_value = fake_resp
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            result = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
            assert result.success  # dispatch still succeeds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_usage_capture.py -v`
Expected: FAIL (no ledger file created — usage discarded).

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/pipeline/dispatch_helper.py`, after the `output_text = response.choices[0].message.content or ""` line (around line 446) and before the `_write_parsed_outputs` call, insert the usage capture. The existing block is:

```python
    output_text = response.choices[0].message.content or ""
    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)

    written = _write_parsed_outputs(
        output_text, output_paths, project_dir, create_truth_templates=True
    )
```

Change it to:

```python
    output_text = response.choices[0].message.content or ""
    log.info("api_dispatch_complete", skill=skill, output_length=len(output_text), model=model)

    # NEW (spec §3.1): capture response.usage — free data the API already
    # returns — and persist to the cost ledger. Defensive: some OpenAI-
    # compatible endpoints omit usage.
    usage_obj = getattr(response, "usage", None)
    if usage_obj is not None:
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) or 0,
        }
        log.info(
            "llm_token_usage",
            skill=skill,
            chapter=chapter,
            model=model,
            **usage,
        )
        try:
            from shenbi.cost.ledger import TokenLedger

            TokenLedger(project_dir).record(skill, chapter or 0, usage, model=model)
        except Exception as exc:
            # Cost accounting must NEVER break a dispatch.
            log.warning("ledger_record_failed", skill=skill, error=str(exc))

    written = _write_parsed_outputs(
        output_text, output_paths, project_dir,
        create_truth_templates=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_usage_capture.py tests/unit/pipeline/test_dispatch_helper.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_usage_capture.py
git commit -m "feat(dispatch): capture response.usage to token ledger

Spec 16 §3.1. _dispatch_via_api records prompt/completion/total tokens +
resolved model on every successful API call. Defensive against endpoints that
omit usage; cost accounting never breaks dispatch."
```

---

### Task 4: Pre-flight prompt token estimate + overflow warning

**Files:**
- Create: `src/shenbi/cost/estimate.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (call estimator before dispatch in `_dispatch_via_api`)
- Test: `tests/unit/cost/test_estimate.py`

**Interfaces:**
- Consumes: the assembled `system_prompt`/`user_prompt` strings
- Produces: `estimate_prompt_tokens(text: str) -> int`, `MODEL_CONTEXT_LIMITS: dict[str, int]`, `CONTEXT_WARN_FRACTION = 0.8`, `warn_if_over_budget(prompt: str, model: str, log) -> bool`. `_dispatch_via_api` calls `warn_if_over_budget` before the API call.

**Context:** Spec §3.4. The estimate is a rough heuristic (4 chars/token English, 1.5 chars/token CJK). This is a warning, not a gate — the function returns whether it warned. Context limits are per-model; unknown models fall back to a conservative default.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cost/test_estimate.py
"""Tests for the pre-flight prompt token estimator (spec §3.4)."""
from __future__ import annotations

import logging

from shenbi.cost.estimate import (
    CONTEXT_WARN_FRACTION,
    MODEL_CONTEXT_LIMITS,
    estimate_prompt_tokens,
    warn_if_over_budget,
)


class TestEstimate:
    def test_english_approx_4_chars_per_token(self):
        # 400 chars of ASCII -> ~100 tokens
        toks = estimate_prompt_tokens("a" * 400)
        assert 80 <= toks <= 120

    def test_cjk_uses_smaller_ratio(self):
        # CJK chars are denser: ~1.5 chars/token
        cjk = "中" * 150  # ~100 tokens
        toks = estimate_prompt_tokens(cjk)
        assert 80 <= toks <= 120

    def test_mixed(self):
        text = "a" * 200 + "中" * 75
        toks = estimate_prompt_tokens(text)
        assert toks > 0


class TestContextLimits:
    def test_warn_fraction_is_0_8(self):
        assert CONTEXT_WARN_FRACTION == 0.8

    def test_default_model_has_limit(self):
        from shenbi.cost.pricing import DEFAULT_PRICING_MODEL

        assert DEFAULT_PRICING_MODEL in MODEL_CONTEXT_LIMITS


class TestWarnIfOverBudget:
    def test_small_prompt_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            warned = warn_if_over_budget("short", "deepseek-v4-pro", logger=logging.getLogger("t"))
        assert warned is False

    def test_huge_prompt_warns(self):
        limit = MODEL_CONTEXT_LIMITS["deepseek-v4-pro"]
        # Build a string whose estimate exceeds 80% of the limit.
        huge = "a" * (limit * 5)  # way over
        warned = warn_if_over_budget(huge, "deepseek-v4-pro", logger=logging.getLogger("t"))
        assert warned is True

    def test_unknown_model_uses_default_no_crash(self):
        # Must not raise on an unknown model.
        warned = warn_if_over_budget("a" * 10000, "totally-unknown-model", logger=logging.getLogger("t"))
        assert warned in (True, False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_estimate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.cost.estimate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/cost/estimate.py
"""Pre-flight prompt token estimate + context-overflow warning (spec §3.4).

Rough heuristic only — ~4 chars/token for ASCII, ~1.5 chars/token for CJK.
Used to WARN before an assembled prompt risks exceeding the model context
window (expensive API failure). Not a hard gate.
"""
from __future__ import annotations

import logging

# Warn when estimated prompt tokens exceed this fraction of the model limit.
CONTEXT_WARN_FRACTION = 0.8

# Conservative per-model context limits (prompt tokens). Unknown models fall
# back to the default entry.
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "deepseek-v4-pro": 128_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
}
_DEFAULT_CONTEXT_LIMIT = 128_000

# CJK Unified Ideographs range, used to pick the denser char/token ratio.
_CJK_START = 0x4E00
_CJK_END = 0x9FFF


def estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~= 4 chars (ASCII) / 1.5 chars (CJK)."""
    cjk = sum(1 for c in text if _CJK_START <= ord(c) <= _CJK_END)
    other = len(text) - cjk
    return int(cjk / 1.5 + other / 4)


def _limit_for(model: str) -> int:
    return MODEL_CONTEXT_LIMITS.get(model, _DEFAULT_CONTEXT_LIMIT)


def warn_if_over_budget(prompt: str, model: str, logger: logging.Logger | None = None) -> bool:
    """Log a warning if *prompt* exceeds 80% of *model*'s context limit.

    Returns True if a warning was emitted, False otherwise.
    """
    log = logger or logging.getLogger("shenbi.cost.estimate")
    limit = _limit_for(model)
    estimated = estimate_prompt_tokens(prompt)
    threshold = int(limit * CONTEXT_WARN_FRACTION)
    if estimated > threshold:
        log.warning(
            "prompt_approaching_context_limit",
            extra={
                "estimated_tokens": estimated,
                "context_limit": limit,
                "warn_fraction": CONTEXT_WARN_FRACTION,
                "model": model,
            },
        )
        return True
    return False
```

Then call it in `_dispatch_via_api`, right after `model = os.environ.get(...)` and before `client.chat.completions.create(...)`. The existing block around line 431:

```python
    log.info("api_dispatch_start", skill=skill, model=model, chapter=chapter)
    try:
        response = client.chat.completions.create(
```

Insert before the `try:`:

```python
    log.info("api_dispatch_start", skill=skill, model=model, chapter=chapter)

    # Pre-flight: warn if the assembled prompt approaches the context limit.
    from shenbi.cost.estimate import warn_if_over_budget

    warn_if_over_budget(f"{system_prompt}\n\n{user_prompt}", model, logger=log)

    try:
        response = client.chat.completions.create(
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/test_estimate.py tests/unit/pipeline/test_dispatch_usage_capture.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/estimate.py src/shenbi/pipeline/dispatch_helper.py tests/unit/cost/test_estimate.py
git commit -m "feat(cost): pre-flight prompt token estimate + context overflow warning

Spec 16 §3.4. estimate_prompt_tokens (~4 chars/token ASCII, ~1.5 CJK);
_dispatch_via_api warns when assembled prompt > 80% of model limit. Warning
only, not a gate."
```

---

### Task 5: shenbi-cost report CLI

**Files:**
- Create: `src/shenbi/cost/report.py`
- Modify: `pyproject.toml:55-61` (add `shenbi-cost` console script)
- Test: `tests/unit/cost/test_report.py`

**Interfaces:**
- Consumes: `TokenLedger` from `shenbi.cost.ledger`; optional G3 average score from `project_dir` scoring files (if present) for cost-per-quality.
- Produces: `render_report(project_dir) -> str` (markdown), `main(argv) -> int` (CLI entry). Console script `shenbi-cost report <project_dir>`.

**Context:** Spec §3.5. The report prints total cost, per-skill breakdown (cost + % of total), per-chapter average, and cost-per-quality-point when an average G3 score is discoverable. `render_report` is separated from `main` so it is unit-testable without subprocess.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/cost/test_report.py
"""Tests for the cost report CLI (spec §3.5)."""
from __future__ import annotations

from pathlib import Path

from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import main, render_report


def _seed_ledger(tmp_path: Path) -> None:
    led = TokenLedger(tmp_path)
    led.record("drafting", 1, {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500})
    led.record("drafting", 2, {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500})
    led.record("review", 1, {"prompt_tokens": 300, "completion_tokens": 100, "total_tokens": 400})


class TestRenderReport:
    def test_report_has_total_and_breakdown(self, tmp_path: Path):
        _seed_ledger(tmp_path)
        out = render_report(tmp_path)
        assert "Total" in out
        assert "drafting" in out
        assert "review" in out
        # per-skill percentage
        assert "%" in out

    def test_report_on_empty_ledger(self, tmp_path: Path):
        out = render_report(tmp_path)
        assert "no token usage" in out.lower() or "$0" in out or "Total" in out


class TestCli:
    def test_main_returns_zero_on_existing(self, tmp_path: Path, capsys):
        _seed_ledger(tmp_path)
        rc = main(["report", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "drafting" in captured.out

    def test_main_returns_nonzero_on_missing_dir(self, tmp_path: Path):
        rc = main(["report", str(tmp_path / "does-not-exist")])
        assert rc != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.cost.report'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/cost/report.py
"""Cost report CLI (spec §3.5).

Usage: shenbi-cost report <project_dir>
Prints total cost, per-skill breakdown (% of total), per-chapter average, and
cost-per-quality-point when an average G3 score is discoverable.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from shenbi.cost.ledger import TokenLedger


def _try_avg_g3_score(project_dir: Path) -> float | None:
    """Best-effort average G3 score from scoring files; None if unavailable."""
    # Look for a common scoring output; tolerate any layout. This is a
    # best-effort metric — never fail the report over it.
    candidates = list(project_dir.glob("**/*score*.json"))
    scores: list[float] = []
    for c in candidates:
        try:
            import json

            data = json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, (int, float)) and 0 <= v <= 100:
                    scores.append(float(v))
    if not scores:
        return None
    return sum(scores) / len(scores)


def render_report(project_dir: Path | str) -> str:
    """Render the cost report as a markdown string."""
    summary = TokenLedger(project_dir).summarize()
    total = summary["total"]
    by_skill = summary["by_skill"]

    if total["calls"] == 0:
        return "# Cost Report\n\nNo token usage recorded for this project.\n"

    total_cost = total["estimated_cost_usd"]
    lines = [
        "# Cost Report",
        "",
        f"- **Total calls**: {total['calls']}",
        f"- **Total tokens**: {total['total_tokens']:,} "
        f"(prompt {total['prompt_tokens']:,} + completion {total['completion_tokens']:,})",
        f"- **Total cost**: ${total_cost:.4f}",
        "",
        "## Per-skill breakdown",
        "",
        "| Skill | Calls | Tokens | Cost | % of total |",
        "|-------|-------|--------|------|------------|",
    ]
    for skill, agg in sorted(by_skill.items(), key=lambda kv: -kv[1]["estimated_cost_usd"]):
        pct = (agg["estimated_cost_usd"] / total_cost * 100) if total_cost else 0.0
        lines.append(
            f"| {skill} | {agg['calls']} | {agg['total_tokens']:,} | "
            f"${agg['estimated_cost_usd']:.4f} | {pct:.1f}% |"
        )

    by_chapter = summary["by_chapter"]
    if by_chapter:
        ch_costs = [c["estimated_cost_usd"] for c in by_chapter.values()]
        avg = sum(ch_costs) / len(ch_costs)
        lines += ["", f"- **Per-chapter average cost**: ${avg:.4f}"]

    avg_score = _try_avg_g3_score(Path(project_dir))
    if avg_score and avg_score > 0:
        cpq = total_cost / avg_score
        lines.append(
            f"- **Cost per quality point**: ${cpq:.6f} "
            f"(total_cost / avg_g3_score={avg_score:.1f})"
        )

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shenbi-cost", description="Pipeline cost report.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="Print the cost report for a project.")
    p_report.add_argument("project_dir", type=Path)

    args = ap.parse_args(argv)
    if args.cmd == "report":
        if not args.project_dir.is_dir():
            print(f"error: project dir not found: {args.project_dir}", file=sys.stderr)
            return 2
        print(render_report(args.project_dir))
        return 0
    return 2
```

Register the console script in `pyproject.toml`. In the `[project.scripts]` table (after the existing `shenbi-generate-plugins` line), add:

```toml
shenbi-cost = "shenbi.cost.report:main"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/test_report.py -v`
Expected: PASS.

Verify the console script entry resolves: `uv run shenbi-cost --help`
Expected: prints usage (no traceback).

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/report.py pyproject.toml tests/unit/cost/test_report.py
git commit -m "feat(cost): add shenbi-cost report CLI

Spec 16 §3.5. Prints total/per-skill/per-chapter cost + cost-per-quality when
G3 score discoverable. render_report separated from main for unit testing."
```

---

### Task 6: Regression verification

**Files:**
- No new files.

**Interfaces:**
- Consumes: all five prior tasks.

**Context:** Spec §5 verification: every API dispatch records tokens; report aggregates per skill/chapter/total; pre-flight warns > 80%; cost-per-quality computed; historical trend visible (per-chapter in the ledger); `just check` passes.

- [ ] **Step 1: Run the cost suite**

Run: `uv run pytest tests/unit/cost/ tests/unit/pipeline/test_dispatch_usage_capture.py -v`
Expected: PASS.

- [ ] **Step 2: Run the full check suite**

Run: `just check`
Expected: PASS (new console script registered, no import cycles).

- [ ] **Step 3: Commit (only if fixes were needed)**

```bash
git add -A
git commit -m "test(cost): full regression green for spec 16"
```
