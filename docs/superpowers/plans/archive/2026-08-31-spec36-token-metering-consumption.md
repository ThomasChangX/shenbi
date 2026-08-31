# Spec #36 token-metering consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接通 C10 存活面——估记扩区、IDE/legacy 估记行、章循环/闭卷自动 cost 报告、报告面诚实化、重试入账 + dispatch trace 事件。

**Architecture:** 全部改动落在既有单源设施上：`TokenLedger.record` 扩可选字段（带默认值，向后兼容）；估记行复用 `estimate_prompt_tokens`；报告自动化复用 `render_report`；T7 经 usage-accumulator dict 从 `@retry` 装饰的 `_call_llm_streaming` 逃逸到 `_dispatch_via_api` 的异常处理分支；trace 事件经既有 `TraceWriter.append`（payload 自由 dict，不 bump schema_version）。

**Tech Stack:** Python 3.11+，dataclasses，tenacity，structlog，pytest（`uv run pytest`）。

## Global Constraints

- Ledger 兼容契约（spec v3）：`TokenUsageRecord` 新字段一律带默认值（`estimated: bool = False`、`attempt: int = 1`、`pricing_status: str = "ok"`）——无默认值字段会使存量行被 `iter_records` 的 TypeError-skip 静默销毁。
- 所有 ledger/report/trace 写入 fail-safe：异常 WARN+跳过，绝不 raise 进派发流（既有 `_record_usage_to_ledger` 同语义）。
- `src/shenbi/` 禁 `print()`（structlog）；pathlib；conventional commits。
- 测试全部 fixtures/fake-client 驱动，禁真实 dispatch（G0.9/成本纪律）。
- 验证命令走 `uv run pytest ...`（与 CI `uv run --frozen` 同构）。
- 本 plan 全部 task 属 infra（dispatch_helper/chapter_loop/cost/trace）——协调者亲自实现，TDD。

---

### Task 1: T6′a — estimate 扩区 + 保守回退（F523）

**Files:**
- Modify: `src/shenbi/cost/estimate.py:21-32`
- Test: `tests/unit/cost/test_estimate.py`（新建或追加；先查现有 `tests/unit/cost/` 下 estimate 测试文件，存在则追加）

**Interfaces:**
- Produces: `estimate_prompt_tokens(text: str) -> int`（签名不变，行为扩区）；模块级 `_warned_unknown_model: bool` + `reset_unknown_model_warning()`（测试 reset 钩子）；`_DEFAULT_CONTEXT_LIMIT` 改 `131_072`。

- [ ] **Step 1: Write the failing test**

```python
from shenbi.cost import estimate


def test_ext_a_counts_as_cjk():
    # U+3491 (扩展 A 区) — 旧实现按 ASCII 4 chars/token 计
    ext_a = "".join(chr(c) for c in range(0x3400, 0x3400 + 30))
    fullwidth = "ＡＢＣ１２３！"  # 全角 FF00-FFEF
    new = estimate.estimate_prompt_tokens(ext_a + fullwidth)
    # 旧实现：全部按 other/4；新实现：全部按 cjk/1.5 → 严格更大
    old_style = int(0 / 1.5 + len(ext_a + fullwidth) / 4)
    assert new > old_style


def test_compat_ideographs_count_as_cjk():
    compat = "".join(chr(c) for c in range(0xF900, 0xF900 + 10))
    assert estimate.estimate_prompt_tokens(compat) == int(10 / 1.5)


def test_unknown_model_conservative_limit():
    assert estimate._limit_for("totally-unknown-model") == 131_072


def test_unknown_model_warns_once(caplog):
    estimate.reset_unknown_model_warning()
    import logging
    logger = logging.getLogger("shenbi.cost.estimate")
    with caplog.at_level(logging.WARNING, logger="shenbi.cost.estimate"):
        estimate.warn_if_over_budget("x" * 600_000, "totally-unknown-model", logger=logger)
        estimate.warn_if_over_budget("x" * 600_000, "totally-unknown-model", logger=logger)
    once = [r for r in caplog.records if r.name == "shenbi.cost.estimate"
            and "unknown model" in str(r.msg)]
    assert len(once) == 1
    estimate.reset_unknown_model_warning()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_estimate.py -v`
Expected: FAIL（ext-A/全角按 ASCII 计；`reset_unknown_model_warning` 不存在）

- [ ] **Step 3: Write minimal implementation**

`src/shenbi/cost/estimate.py` 改动（替换 :21-32 区域）：

```python
# CJK ranges (F523): Basic + Ext-A + compatibility ideographs + fullwidth forms.
_CJK_RANGES = (
    (0x3400, 0x4DBF),  # CJK Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0xFF00, 0xFFEF),  # Fullwidth Forms + halfwidth/fullwidth punctuation
)

# F523: unknown models must NOT fall back optimistically to the largest known
# limit — 1M was the flagship limit, silently disabling the overflow warning.
_DEFAULT_CONTEXT_LIMIT = 131_072

_warned_unknown_model = False


def reset_unknown_model_warning() -> None:
    """Test hook: re-arm the one-shot unknown-model fallback warning."""
    global _warned_unknown_model
    _warned_unknown_model = False


def _is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(start <= cp <= end for start, end in _CJK_RANGES)


def estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate: 1 token ~= 4 chars (ASCII) / 1.5 chars (CJK)."""
    cjk = sum(1 for c in text if _is_cjk(c))
    other = len(text) - cjk
    return int(cjk / 1.5 + other / 4)
```

`_limit_for` 加一次性告警：

```python
def _limit_for(model: str) -> int:
    limit = MODEL_CONTEXT_LIMITS.get(model)
    if limit is None:
        global _warned_unknown_model
        if not _warned_unknown_model:
            _warned_unknown_model = True
            logging.getLogger("shenbi.cost.estimate").warning(
                "context_limit_unknown_model_conservative_fallback",
                extra={"model": model, "fallback_limit": _DEFAULT_CONTEXT_LIMIT},
            )
        return _DEFAULT_CONTEXT_LIMIT
    return limit
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/ -v`
Expected: PASS（含既有 estimate 测试无回归）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/estimate.py tests/unit/cost/test_estimate.py
git commit -m "fix: F523 CJK ext-A/fullwidth ranges + conservative unknown-model context fallback (spec #36 T6'a)"
```

---

### Task 2: ledger 字段扩展（estimated/attempt/pricing_status，兼容契约）

**Files:**
- Modify: `src/shenbi/cost/ledger.py:23-80`
- Test: `tests/unit/cost/test_ledger_fields.py`（新建）

**Interfaces:**
- Produces: `TokenUsageRecord(..., estimated: bool = False, attempt: int = 1, pricing_status: str = "ok")`；
  `TokenLedger.record(skill, chapter, usage, model=None, *, estimated: bool = False, attempt: int = 1) -> TokenUsageRecord`（`pricing_status` 由 record 内部判定：定价缺失 → `"unknown-model"`）。

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from shenbi.cost.ledger import TokenLedger, TokenUsageRecord


def _old_row(skill="chapter-drafting"):
    # 0d36d31a 时代的旧格式行：无新字段
    return json.dumps({
        "timestamp": "2026-08-16T00:00:00+00:00", "skill": skill, "chapter": 1,
        "model": "deepseek-v4-flash", "prompt_tokens": 10, "completion_tokens": 5,
        "total_tokens": 15, "estimated_cost_usd": 0.001,
    })


def test_mixed_old_and_new_rows_all_readable(tmp_path: Path):
    ledger = TokenLedger(tmp_path)
    ledger.record("s", 1, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
    with ledger.ledger_path.open("a", encoding="utf-8") as f:
        f.write(_old_row() + "\n")
    recs = list(ledger.iter_records())
    assert len(recs) == 2  # 兼容契约：旧行零 skip


def test_record_estimated_and_attempt_flags(tmp_path: Path):
    rec = TokenLedger(tmp_path).record(
        "s", 2, {"prompt_tokens": 100, "total_tokens": 100}, estimated=True, attempt=3
    )
    data = json.loads(ledger_last_line(tmp_path))
    assert data["estimated"] is True and data["attempt"] == 3
    assert rec.estimated is True and rec.pricing_status == "ok"


def test_unknown_model_marked_not_silent_zero(tmp_path: Path):
    rec = TokenLedger(tmp_path).record("s", 1, {"prompt_tokens": 10, "total_tokens": 10},
                                       model="no-such-model-v9")
    assert rec.pricing_status == "unknown-model"
    assert rec.model == "no-such-model-v9"  # 真实模型名保留


def ledger_last_line(tmp_path: Path) -> str:
    return TokenLedger(tmp_path).ledger_path.read_text(encoding="utf-8").strip().splitlines()[-1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_ledger_fields.py -v`
Expected: FAIL（`estimated` kwarg 不存在 / pricing_status 无）

- [ ] **Step 3: Write minimal implementation**

`ledger.py`：

```python
def _safe_estimate_cost(usage: dict[str, Any], model: str) -> tuple[float, str]:
    """(cost, pricing_status). Unknown model → (0.0, "unknown-model") — the
    row is explicitly marked instead of a silent $0 (C10 T404)."""
    try:
        return estimate_cost(usage, model), "ok"
    except ValueError:
        log.warning("ledger_unknown_model_no_pricing", model=model)
        return 0.0, "unknown-model"
```

```python
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
    # C10 v3 ledger 兼容契约：新字段一律带默认值，否则存量行在
    # iter_records 的 TokenUsageRecord(**data) TypeError-skip 下被静默销毁。
    estimated: bool = False
    attempt: int = 1
    pricing_status: str = "ok"
```

`record` 签名加 `*, estimated: bool = False, attempt: int = 1`；构造处：

```python
        cost, pricing_status = _safe_estimate_cost(usage, resolved)
        rec = TokenUsageRecord(
            ...,
            estimated_cost_usd=cost,
            estimated=estimated,
            attempt=attempt,
            pricing_status=pricing_status,
        )
```

注意：`resolve_model` 对 None 返回默认模型——`pricing_status` 判定发生在 resolve 后（unknown-model 仅当显式传入未知名）。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/ tests/pipeline/test_dispatch_helper_ledger.py tests/unit/pipeline/test_token_ledger_guard.py -v`
Expected: PASS 全部（既有 ledger 测试无回归——默认值保证旧行为不变）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/ledger.py tests/unit/cost/test_ledger_fields.py
git commit -m "fix: ledger estimated/attempt/pricing_status fields with defaults (spec #36 compat contract + T404)"
```

---

### Task 3: T5 — IDE/legacy 路径估记行（F796）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（新增 `_record_estimate_row` helper；`_dispatch_via_ide` 成功路径 ~:2114 处；legacy 子进程路由 ~:2334-2380）
- Test: `tests/unit/pipeline/test_estimate_rows.py`（新建）

**Interfaces:**
- Consumes: Task 1 `estimate_prompt_tokens`、Task 2 `record(..., estimated=True)`
- Produces: `_record_estimate_row(skill: str, chapter: int | None, prompt_text: str, project_dir: Path | None, attempt: int = 1) -> None`（fail-safe）

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from shenbi.pipeline import dispatch_helper as dh


def test_record_estimate_row_writes_estimated_true(tmp_path: Path, caplog):
    dh._record_estimate_row("skill-x", 3, "中文 prompt " * 100, tmp_path)
    line = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").strip()
    data = json.loads(line)
    assert data["estimated"] is True and data["chapter"] == 3
    assert data["prompt_tokens"] > 0 and data["completion_tokens"] == 0


def test_record_estimate_row_fail_safe(tmp_path: Path):
    dh._record_estimate_row("s", None, "p", None)  # project_dir None → WARN 不 raise


def test_ide_dispatch_records_estimate_row(tmp_path: Path, monkeypatch):
    # fake IDE CLI: 成功返回（_write_parsed_outputs stub 掉写盘）
    class R:
        returncode = 0
        stdout = "### FILE: out.md\nhi"
        stderr = ""
    monkeypatch.setattr(dh.subprocess, "run", lambda *a, **k: R())
    monkeypatch.setattr(dh, "_find_ide_cli", lambda: ["cat", "{dir}"])
    monkeypatch.setattr(dh, "_build_skill_prompt", lambda *a, **k: ("sys", "user", ["out.md"]))
    monkeypatch.setattr(dh, "_write_parsed_outputs", lambda *a, **k: True)
    res = dh._dispatch_via_ide("skill-x", tmp_path, "写第 3 章 chapter-003.md")
    assert res.success
    rows = [json.loads(l) for l in
            (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(r["estimated"] is True for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_estimate_rows.py -v`
Expected: FAIL（`_record_estimate_row` 不存在）

- [ ] **Step 3: Write minimal implementation**

dispatch_helper.py 新 helper（放 `_record_usage_to_ledger` 旁）：

```python
def _record_estimate_row(
    skill: str,
    chapter: int | None,
    prompt_text: str,
    project_dir: Path | None,
    attempt: int = 1,
) -> None:
    """Append a lower-bound estimated row (C10 spec T5/F796).

    IDE/subprocess paths cannot report structured usage; the prompt estimate
    is a floor, explicitly marked estimated=True so the report can separate
    it from metered rows. Fail-safe like _record_usage_to_ledger.
    """
    if project_dir is None:
        log.warning("ledger_skip_no_project_dir", skill=skill)
        return
    try:
        from shenbi.cost.estimate import estimate_prompt_tokens

        est = estimate_prompt_tokens(prompt_text)
        TokenLedger(project_dir).record(
            skill,
            chapter or 0,
            {"prompt_tokens": est, "completion_tokens": 0, "total_tokens": est},
            estimated=True,
            attempt=attempt,
        )
    except Exception:
        log.warning("ledger_estimate_record_failed", skill=skill, exc_info=True)
```

接线：`_dispatch_via_ide` 成功返回前——在 `if state is not None:` info-only 块（:2114-2122）**之外、之前**无条件调用 `_record_estimate_row(skill, chapter, full_prompt, project_dir)`（state 块仅是日志，多数调用点无 state；info 日志保留）。legacy 子进程路由（`dispatch_skill` 内 `uv run shenbi-dispatch` 分支）：派发完成后同样调用（prompt 变量以该分支实际变量名为准）。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_estimate_rows.py tests/unit/pipeline/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_estimate_rows.py
git commit -m "fix: IDE + legacy subprocess dispatch record estimated lower-bound ledger rows (spec #36 T5/F796)"
```

---

### Task 4: T4 — 章循环/闭卷自动 cost 报告（T402/F1115）

**Files:**
- Modify: `src/shenbi/cost/report.py`（新增 `write_report` fail-safe 落盘函数 + T406′ 警告行 + estimated 分列——T6′b 的报告面改动合并于此 task 的 render 改动一起做见 Task 5，本 task 只加 `write_report`）；`src/shenbi/pipeline/chapter_loop.py`（`_complete_chapter` ~:1014 后段）；`src/shenbi/pipeline/closure.py`（`run_closure_step` 的 `idx >= n` 完成分支 ~:273-276）
- Test: `tests/unit/pipeline/test_cost_report_auto.py`（新建）

**Interfaces:**
- Consumes: `render_report(project_dir: Path | str) -> str`（report.py:44）
- Produces: `write_report(project_dir: Path | str) -> Path | None`（渲染 + 写 `cost/report.md`，异常 WARN 返 None）

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import write_report
from shenbi.pipeline import chapter_loop, closure


def test_write_report_creates_file(tmp_path: Path):
    TokenLedger(tmp_path).record("s", 1, {"prompt_tokens": 5, "total_tokens": 5})
    out = write_report(tmp_path)
    assert out == tmp_path / "cost" / "report.md" and out.exists()


def test_write_report_fail_safe(tmp_path: Path, monkeypatch):
    import shenbi.cost.report as rep
    monkeypatch.setattr(rep, "render_report", lambda p: (_ for _ in ()).throw(RuntimeError("x")))
    assert write_report(tmp_path) is None  # WARN 不 raise


def test_complete_chapter_renders_report(tmp_path: Path, monkeypatch):
    # 参照 tests/unit/pipeline/ 既有 fake-state 模式：_complete_chapter 需要
    # state.project_dir / state.chapter_loop.chapter_states；上游检查打桩。
    from types import SimpleNamespace as NS
    from shenbi.pipeline import chapter_loop
    monkeypatch.setattr("shenbi.pipeline.product_contracts.check_product_contracts", lambda pd: [])
    monkeypatch.setattr(chapter_loop, "_maybe_rebuild_truth_index", lambda *a: None)
    # 其余下游（checkpoint 设定等）按 _complete_chapter 实际代码路径补桩，
    # 目标断言只有一个：函数返回后 cost/report.md 存在。
    state = NS(project_dir=str(tmp_path),
               chapter_loop=NS(chapter_states={}),
               # 按 _complete_chapter 读到的其余属性逐个补 NS 默认
               )
    try:
        chapter_loop._complete_chapter(state, 1)
    except Exception:
        pass  # 下游桩缺失导致的错不属本验收面
    assert (tmp_path / "cost" / "report.md").exists()


def test_closure_completed_renders_report(tmp_path: Path, monkeypatch):
    from types import SimpleNamespace as NS
    from shenbi.pipeline import closure as clo
    state = NS(closure_step=len(clo.CLOSURE_STEPS), closure=None,
               closure_retries={}, project_dir=str(tmp_path))
    assert clo.run_closure_step(state, tmp_path) is True
    assert state.closure == clo.ClosureState.COMPLETED
    assert (tmp_path / "cost" / "report.md").exists()
```

（两测试的 state 属性集在实现时按 `_complete_chapter`/`run_closure_step` 实际读取面校准——目标是断言报告产出，桩属性缺失时补 NS 字段而非放宽断言。）

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_cost_report_auto.py -v`
Expected: FAIL（`write_report` 不存在）

- [ ] **Step 3: Write minimal implementation**

report.py 追加：

```python
from shenbi.logging import get_logger

log = get_logger(__name__)


def write_report(project_dir: Path | str) -> Path | None:
    """Render + persist cost/report.md. Node-level automation (C10 spec T4):
    fail-safe — a report error must never break the chapter loop."""
    project_dir = Path(project_dir)
    out = project_dir / "cost" / "report.md"
    try:
        out.write_text(render_report(project_dir), encoding="utf-8")
        return out
    except Exception:
        log.warning("cost_report_write_failed", project_dir=str(project_dir), exc_info=True)
        return None
```

chapter_loop `_complete_chapter`：在 `cs.status = ChapterStatus.COMPLETE` 赋值后追加：

```python
    from shenbi.cost.report import write_report

    write_report(project_dir)  # C10 spec T4: node-level cost report, fail-safe
```

closure `run_closure_step` 的 `idx >= n` 分支：

```python
    if idx >= n:
        state.closure = ClosureState.COMPLETED
        from shenbi.cost.report import write_report

        write_report(project_dir)  # C10 spec T4: closure-node cost report
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_cost_report_auto.py tests/unit/pipeline/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/report.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/closure.py tests/unit/pipeline/test_cost_report_auto.py
git commit -m "feat: chapter-completion + closure nodes auto-render cost/report.md (spec #36 T4/T402/F1115)"
```

---

### Task 5: T6′b — 报告面诚实化（T406′ 警告行 + estimated 分列）

**Files:**
- Modify: `src/shenbi/cost/report.py:74-78`
- Test: `tests/unit/cost/test_report_honesty.py`（新建）

**Interfaces:**
- Consumes: Task 2 `estimated` 字段
- Produces: render_report 输出含 per-chapter average 警告行 + estimated 行分列行

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from shenbi.cost.ledger import TokenLedger
from shenbi.cost.report import render_report


def test_per_chapter_average_has_caveat_line(tmp_path: Path):
    TokenLedger(tmp_path).record("s", 1, {"prompt_tokens": 5, "total_tokens": 5})
    text = render_report(tmp_path)
    assert "Per-chapter average cost" in text
    assert "total cost / chapter count" in text  # 警告行


def test_estimated_rows_broken_out(tmp_path: Path):
    TokenLedger(tmp_path).record("metered", 1, {"prompt_tokens": 5, "total_tokens": 5})
    TokenLedger(tmp_path).record("unmetered", 2, {"prompt_tokens": 50, "total_tokens": 50},
                                 estimated=True)
    text = render_report(tmp_path)
    assert "Estimated (lower-bound) rows: 1" in text
    assert "50" in text.split("Estimated (lower-bound) rows: 1")[1].splitlines()[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/cost/test_report_honesty.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

report.py `render_report` 中 per-chapter average 块改为：

```python
    by_chapter = summary["by_chapter"]
    if by_chapter:
        ch_costs = [c["estimated_cost_usd"] for c in by_chapter.values()]
        avg = sum(ch_costs) / len(ch_costs)
        lines += [
            "",
            f"- **Per-chapter average cost**: ${avg:.4f}",
            f"  - note: this equals total cost / chapter count "
            f"(by-chapter buckets carry no independent signal)",
        ]

    est_rows = [r for r in TokenLedger(project_dir).iter_records() if r.estimated]
    if est_rows:
        est_tokens = sum(r.total_tokens for r in est_rows)
        lines += [
            "",
            f"- **Estimated (lower-bound) rows**: {len(est_rows)} calls / "
            f"{est_tokens:,} tokens (IDE/subprocess paths; $0 priced, not in cost totals)",
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/cost/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/report.py tests/unit/cost/test_report_honesty.py
git commit -m "fix: per-chapter average caveat line + estimated rows broken out in cost report (spec #36 T6'b/T406')"
```

---

### Task 6: T7 — 重试入账二分 + dispatch trace 事件（F1116/T410）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（`_call_llm_streaming` ~:1685-1740 增 `usage_acc` 参数；`_call_llm_streaming_with_retry` ~:1741-1767 透传；`_dispatch_via_api` ~:1780-1900 异常分支 + 收尾处 trace 事件）
- Test: `tests/unit/pipeline/test_retry_accounting.py`（新建）

**Interfaces:**
- Consumes: Task 2 `record(..., attempt=N)` / `estimated=True`、Task 3 `_record_estimate_row`
- Produces: `_call_llm_streaming(..., usage_acc: dict[str, Any] | None = None)`；`_emit_dispatch_trace(project_dir, skill, chapter, model, finish_reason, estimated, attempt, success)` helper

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from types import SimpleNamespace as NS
from shenbi.pipeline import dispatch_helper as dh


def _fake_client(stream):
    """client stub whose create() returns the given iterable stream."""
    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    return stream
    return Client()


class _MidstreamStream:
    """建流成功、中途断流——usage 永不送达。"""
    def __iter__(self):
        yield NS(usage=None, choices=[NS(finish_reason=None, delta=NS(content="部分"))])
        raise ConnectionError("reset")


class _UsageThenErrorStream:
    """usage 已送达后失败——流末失败形态。"""
    def __iter__(self):
        yield NS(usage=None, choices=[NS(finish_reason="stop", delta=NS(content="ok"))])
        yield NS(usage=NS(prompt_tokens=10, completion_tokens=4, total_tokens=14), choices=[])
        raise ConnectionError("reset-after-usage")


def test_usage_acc_semantics_midstream():
    """usage_acc 语义单元层断言：中途断流 usage 永不送达，attempts 递增。"""
    acc: dict = {}
    try:
        dh._call_llm_streaming(_fake_client(_MidstreamStream()), "m",
                               [{"role": "user", "content": "写"}], usage_acc=acc)
    except ConnectionError:
        pass
    assert acc.get("usage") is None
    assert acc.get("attempts", 0) >= 1


def test_wrapper_accounts_via_dispatch_api_midstream(tmp_path: Path, monkeypatch):
    """_dispatch_via_api 级：中途断流 → estimated 行 + attempt ≥ 1。"""
    from unittest.mock import patch

    monkeypatch.setenv("SHENBI_LLM_API_KEY", "k")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    with (
        patch("openai.OpenAI") as mock_openai,
        patch("shenbi.pipeline.dispatch_helper._build_skill_prompt",
              return_value=("sys", "user", ["chapters/chapter-1.md"])),
    ):
        mock_openai.return_value.chat.completions.create.return_value = _MidstreamStream()
        res = dh._dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
    assert not res.success
    rows = [json.loads(l) for l in
            (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(r.get("estimated") is True and r["attempt"] >= 1 for r in rows)


def test_wrapper_accounts_real_usage_after_stream_end(tmp_path: Path, monkeypatch):
    """流末失败（usage 已送达）→ 真实 usage 行 attempt ≥ 1。"""
    from unittest.mock import patch

    monkeypatch.setenv("SHENBI_LLM_API_KEY", "k")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    with (
        patch("openai.OpenAI") as mock_openai,
        patch("shenbi.pipeline.dispatch_helper._build_skill_prompt",
              return_value=("sys", "user", ["chapters/chapter-1.md"])),
    ):
        mock_openai.return_value.chat.completions.create.return_value = _UsageThenErrorStream()
        res = dh._dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
    assert not res.success
    rows = [json.loads(l) for l in
            (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(r.get("estimated") is not True and r["prompt_tokens"] == 10
               and r["attempt"] >= 1 for r in rows)


def test_success_emits_dispatch_trace_with_finish_reason(tmp_path: Path, monkeypatch):
    from unittest.mock import patch

    (tmp_path / "trace.jsonl").write_text("", encoding="utf-8")  # 预置 trace 流
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "k")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    fake_stream = [
        NS(usage=None, choices=[NS(finish_reason="stop", delta=NS(content="### FILE: chapters/chapter-1.md\nbody\n"))]),
        NS(usage=NS(prompt_tokens=5, completion_tokens=1, total_tokens=6), choices=[]),
    ]
    with (
        patch("openai.OpenAI") as mock_openai,
        patch("shenbi.pipeline.dispatch_helper._build_skill_prompt",
              return_value=("sys", "user", ["chapters/chapter-1.md"])),
    ):
        mock_openai.return_value.chat.completions.create.return_value = fake_stream
        res = dh._dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
    assert res.success
    events = [json.loads(l) for l in
              (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines() if l]
    disp = [e for e in events if e["action"] == "DISPATCH"]
    assert disp and disp[0]["payload"]["finish_reason"] == "stop"


```

（`_is_retryable` 对 ConnectionError 的归类决定 attempt 计数上限；若 ConnectionError 非 retryable，attempt=1 仍满足 `>= 1` 断言。timeout 路径同构，不单测。）

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_retry_accounting.py -v`
Expected: FAIL（`usage_acc` 参数不存在）

- [ ] **Step 3: Write minimal implementation**

1. `_call_llm_streaming` 签名尾部加 `usage_acc: dict[str, Any] | None = None`；函数开头：

```python
    if usage_acc is not None:
        usage_acc["attempts"] = usage_acc.get("attempts", 0) + 1
        usage_acc.pop("usage", None)  # fresh attempt invalidates stale usage
```

usage 捕获处（chunk.usage 分支）同步写 `usage_acc["usage"] = usage`。

2. `_call_llm_streaming_with_retry` 不改签名（`**kwargs` 已透传 `usage_acc`）——`_dispatch_via_api` 调用处传入：

```python
    usage_acc: dict[str, Any] = {}
    try:
        output_text, stop_reason, usage, finish_reason = _call_llm_streaming_with_retry(
            client, model, [...], usage_acc=usage_acc, ...
        )
    except httpx.TimeoutException:
        _account_failed_attempt(skill, chapter, usage_acc, system_prompt, user_prompt, project_dir)
        _emit_dispatch_trace(project_dir, skill, chapter, model, None, True, usage_acc.get("attempts", 1), success=False)
        _handle_timeout_gracefully(skill, chapter)
        log.error("api_call_timeout", skill=skill)
        return DispatchResult(False, -1, "", "API call timed out")
    except Exception as exc:
        _account_failed_attempt(skill, chapter, usage_acc, system_prompt, user_prompt, project_dir)
        _emit_dispatch_trace(project_dir, skill, chapter, model, None, True, usage_acc.get("attempts", 1), success=False)
        log.error("api_call_failed", skill=skill, error=str(exc))
        return DispatchResult(False, -1, "", f"API call failed: {exc}")
```

3. 二分入账 helper：

```python
def _account_failed_attempt(
    skill: str,
    chapter: int | None,
    usage_acc: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    project_dir: Path,
) -> None:
    """C10 spec T7 bifurcation: (a) usage already delivered before the failure
    → metered row with attempt=N; (b) failure before usage arrived (mid-stream
    or connect) → estimated lower-bound row. Fail-safe."""
    try:
        attempts = int(usage_acc.get("attempts", 1))
        usage = usage_acc.get("usage")
        if usage is not None:
            _record_usage_to_ledger(skill, chapter, usage, project_dir, attempt=attempts)
        else:
            _record_estimate_row(skill, chapter, f"{system_prompt}\n\n{user_prompt}",
                                 project_dir, attempt=attempts)
    except Exception:
        log.warning("failed_attempt_accounting_error", skill=skill, exc_info=True)
```

`_record_usage_to_ledger` 增加可选 `attempt: int = 1` 透传到 `record(..., attempt=attempt)`。

4. 成功路径 trace：`_dispatch_via_api` 收尾（`api_dispatch_complete` 日志附近，finish_reason 已知处）：

```python
    _emit_dispatch_trace(project_dir, skill, chapter, model, finish_reason,
                         bool(usage is None), usage_acc.get("attempts", 1), success=True)
```

5. trace helper（fail-safe，trace 不存在则 DEBUG 跳过——不新建 trace 文件面）：

```python
def _emit_dispatch_trace(
    project_dir: Path,
    skill: str,
    chapter: int | None,
    model: str,
    finish_reason: str | None,
    estimated: bool,
    attempt: int,
    *,
    success: bool,
) -> None:
    """C10 spec T7: DISPATCH trace event (finish_reason visibility, F1116).

    Only appends when a trace stream already exists in project_dir — dispatch
    must not silently create new trace surfaces. payload is a free dict, so
    no schema_version bump and no G7 chain impact."""
    trace_path = Path(project_dir) / "trace.jsonl"
    if not trace_path.exists():
        log.debug("dispatch_trace_skipped_no_trace", skill=skill)
        return
    try:
        from shenbi.trace.writer import TraceWriter

        TraceWriter(Path(project_dir)).append(
            actor="dispatch_helper",
            actor_role="SYSTEM",
            action="DISPATCH",
            target=f"skill:{skill}",
            skill=skill,
            payload={
                "chapter": chapter,
                "model": model,
                "finish_reason": finish_reason,
                "estimated": estimated,
                "attempt": attempt,
                "success": success,
            },
        )
    except Exception:
        log.warning("dispatch_trace_append_failed", skill=skill, exc_info=True)
```

（`actor_role="SYSTEM"` 为 `ActorRole` Literal 合法值；`action="DISPATCH"` 经 payload 自由 dict 语义，不触发状态字面量 lint——lint 只管 gate/phase 状态字面量，实现后跑 `just check` 验证。）

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_retry_accounting.py tests/unit/pipeline/ tests/pipeline/ -v`
Expected: PASS（含既有 test_retry.py / usage capture 测试——`usage_acc` 默认 None 不改既有行为）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_retry_accounting.py
git commit -m "fix: retry-attempt usage accounting bifurcation + DISPATCH trace events (spec #36 T7/F1116/T410)"
```

---

## 验收覆盖表（spec v3 验收 → task → 验证命令）

| 验收 | task | 验证 |
|---|---|---|
| 1 章循环/闭卷产出报告 + fail-safe | T4 | `uv run pytest tests/unit/pipeline/test_cost_report_auto.py -v` |
| 2 IDE 估记行 | T3 | `uv run pytest tests/unit/pipeline/test_estimate_rows.py -v` |
| 3 unknown-model 标记 + model 名保留 | T2 | `uv run pytest tests/unit/cost/test_ledger_fields.py -v` |
| 4 per-chapter average 警告行 | T5 | `uv run pytest tests/unit/cost/test_report_honesty.py -v` |
| 5 扩区估记严格更大 + 保守回退一次性告警 | T1 | `uv run pytest tests/unit/cost/test_estimate.py -v` |
| 6 二分入账 + trace finish_reason | T6 | `uv run pytest tests/unit/pipeline/test_retry_accounting.py -v` |
| 7 新旧行混合可读 | T2 | `test_mixed_old_and_new_rows_all_readable` |
| 8 just check 全绿 | 全 | `just check` |

评分场景：无（本 spec 不涉及 G3 评分产出）。

## 已知残余盲点（阶段 5 审查 I4 裁定 · out-of-scope）

- `_dispatch_via_api` 的 cap-raise 二次调用（`finish_reason == "length"` 后 ~:1907-1924 的第二次 `_call_llm_streaming_with_retry`）不接 `usage_acc`/入账/trace——其异常分支沿用现状（成功路径 usage 已在 :1868 入账）。留待后续 spec（trace 完整面），本 plan 显式排除。
- content_filter / length-at-ceiling 失败返回路径：usage 已入账（metered 行），仅缺 DISPATCH trace 事件；与 cap-raise 同属上述残余面。
- M3 记录：`_emit_dispatch_trace` 采用「project_dir/trace.jsonl 已存在则 append」而非 spec 的 round_dir 措辞——语义等价（防新建 trace 面）， DISPATCH 事件无程序化消费方，属 G7 审计证据面（spec 明确要求，非 dead-wire）。
