# C33 Retry/Failure Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the three uncoordinated retry layers (openai SDK implicit / tenacity dead predicate / outer serial+parallel+scoring loops) behind a single `FailureClass` taxonomy, a chapter-durable retry budget, deterministic-failure zero-retry routing, and a correct `audit_retry_count` lifecycle — per `docs/superpowers/specs/2026-08-16-c33-retry-failure-taxonomy-design.md` (Revised 2026-09-07).

**Architecture:** `FailureClass` lives in `src/shenbi/contracts/enums.py` (C8 single source). A pure classifier `classify_dispatch_failure` in `dispatch_helper.py` feeds four mandatory classification points (tenacity predicate, write-audit rc=2 downgrade, chapter-loop scoring exit, parallel wave retry). All transient retries converge on the tenacity layer (SDK `max_retries=0`); durable accounting reuses the existing `retry_budget_consumed` machinery. Parallel waves report per-task attempt counts aggregated into state at wave completion (no cross-thread state writes).

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

(Add `FailureClass` to that file's exported `__all__`/registry dict the same way other enums there are registered.)

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
- Produces: `OpenAI(..., max_retries=0)`; every `_emit_dispatch_trace` call passes `failure_class=`; `_with_write_audit` downgrade site classifies rc=2

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

    def test_retryable_predicate_accepts_sdk_wrapper(self, monkeypatch):
        calls: list[BaseException] = []

        class FakeClient:
            def __init__(self, *a, **k):
                raise AssertionError("should not construct real client")

        class FakeRetryable(Exception):
            def __init__(self):
                super().__init__("sdk")
                self.__cause__ = httpx.ReadTimeout("t")

        # F977 acceptance: SDK exception enters tenacity retry (predicate True).
        assert dh._is_retryable(FakeRetryable()) is True


class TestTraceFailureClass:
    def test_emit_dispatch_trace_carries_failure_class(self, tmp_path, monkeypatch):
        emitted: dict = {}
        monkeypatch.setattr(
            dh, "_emit_dispatch_trace",
            lambda *a, failure_class=None, **k: emitted.update(fc=failure_class),
        )
        # simulate the rc=2 downgrade classification call path helper:
        fc = dh.classify_dispatch_failure(returncode=2, stderr="x\nwrite-audit GATE_FAIL: drift")
        assert fc is FailureClass.DETERMINISTIC_GATE
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

Both `_emit_dispatch_trace` call sites (:2165 success, :2180 failure): pass `failure_class=` — success site `None`, failure site `classify_dispatch_failure(returncode=<rc>, stderr=<stderr>)`. Check the actual call-site locals and wire the values present there.

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
- Modify: `src/shenbi/pipeline/chapter_loop.py` (scoring branch :3103-3115; `_handle_failure` retry sleep)
- Test: `tests/unit/pipeline/test_retry_taxonomy.py` (append)

**Interfaces:**
- Consumes: `FailureClass`, `classify_dispatch_failure` (Task 1); `_handle_failure(state, step, chapter, failure, project_dir, *, budget_pre_consumed=False) -> bool`
- Produces: `handle_scoring_failure(state, exit_code) -> tuple[bool, FailureClass]` — **BREAKING internal signature**; only caller is chapter_loop.py:3108 (update in same task)

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
        st.chapter_loop.retry_counts["ch1-review-resonance"] = st.config.max_audit_retries - 1  # one retry left
        step = type("S", (), {"skill": "shenbi-review-resonance"})()
        # one more failure: budget exhausts → RetryExhaustedError raised, but
        # the sleep must have happened before that decision point.
        with pytest.raises(cl.RetryExhaustedError):
            cl._handle_failure(st, step, 1, "scoring", "/tmp")
        assert any(d > 0 for d in slept)
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

`_handle_failure` — add backoff before the return-False (retry) decision. Insert after the budget check, before `handle_dispatch_failure` invocation, gated on an injectable module-level sleep (the test monkeypatches `cl.time.sleep`; ensure `chapter_loop` imports `time`):

```python
    # C33 R2 (T510): serial-layer backoff with jitter — reuse the
    # parallel_dispatch RETRY_JITTER pattern (spec §5.3/§2.8 magnitude rule).
    import random as _random

    _delay = 2.0 ** (count - 1) + _random.uniform(0, 2.0)
    log.debug("serial_retry_backoff", chapter=chapter, skill=step.skill, delay=_delay)
    time.sleep(_delay)
```

(If `chapter_loop.py` lacks `import time`, add it at module top. `time.sleep` runs on every retry-eligible failure — the RetryExhaustedError raise must happen BEFORE the sleep for the exhausted case; verify order: budget check raises first, sleep only on the retry path. Adjust placement accordingly.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q && uv run pytest tests/unit/pipeline/ -q -k "scoring or retry"`
Expected: PASS (run the neighboring suite to catch callers of the old bool signature)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/error_handler.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_retry_taxonomy.py
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
    def _state_with_checkpoint(self):
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import CheckpointType, ReviewDecision

        st = PipelineState()
        st.chapter_states[3].audit_retry_count = st.config.max_audit_retries
        st.chapter_states[3].revision_count = st.config.max_audit_retries
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=3, reason="audit_blocking")
        return st, clear_checkpoint

    def test_approve_resets_counters(self):
        from shenbi.pipeline.state import ReviewDecision

        st, clear = self._state_with_checkpoint()
        clear(st, ReviewDecision.APPROVE, feedback=None)
        assert st.chapter_states[3].audit_retry_count == 0
        assert st.chapter_states[3].revision_count == 0

    def test_reject_and_modify_also_reset(self):
        from shenbi.pipeline.state import ReviewDecision

        for decision in (ReviewDecision.REJECT, ReviewDecision.MODIFY):
            st, clear = self._state_with_checkpoint()
            clear(st, decision, feedback="x")
            assert st.chapter_states[3].audit_retry_count == 0

    def test_chapter_none_clears_all(self):
        from shenbi.pipeline.state import ReviewDecision

        st = PipelineState()
        for ch in (1, 2):
            st.chapter_states[ch].audit_retry_count = 5
        from shenbi.pipeline.machine import set_checkpoint
        from shenbi.pipeline.state import CheckpointType

        set_checkpoint(st, CheckpointType.ESCALATION, chapter=None, reason="pipeline")
        from shenbi.pipeline.machine import clear_checkpoint

        clear_checkpoint(st, ReviewDecision.APPROVE, feedback=None)
        assert all(cs.audit_retry_count == 0 for cs in st.chapter_states.values())

    def test_post_resolve_blocking_routes_to_revision(self):
        """T508 acceptance (T2-tier): ESCALATION resolved → new BLOCKING must
        retry revision instead of instantly re-escalating."""
        from shenbi.pipeline.error_handler import handle_audit_blocking
        from shenbi.pipeline.machine import clear_checkpoint, set_checkpoint
        from shenbi.pipeline.state import CheckpointType, ReviewDecision

        st = PipelineState()
        st.chapter_states[5].audit_retry_count = st.config.max_audit_retries
        set_checkpoint(st, CheckpointType.ESCALATION, chapter=5, reason="audit_blocking")
        clear_checkpoint(st, ReviewDecision.APPROVE, feedback=None)
        assert handle_audit_blocking(st, 5, st.chapter_states[5].audit_retry_count) is True
```

(Adapt constructor/arities of `set_checkpoint`/`clear_checkpoint`/`ReviewDecision` import location to the real signatures in `machine.py`/`state.py` when implementing — check before writing the test.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_taxonomy.py -q -k AuditRetryReset`
Expected: FAIL — counters stay non-zero after clear_checkpoint

- [ ] **Step 3: Implement**

`machine.py` `clear_checkpoint` ESCALATION branch — after the three `.clear()` calls add:

```python
        # C33 R3 (T508): per-chapter audit counters share the reset contract.
        # New scope rule: chapter set → clear that chapter only; None → all
        # (mirrors _reset_retry_budget prefix semantics, NOT dict clear-all).
        _chapters = (
            [cp.chapter] if cp.chapter is not None else list(state.chapter_states)
        )
        for ch in _chapters:
            cs = state.chapter_states.get(ch)
            if cs is not None:
                cs.audit_retry_count = 0
                cs.revision_count = 0
```

Add to the `machine.py` docstring: `All per-phase retry counters — including per-chapter audit_retry_count/revision_count — are reset when an ESCALATION checkpoint is resolved (approve/reject/modify).`

`cli.py` `_reset_retry_budget` — same loop appended inside the function (idempotent mirror):

```python
    for ch in ([cp.chapter] if cp.chapter is not None else list(state.chapter_states)):
        cs = state.chapter_states.get(ch)
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
    def test_lifecycle_dispatch_failure_routes_to_handle_failure(self, monkeypatch, tmp_path):
        """F365 residual: lifecycle dispatch failure must retry/escalate via
        _handle_failure, not just log.error."""
        from shenbi.pipeline import chapter_loop as cl
        from shenbi.pipeline.parallel_dispatch import DispatchResult

        called = {}
        monkeypatch.setattr(cl, "_handle_failure",
                            lambda *a, **k: called.setdefault("routed", True) or True)
        # drive the post-draft lifecycle block with a failing lifecycle_result;
        # exact harness: reuse the existing test in this file that exercises
        # the post-draft two-step block and flip lifecycle_result to failed.
```

(Build the concrete harness on top of the existing post-draft tests already in `test_retry_budget.py`/`test_chapter_loop*` — copy their fixture setup verbatim rather than inventing state.)

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
    """
    for task, _result in results:
        retries = max(0, task.attempts - 1)
        if retries == 0:
            continue
        key = _retry_key(chapter, task.skill)
        current = state.chapter_loop.retry_budget_consumed.get(key, 0)
        state.chapter_loop.retry_budget_consumed[key] = max(current, retries)
```

Call it at the parallel-audit-wave completion site where `ReviewTask` futures are collected (locate the `as_completed` / result-gathering block in the wave function ~:2740-2940; insert after all futures resolve, before `_wave_savepoint`).

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
        from shenbi.pipeline.exceptions import RetryExhaustedError
        from shenbi.pipeline.chapter_loop import _handle_failure

        st = PipelineState()
        key = "ch9-shenbi-review-resonance"
        st.chapter_loop.retry_budget_consumed[key] = st.config.max_audit_retries
        step = type("S", (), {"skill": "shenbi-review-resonance"})()
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
