# C33 Retry/Failure Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the three uncoordinated retry layers (openai SDK implicit / tenacity dead predicate / outer serial+parallel+scoring loops) behind a single `FailureClass` taxonomy, a chapter-durable retry budget, deterministic-failure zero-retry routing, and a correct `audit_retry_count` lifecycle — per `docs/superpowers/specs/archive/2026-08-16-c33-retry-failure-taxonomy-design.md` (Revised 2026-09-07).

**Architecture:** `FailureClass` lives in `src/shenbi/contracts/enums.py` (C8 single source). A pure classifier `classify_dispatch_failure` in `dispatch_helper.py` feeds four mandatory classification points (tenacity predicate, write-audit rc=2 downgrade, chapter-loop scoring exit, parallel wave retry — the last is spec point ④ "audit_layer 派发失败出口" rendered as the wave's per-task failure branch). All transient retries converge on the tenacity layer (SDK `max_retries=0`); durable accounting reuses the existing `retry_budget_consumed` machinery. Parallel waves report per-task attempt counts aggregated into state at wave completion (no cross-thread state writes).

**Tech Stack:** Python 3.11+, tenacity, openai SDK, structlog, pytest. Validation via `just`/`uv run` only.

## Global Constraints

- No `print()` in `src/shenbi/` — structlog only (`log.info/warning/error`).
- All state literals single-sourced: `FailureClass` defined ONLY in `src/shenbi/contracts/enums.py`; `tools/lint_status_strings.py` must stay green.
- Gate checkers pure/idempotent; this plan touches no gate checkers.
- Tests use real code paths; scenario inputs referencing skill outputs must use `tests/fixtures/` real products (G0.9). Mocking the LLM transport/client inside framework unit tests is allowed (that is code under test, not a skill-output fixture).
- Conventional commits: `fix:`/`test:`/`docs:` prefixes; pathspec commits only (never `git add -A`).
- All validation commands via `uv run`/`just` (CI-isomorphic). No real `shenbi-dispatch`/`pipeline` invocations for verification (cost/state discipline).
- Backoff tests must inject a fake clock/tenacity wait factory — no real sleeps in CI.

---

### Task 1: `FailureClass` enum + pure classifier + trace field

**Files:**
- Modify: `src/shenbi/contracts/enums.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add classifier near `_is_retryable`, extend `_emit_dispatch_trace` call sites)
- Create: `tests/unit/pipeline/test_retry_taxonomy.py`
- Test: `tests/unit/pipeline/test_retry_taxonomy.py`

**Interfaces:**
- Consumes: `_emit_dispatch_trace(project_dir, skill, chapter, model, finish_reason, estimated, attempt, *, success)` (dispatch_helper.py:1871)
- Produces:
  - `FailureClass` StrEnum members: `TRANSIENT = "transient"`, `DETERMINISTIC_GATE = "deterministic_gate"`, `DETERMINISTIC_CONTENT = "deterministic_content"`
  - `classify_dispatch_failure(exc: BaseException | None = None, returncode: int | None = None, *, stderr: str = "") -> FailureClass` (dispatch_helper.py)
  - `_emit_dispatch_trace(..., failure_class: FailureClass | None = None)` new keyword-only param; trace payload gains `"failure_class"` when not None

- [ ] **Step 1: Write failing tests**

```python
"""C33 R1: FailureClass taxonomy + classification points (spec #47)."""
from __future__ import annotations

import httpx
import pytest

from shenbi.contracts.enums import FailureClass
from shenbi.pipeline.dispatch_helper import classify_dispatch_failure


class TestClassifier:
    def test_httpx_timeout_transient(self):
        assert classify_dispatch_failure(exc=httpx.ConnectTimeout("t")) is FailureClass.TRANSIENT

    def test_httpx_5xx_transient(self):
        req = httpx.Request("POST", "https://api/x")
        resp = httpx.Response(503, request=req)
        exc = httpx.HTTPStatusError("503", request=req, response=resp)
        assert classify_dispatch_failure(exc=exc) is FailureClass.TRANSIENT

    def test_openai_sdk_exc_wrapping_httpx_transient(self):
        # F977 repro: SDK exceptions wrap httpx as __cause__, never subclass it.
        class FakeAPIConnectionError(Exception):
            def __init__(self):
                super().__init__("conn")
                self.__cause__ = httpx.ReadTimeout("read timed out")

        assert classify_dispatch_failure(exc=FakeAPIConnectionError()) is FailureClass.TRANSIENT

    def test_rc2_write_audit_gate_deterministic(self):
        # F533: rc=2 GATE_FAIL is deterministic — zero retry.
        assert (
            classify_dispatch_failure(returncode=2, stderr="write-audit GATE_FAIL: drift")
            is FailureClass.DETERMINISTIC_GATE
        )

    def test_rc2_plain_is_content(self):
        assert classify_dispatch_failure(returncode=2) is FailureClass.DETERMINISTIC_CONTENT

    def test_plain_exception_defaults_transient(self):
        # unknown → transient-or-escalate rule (M1): transient, budget still guards.
        assert classify_dispatch_failure(exc=RuntimeError("x")) is FailureClass.TRANSIENT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q`
Expected: FAIL — `ImportError: cannot import name 'FailureClass'`

- [ ] **Step 3: Implement**

In `src/shenbi/contracts/enums.py` (after existing enums):

```python
class FailureClass(StrEnum):
    """C33 (spec #47): single failure taxonomy consumed by every retry decision.

    budget-exhausted is a routing OUTCOME (RetryExhaustedError → escalation),
    not a failure signature, so it is deliberately not a member. Unknown
    failures classify as TRANSIENT and remain guarded by the retry budget.
    """

    TRANSIENT = "transient"
    DETERMINISTIC_GATE = "deterministic_gate"
    DETERMINISTIC_CONTENT = "deterministic_content"
```

(Registration: `enums.py` has no `__all__`/registry dict — the status-vocab registration surface is `docs/framework/status-vocab.md` + `tools/lint_status_strings.py`; add `FailureClass` values there per the module's 登记表 convention, and to the contract schema docs as spec R1 requires.)

In `src/shenbi/pipeline/dispatch_helper.py`, above `_is_retryable` (line ~1954):

```python
def classify_dispatch_failure(
    exc: BaseException | None = None,
    returncode: int | None = None,
    *,
    stderr: str = "",
) -> FailureClass:
    """C33 R1: classify a dispatch failure for every retry decision site.

    Four classification points consume this (spec #47 R1):
    ① tenacity predicate (_is_retryable), ② write-audit rc=2 downgrade in
    _with_write_audit, ③ chapter_loop scoring exits, ④ parallel wave retry.
    """
    if returncode == 2 and "write-audit GATE_FAIL" in stderr:
        return FailureClass.DETERMINISTIC_GATE
    if returncode is not None and returncode != 0:
        return FailureClass.DETERMINISTIC_CONTENT
    # Exception face: httpx direct OR openai SDK wrappers (cause chain) → transient.
    if exc is not None and _is_retryable_exception_tree(exc):
        return FailureClass.TRANSIENT
    if exc is not None:
        return FailureClass.TRANSIENT  # unknown → transient-or-escalate (budget guards)
    return FailureClass.TRANSIENT


def _is_retryable_exception_tree(exc: BaseException) -> bool:
    """True if exc or any __cause__/__context__ ancestor is a retryable httpx error.

    F977: openai SDK exceptions never subclass httpx — they wrap it, so the
    old isinstance-only predicate was a dead layer for SDK calls.
    """
    seen: set[int] = set()
    node: BaseException | None = exc
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        if isinstance(node, httpx.TimeoutException):
            return True
        if isinstance(node, httpx.HTTPStatusError):
            return node.response.status_code in _RETRYABLE_STATUSES
        node = node.__cause__ or node.__context__
    return False
```

Rewrite `_is_retryable` body to `return _is_retryable_exception_tree(exception)` (keep the public name — tenacity wiring at :2039 unchanged). Extend `_emit_dispatch_trace` signature with keyword-only `failure_class: FailureClass | None = None` and add `failure_class=failure_class.value if failure_class else None` to its payload dict (only when not None).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/enums.py src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_retry_taxonomy.py
git commit -m "feat: C33 R1 FailureClass taxonomy + classifier + trace failure_class field (spec #47)"
```

---

### Task 2: SDK `max_retries=0` + tenacity consumes FailureClass + trace emission at classification points

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`OpenAI(` constructor :2129; `_with_write_audit` :2615-2632; both `_emit_dispatch_trace` call sites :2165/:2180)
- Test: `tests/unit/pipeline/test_retry_taxonomy.py` (append)

**Interfaces:**
- Consumes: `FailureClass`, `classify_dispatch_failure`, `_is_retryable_exception_tree` (Task 1)
- Produces: `OpenAI(..., max_retries=0)`; `_with_write_audit` downgrade site classifies rc=2; **all four** `_emit_dispatch_trace` call sites pass `failure_class=` (:2165 timeout → `classify_dispatch_failure(exc=<exc>)`, :2180 generic exception → same, :2228 content_filter cap-raise → `FailureClass.DETERMINISTIC_CONTENT` literal, :2355 final success outcome → `None`)

- [ ] **Step 1: Write failing tests** (append to test_retry_taxonomy.py)

```python
import inspect
from shenbi.pipeline import dispatch_helper as dh


class TestSdgMaxRetriesZero:
    def test_openai_client_constructed_with_max_retries_zero(self):
        # T506: SDK implicit max_retries=2 must be eliminated at the single
        # construction point so all transient retries are visible to tenacity.
        src = inspect.getsource(dh)
        assert "max_retries=0" in src

    def test_retryable_predicate_accepts_sdk_wrapper(self):
        class FakeRetryable(Exception):
            def __init__(self):
                super().__init__("sdk")
                self.__cause__ = httpx.ReadTimeout("t")

        # F977 acceptance: SDK exception enters tenacity retry (predicate True).
        assert dh._is_retryable(FakeRetryable()) is True


class TestTraceFailureClass:
    def test_emit_dispatch_trace_writes_failure_class_payload(self, tmp_path):
        """Acceptance #3 (spec R1): classification written to trace under the
        exact field name `failure_class` — REAL payload assertion, not a mock."""
        import json

        (tmp_path / "trace.jsonl").write_text('{"action": "SEED"}\n', encoding="utf-8")
        dh._emit_dispatch_trace(
            tmp_path, "shenbi-review-resonance", 1, "test-model", None, False, 1,
            success=False, failure_class=FailureClass.DETERMINISTIC_CONTENT,
        )
        line = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        assert line["payload"]["failure_class"] == "deterministic_content"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q`
Expected: FAIL at `test_openai_client_constructed_with_max_retries_zero` (AssertionError: "max_retries=0" not in source)

- [ ] **Step 3: Implement**

Constructor (dispatch_helper.py:2129):

```python
    client = OpenAI(
        api_key=os.environ[_ENV_LLM_API_KEY],
        base_url=os.environ.get(_ENV_LLM_BASE_URL, _DEFAULT_BASE_URL),
        max_retries=0,  # C33 R2 (T506): SDK retries invisible to budget — route all transient retries through tenacity.
    )
```

`_with_write_audit` rc=2 branch: after building the downgraded `DispatchResult`, add classification + trace:

```python
                rc = DispatchResult(False, 2, rc.stdout, stderr)
                fc = classify_dispatch_failure(returncode=2, stderr=stderr)
                log.warning("write_audit_gate_fail_classified", skill=skill, failure_class=fc.value)
```

Both `_emit_dispatch_trace` call sites inside the dispatch try/except (:2165 timeout, :2180 generic exception): pass `failure_class=classify_dispatch_failure(exc=<the caught exception>)`. Additionally the other two sites: :2228 (content_filter cap-raise) pass `failure_class=FailureClass.DETERMINISTIC_CONTENT`; :2355 (final outcome, success path) pass `failure_class=None` (default). Check the actual call-site locals and wire the values present there.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_retry_taxonomy.py
git commit -m "feat: C33 R2a SDK max_retries=0 + tenacity FailureClass predicate + trace wiring (spec #47)"
```

---

### Task 3: Scoring exit-2/exit-3 zero-retry + serial backoff with jitter + amplification cap

**Files:**
- Modify: `src/shenbi/pipeline/error_handler.py` (`handle_scoring_failure` :89-101 + module docstring)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (scoring branch :3103-3115; `_handle_failure` retry sleep; module-top `import random`)
- Modify: `tests/unit/pipeline/test_full_flows.py:215-219` (old bool-semantics assertions)
- Modify: `tests/unit/pipeline/test_chapter_loop.py:947-967` (old bool-semantics assertions)
- Test: `tests/unit/pipeline/test_retry_taxonomy.py` (append)

**Interfaces:**
- Consumes: `FailureClass`, `classify_dispatch_failure` (Task 1); `_handle_failure(state, step, chapter, failure, project_dir, *, budget_pre_consumed=False) -> bool`
- Produces: `handle_scoring_failure(state, exit_code) -> tuple[bool, FailureClass]` — **BREAKING internal signature**; production caller = chapter_loop.py:3108, legacy test callers in test_full_flows.py + test_chapter_loop.py updated in this same task (rewrite their assertions to `retry, fc = handle_scoring_failure(...)`; `retry is False`, exit 2 → `FailureClass.DETERMINISTIC_CONTENT`, exit 3 → `FailureClass.DETERMINISTIC_GATE`)

- [ ] **Step 1: Write failing tests** (append)

```python
from shenbi.pipeline.error_handler import handle_scoring_failure
from shenbi.pipeline.state import PipelineState


def _state() -> PipelineState:
    return PipelineState()


class TestScoringDeterministic:
    def test_exit2_classified_content_zero_retry(self):
        retry, fc = handle_scoring_failure(_state(), 2)
        assert retry is False and fc is FailureClass.DETERMINISTIC_CONTENT

    def test_exit3_classified_gate_zero_retry(self):
        retry, fc = handle_scoring_failure(_state(), 3)
        assert retry is False and fc is FailureClass.DETERMINISTIC_GATE

    def test_other_exit_no_recovery(self):
        retry, fc = handle_scoring_failure(_state(), 7)
        assert retry is False and fc is FailureClass.DETERMINISTIC_CONTENT


class TestAmplificationCap:
    def test_persistent_5xx_total_attempts_bounded(self):
        """T506: outer(3) × tenacity(3) × SDK(3) = 27 worst case must collapse
        to tenacity-only 3 attempts now that SDK retries are 0 and the outer
        scoring/serial layers zero-retry deterministic failures."""
        # tenacity stop_after_attempt(3) is the only retry surface for
        # persistent transient failures; assert via the actual decorator state.
        import tenacity
        retry_state = tenacity.RetryCallState(
            fn=dh._call_llm_streaming_with_retry, args=(), kwargs={})
        retry_state.attempt_number = 3
        # stop_after_attempt(3): should_stop True at attempt 3
        assert dh._call_llm_streaming_with_retry.retry.stop(retry_state) is True


class TestSerialBackoff:
    def test_handle_failure_sleeps_with_jitter_before_retry(self, monkeypatch):
        """T510: serial layer retries had zero backoff; R2 reuses the
        RETRY_JITTER pattern (parallel_dispatch) with an injected clock."""
        from shenbi.pipeline import chapter_loop as cl

        slept: list[float] = []
        monkeypatch.setattr(cl.time, "sleep", lambda s: slept.append(s))
        st = PipelineState()
        key = "ch1-shenbi-review-resonance"
        st.chapter_loop.retry_counts[key] = 0
        st.chapter_loop.retry_budget_consumed[key] = 0  # budget NOT exhausted → retry path
        step = type("S", (), {"skill": "shenbi-review-resonance", "step_num": 3})()
        # retry path: _handle_failure returns False (retry) and must have slept.
        retried = cl._handle_failure(st, step, 1, "scoring", "/tmp")
        assert retried is False
        assert any(d > 0 for d in slept)

    def test_budget_exhausted_raises_before_sleep(self, monkeypatch):
        """Exhausted budget raises RetryExhaustedError without backoff sleep."""
        from shenbi.pipeline import chapter_loop as cl

        slept: list[float] = []
        monkeypatch.setattr(cl.time, "sleep", lambda s: slept.append(s))
        st = PipelineState()
        key = "ch9-shenbi-review-resonance"
        st.chapter_loop.retry_budget_consumed[key] = st.config.max_audit_retries
        step = type("S", (), {"skill": "shenbi-review-resonance", "step_num": 3})()
        with pytest.raises(cl.RetryExhaustedError):
            cl._handle_failure(st, step, 9, "scoring", "/tmp")
        assert slept == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q`
Expected: FAIL — `handle_scoring_failure` returns bool not tuple; no sleep in `_handle_failure`

- [ ] **Step 3: Implement**

`error_handler.py` — replace `handle_scoring_failure`:

```python
def handle_scoring_failure(
    state: PipelineState, exit_code: int
) -> tuple[bool, FailureClass]:
    """Classify a scoring failure for retry routing (spec S11 + C33 spec #47 R2).

    Exit code 2 (validation failure) → deterministic_content: zero retry,
    route straight to _handle_failure/escalation.
    Exit code 3 (marker file missing) → deterministic_gate: structural
    absence is not retryable — zero retry.
    Returns (retry, failure_class); retry is now False for both (C33).
    """
    if exit_code == 2:
        log.warning("scoring_failure_classified", exit_code=exit_code, failure_class="deterministic_content")
        return False, FailureClass.DETERMINISTIC_CONTENT
    if exit_code == 3:
        log.warning("scoring_failure_classified", exit_code=exit_code, failure_class="deterministic_gate")
        return False, FailureClass.DETERMINISTIC_GATE
    log.error("scoring_unrecoverable", exit_code=exit_code)
    return False, FailureClass.DETERMINISTIC_CONTENT
```

Update module docstring scoring line to: `* scoring failure -- exit 2/3 are deterministic (C33): zero retry, escalate via _handle_failure`. Add `from shenbi.contracts.enums import FailureClass` import.

`chapter_loop.py` scoring branch (:3103-3115) becomes:

```python
    # Scoring failure (review-resonance): C33 — exit 2/3 deterministic, zero retry.
    if not result.success and "review-resonance" in step.skill:
        from shenbi.pipeline.error_handler import handle_scoring_failure

        retry, fc = handle_scoring_failure(state, result.returncode)
        if retry:  # pragma: no cover — no retry path remains; kept for API truth
            log.warning("scoring_failure_retry", chapter=chapter, exit_code=result.returncode)
            return False
        log.warning(
            "scoring_failure_deterministic",
            chapter=chapter,
            exit_code=result.returncode,
            failure_class=fc.value,
        )
        return _handle_failure(state, step, chapter, "scoring", project_dir)
```

`_handle_failure` — add backoff on the retry path only. Insert AFTER the budget check (so `RetryExhaustedError` raises before any sleep) and BEFORE the `handle_dispatch_failure` invocation; use module-top `import random` in chapter_loop.py (it already imports `time` at :34):

```python
    # C33 R2 (T510): serial-layer backoff with jitter — reuse the
    # parallel_dispatch RETRY_JITTER pattern (spec §5.3/§2.8 magnitude rule).
    _delay = 2.0 ** (count - 1) + random.uniform(0, 2.0)
    log.debug("serial_retry_backoff", chapter=chapter, skill=step.skill, delay=_delay)
    time.sleep(_delay)
```

- [ ] **Step 4: Update legacy test callers, then run**

Rewrite the old bool-semantics assertions in `tests/unit/pipeline/test_full_flows.py:215-219` and `tests/unit/pipeline/test_chapter_loop.py:947-967` to the tuple API (`retry, fc = handle_scoring_failure(state, n)`; exit 2 → `(False, FailureClass.DETERMINISTIC_CONTENT)`, exit 3 → `(False, FailureClass.DETERMINISTIC_GATE)`).

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py tests/unit/pipeline/test_full_flows.py tests/unit/pipeline/test_chapter_loop.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/error_handler.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_retry_taxonomy.py tests/unit/pipeline/test_full_flows.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "feat: C33 R2b scoring exit-2/3 zero-retry + serial backoff jitter + amplification cap (spec #47)"
```

---

### Task 4: `audit_retry_count` lifecycle (R3)

**Files:**
- Modify: `src/shenbi/pipeline/machine.py` (`clear_checkpoint` :114-123 + module/class docstring)
- Modify: `src/shenbi/pipeline/cli.py` (`_reset_retry_budget` :560-577)
- Test: `tests/unit/pipeline/test_retry_taxonomy.py` (append)

**Interfaces:**
- Consumes: `CheckpointType.ESCALATION`, `ReviewDecision`, `state.chapter_states: dict[int, ChapterState]` (`ChapterState.audit_retry_count`, `.revision_count`)
- Produces: no new public API — mutation of `clear_checkpoint` (authoritative) and `_reset_retry_budget` (idempotent mirror)

- [ ] **Step 1: Write failing tests** (append)

```python
class TestAuditRetryReset:
    """Real arities (verified): set_checkpoint(state, cp_type, chapter=,
    artifact=, context=, options=); clear_checkpoint(state, decision);
    chapter_states lives at state.chapter_loop.chapter_states, STR-keyed
    (key = str(chapter), convention of add_step_done, state.py:234)."""

    def _state_with_checkpoint(self, chapter: int | None = 3):
        from shenbi.pipeline.machine import set_checkpoint
        from shenbi.pipeline.state import ChapterState, CheckpointType

        st = PipelineState()
        key = str(chapter)
        # chapter_states is a plain dict (NOT defaultdict) — create the entry.
        st.chapter_loop.chapter_states[key] = ChapterState()
        st.chapter_loop.chapter_states[key].audit_retry_count = st.config.max_audit_retries
        st.chapter_loop.chapter_states[key].revision_count = st.config.max_audit_retries
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=chapter, context="audit_blocking")
        return st

    def test_approve_resets_counters(self):
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        st = self._state_with_checkpoint()
        clear_checkpoint(st, ReviewDecision.APPROVE)
        cs = st.chapter_loop.chapter_states["3"]
        assert cs.audit_retry_count == 0 and cs.revision_count == 0

    def test_reject_and_modify_also_reset(self):
        from shenbi.pipeline.machine import clear_checkpoint
        from shenbi.pipeline.state import ReviewDecision

        for decision in (ReviewDecision.REJECT, ReviewDecision.MODIFY):
            st = self._state_with_checkpoint()
            clear_checkpoint(st, decision)
            assert st.chapter_loop.chapter_states["3"].audit_retry_count == 0

    def test_chapter_none_clears_all(self):
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import ChapterState, CheckpointType, ReviewDecision

        st = PipelineState()
        for ch in ("1", "2"):
            st.chapter_loop.chapter_states[ch] = ChapterState()
            st.chapter_loop.chapter_states[ch].audit_retry_count = 5
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=None, context="pipeline")
        clear_checkpoint(st, ReviewDecision.APPROVE)
        assert all(cs.audit_retry_count == 0 for cs in st.chapter_loop.chapter_states.values())

    def test_post_resolve_blocking_routes_to_revision(self):
        """T508 acceptance (T2-tier): ESCALATION resolved → new BLOCKING must
        retry revision instead of instantly re-escalating."""
        from shenbi.pipeline.error_handler import handle_audit_blocking
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import ChapterState, CheckpointType, ReviewDecision

        st = PipelineState()
        st.chapter_loop.chapter_states["5"] = ChapterState()
        st.chapter_loop.chapter_states["5"].audit_retry_count = st.config.max_audit_retries
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=5, context="audit_blocking")
        clear_checkpoint(st, ReviewDecision.APPROVE)
        cs = st.chapter_loop.chapter_states["5"]
        assert handle_audit_blocking(st, 5, cs.audit_retry_count) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q -k AuditRetryReset`
Expected: FAIL — counters stay non-zero after clear_checkpoint

- [ ] **Step 3: Implement**

`machine.py` `clear_checkpoint` ESCALATION branch — after the three `.clear()` calls add (NOTE: `chapter_states` is STR-keyed at `state.chapter_loop.chapter_states`):

```python
        # C33 R3 (T508): per-chapter audit counters share the reset contract.
        # New scope rule: chapter set → clear that chapter only; None → all
        # (mirrors _reset_retry_budget prefix semantics, NOT dict clear-all).
        _keys = (
            [str(cp.chapter)] if cp.chapter is not None
            else list(state.chapter_loop.chapter_states)
        )
        for k in _keys:
            cs = state.chapter_loop.chapter_states.get(k)
            if cs is not None:
                cs.audit_retry_count = 0
                cs.revision_count = 0
```

Add to the `machine.py` docstring: `All per-phase retry counters — including per-chapter audit_retry_count/revision_count — are reset when an ESCALATION checkpoint is resolved (approve/reject/modify).`

`cli.py` `_reset_retry_budget` — same loop appended inside the function (idempotent mirror; same STR-key convention):

```python
    for k in ([str(cp.chapter)] if cp.chapter is not None else list(state.chapter_loop.chapter_states)):
        cs = state.chapter_loop.chapter_states.get(k)
        if cs is not None:
            cs.audit_retry_count = 0
            cs.revision_count = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q && uv run pytest tests/unit/pipeline/ -q -k "checkpoint or escalation"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/machine.py src/shenbi/pipeline/cli.py tests/unit/pipeline/test_retry_taxonomy.py
git commit -m "feat: C33 R3 audit_retry_count lifecycle reset on ESCALATION resolution (spec #47)"
```

---

### Task 5: Parallel-wave budget aggregation + lifecycle/G4 failure routing (R4)

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py` (`ReviewTask` :41-56; `_dispatch_with_retry` :58-129)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (wave completion aggregation site; lifecycle dispatch failure :2937-2944; G4 failure :2946-2957)
- Test: `tests/unit/pipeline/test_retry_budget.py` (extend)

**Interfaces:**
- Consumes: `DispatchResult(success, returncode, stdout, stderr)`; `retry_budget_consumed: dict[str, int]`; `_retry_key(chapter, skill) -> str`; `_handle_failure(...)`; `classify_dispatch_failure`
- Produces: `ReviewTask.attempts: int = 0` (set by `_dispatch_with_retry`); wave aggregator `_charge_wave_retries(state, chapter, results: list[tuple[ReviewTask, DispatchResult]]) -> None` in chapter_loop.py

- [ ] **Step 1: Write failing tests** (extend `tests/unit/pipeline/test_retry_budget.py`)

```python
class TestWaveBudgetAggregation:
    def test_wave_retries_charged_once_after_completion(self, tmp_path):
        """F363: wave worker retries must land in retry_budget_consumed."""
        from shenbi.pipeline.chapter_loop import _charge_wave_retries
        from shenbi.pipeline.parallel_dispatch import DispatchResult, ReviewTask

        st = PipelineState()
        tasks = [
            (ReviewTask(skill="shenbi-review-anti-ai", project_dir=tmp_path, prompt="p",
                        output_path="o"), DispatchResult(False, 1, "", "x")),
        ]
        tasks[0][0].attempts = 3  # 3 attempts → 2 retries consumed
        _charge_wave_retries(st, 1, tasks)
        assert st.chapter_loop.retry_budget_consumed.get("ch1-shenbi-review-anti-ai") == 2

    def test_charge_idempotent_on_replay(self, tmp_path):
        """Crash consistency: re-charging the same wave must not double-count."""
        from shenbi.pipeline.chapter_loop import _charge_wave_retries
        from shenbi.pipeline.parallel_dispatch import DispatchResult, ReviewTask

        st = PipelineState()
        t = ReviewTask(skill="shenbi-review-anti-ai", project_dir=tmp_path, prompt="p",
                       output_path="o")
        t.attempts = 3
        res = DispatchResult(False, 1, "", "x")
        _charge_wave_retries(st, 1, [(t, res)])
        _charge_wave_retries(st, 1, [(t, res)])  # resume replay
        assert st.chapter_loop.retry_budget_consumed.get("ch1-shenbi-review-anti-ai") == 2
```

(Idempotency design: charge uses `max(current, attempts - 1)` not `+=`.)

```python
class TestLifecycleFailureRouting:
    """F365 residual: lifecycle dispatch failure must retry/escalate via
    _handle_failure, not just log.error. Harness copied from
    test_chapter_loop.py::TestConditionalResolveIntegration::
    test_lifecycle_step_dispatches_via_parallel (mock run_parallel_post_draft_steps
    + run_gate_g4, drive run_chapter_step at step_index 6)."""

    def test_lifecycle_dispatch_failure_routes_to_handle_failure(self, tmp_path):
        from unittest.mock import patch

        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.dispatch_helper import DispatchResult
        from shenbi.pipeline.state import PipelineState

        routed = {}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 6
        with (
            patch(
                "shenbi.pipeline.chapter_loop.run_parallel_post_draft_steps",
                return_value=(DispatchResult(False, 1, "", "x"), DispatchResult(True, 0, "{}", "")),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "PASS"}),
            patch(
                "shenbi.pipeline.chapter_loop._handle_failure",
                side_effect=lambda *a, **k: routed.setdefault("called", True) or True,
            ),
        ):
            run_chapter_step(state, tmp_path)
        assert routed.get("called") is True

    def test_g4_failure_routes_to_handle_failure(self, tmp_path):
        from unittest.mock import patch

        from shenbi.pipeline.chapter_loop import run_chapter_step
        from shenbi.pipeline.dispatch_helper import DispatchResult
        from shenbi.pipeline.state import PipelineState

        routed = {}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 6
        with (
            patch(
                "shenbi.pipeline.chapter_loop.run_parallel_post_draft_steps",
                return_value=(DispatchResult(True, 0, "{}", ""), DispatchResult(True, 0, "{}", "")),
            ),
            patch("shenbi.pipeline.chapter_loop.run_gate_g4", return_value={"status": "FAIL"}),
            patch(
                "shenbi.pipeline.chapter_loop._handle_failure",
                side_effect=lambda *a, **k: routed.setdefault("called", True) or True,
            ),
        ):
            run_chapter_step(state, tmp_path)
        assert routed.get("called") is True
```

(These two tests live in `tests/unit/pipeline/test_retry_taxonomy.py`, not test_retry_budget.py — the imports above are self-contained. G0.9 note: mocked `run_parallel_post_draft_steps`/`run_gate_g4` are framework code under test, not skill-output fixtures — allowed per Global Constraints.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_budget.py -q`
Expected: FAIL — no `attempts` attribute / no `_charge_wave_retries`

- [ ] **Step 3: Implement**

`parallel_dispatch.py`: add field to `ReviewTask`:

```python
    #: C33 R4 (F363): attempts used (1 = first try). Set by _dispatch_with_retry;
    #: aggregated into retry_budget_consumed at wave completion (main thread).
    attempts: int = 0
```

In `_dispatch_with_retry`: set `task.attempts = attempt + 1` immediately after entering each loop iteration (before dispatch), so even exception paths record the attempt.

`chapter_loop.py` — add the aggregator:

```python
def _charge_wave_retries(
    state: PipelineState,
    chapter: int,
    results: list[tuple[ReviewTask, DispatchResult]],
) -> None:
    """C33 R4 (F363): charge wave retry consumption into the durable budget.

    Wave-aggregation design (spec #47 R4): workers never touch state (no
    cross-thread writes); the main thread charges once at wave completion.
    Idempotent: max(current, attempts - 1) so crash-resume replay cannot
    double-count; trace failure_class/attempts are the reconciliation source.
    (Locking: write under `state._lock` for convention parity with
    add_step_done even though this is main-thread-only.)
    """
    with state._lock:
        for task, _result in results:
            retries = max(0, task.attempts - 1)
            if retries == 0:
                continue
            key = _retry_key(chapter, task.skill)
            current = state.chapter_loop.retry_budget_consumed.get(key, 0)
            state.chapter_loop.retry_budget_consumed[key] = max(current, retries)
```

Call it at the single combined result-gathering zip (chapter_loop.py ~:2874): `zip(core_wave + core_serial + genre_wave + genre_serial, core_results + genre_results, strict=True)`. There is exactly ONE insertion point — insert `_charge_wave_retries(state, chapter, list(zip(core_wave + core_serial + genre_wave + genre_serial, core_results + genre_results)))` immediately before that zip's consuming loop (or fold the charge into its first iteration). Note: `_wave_savepoint` is a per-task `on_task_complete` callback that runs DURING the wave — the charge goes at the zip-gathering site, not near the savepoint.

Lifecycle dispatch failure (:2937-2944) — replace log-only with routing:

```python
        if not lifecycle_result.success:
            log.error(
                "chapter_dispatch_failed",
                chapter=chapter,
                step=lifecycle_step.step_num,
                skill=lifecycle_step.skill,
            )
            # C33 R4 (F365 residual): route to failure handler — retry budget
            # + escalation, instead of silently continuing with settling only.
            return _handle_failure(state, lifecycle_step, chapter, "dispatch", project_dir)
```

G4 failure (:2946-2957) — same routing per-step:

```python
            if not _gate_passed(g4):
                log.warning(
                    "parallel_post_draft_g4_failed",
                    chapter=chapter,
                    skill=pstep.skill,
                )
                return _handle_failure(
                    state, pstep, chapter, "g4", project_dir, budget_pre_consumed=True
                )
```

(Use `budget_pre_consumed=True` only if the G4 hard-fail pre-charge already ran for this path — check the existing G4 hard-fail pre-charge at :3168-3175 and mirror its convention; if this site does not pre-charge, pass False.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_budget.py tests/unit/pipeline/test_retry_accounting.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/parallel_dispatch.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_retry_budget.py
git commit -m "feat: C33 R4 wave retry budget aggregation + lifecycle/G4 failure routing (spec #47)"
```

---

### Task 6: Full-matrix verification + spec acceptance sweep

**Files:**
- Test: `tests/unit/pipeline/test_retry_taxonomy.py` (final matrix additions)
- Docs: spec deviation log only if reality diverges

**Interfaces:**
- Consumes: everything from Tasks 1-5

- [ ] **Step 1: Complete the spec acceptance matrix** — ensure these exact scenarios exist and pass (add if missing):
  1. F977 repro: SDK exception → tenacity retry (Task 2 ✓)
  2. rc=2 sample zero-retry straight to escalation (Task 1+3 ✓; add explicit chapter-loop-level assertion if only classifier-level exists)
  3. classification written to trace with field name `failure_class` (Task 2 ✓)
  4. persistent-5xx total requests ≤ budget cap (Task 3 TestAmplificationCap ✓; assert the outer layer does not add attempts on deterministic failures)
  5. backoff curve unit test with injected clock (Task 3 ✓)
  6. ESCALATION→each decision→re-BLOCKING routes to revision (Task 4 ✓)
  7. approve-path budget stays at ceiling: new failure escalates without burning retries (I4 assertion — add):

```python
    def test_approve_keeps_budget_escalates_on_next_failure(self):
        from shenbi.exceptions import RetryExhaustedError
        from shenbi.pipeline.chapter_loop import _handle_failure

        st = PipelineState()
        key = "ch9-shenbi-review-resonance"
        st.chapter_loop.retry_budget_consumed[key] = st.config.max_audit_retries
        step = type("S", (), {"skill": "shenbi-review-resonance", "step_num": 3})()
        with pytest.raises(RetryExhaustedError):
            _handle_failure(st, step, 9, "scoring", "/tmp")
```

  8. failed-attempt token accounting face: assert `usage_acc["attempts"]` counts retries (already exists via T410 tests — grep `usage_acc` in tests; reference, don't duplicate)

- [ ] **Step 2: Run the full verification battery**

```bash
uv run pytest tests/unit/pipeline/test_retry_taxonomy.py tests/unit/pipeline/test_retry_budget.py tests/unit/pipeline/test_retry_accounting.py -q
uv run pytest -n auto -m "not last" -q
just check
```
Expected: all green

- [ ] **Step 3: Commit**

```bash
git add tests/unit/pipeline/test_retry_taxonomy.py
git commit -m "test: C33 acceptance matrix completion — approve-path budget assertion (spec #47)"
```

## Self-Review

- **Spec coverage:** R1→Task 1+2 (enum, classifier, 4 classification points, trace field, F977 repro); R2→Task 2+3 (max_retries=0, exit-2/3, backoff, amplification cap, I4 semantics); R3→Task 4 (all three decisions, scope rule, machine.py docstring); R4→Task 5 (wave aggregation F363, lifecycle/G4 routing F365 residual, TokenLedger face); cluster acceptance (test_retry_taxonomy.py full matrix, just check) → Task 6. Genesis/closure explicitly out of scope (deviation I1).
- **Type consistency:** `handle_scoring_failure` tuple change is internal-only (single caller updated in same task); `FailureClass` StrEnum values used as `.value` in log/trace payloads; `_charge_wave_retries` signature fixed in both test and impl.
- **No placeholders:** the two harness-dependent tests (post-draft lifecycle, wave call site) name their concrete reuse source; implementer must locate the exact block by the cited line ranges and existing neighbors.
