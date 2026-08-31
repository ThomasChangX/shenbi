# Spec #37 并发/durability（簇 C11）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec #37 v3 统一锁协议收敛跨进程写路径、修复锁原语/TOCTOU/物化覆盖，并固化并发回归套件。

**Architecture:** 三锁域收敛为两级协议（L1=WriteLock 项目级；L2=per-path 锁文件→目录 flock，禁 L2→L1）。safe_write 增 `locked_transact` 锁定读改写；绕锁写方按文件族归属表迁移；物化调用点按裁定 (b) 移除。

**Tech Stack:** Python 3.11+，fcntl.flock（POSIX 权威）、filelock（Windows 回退）、pytest（并发用例 POSIX-only skipif）。

## Global Constraints

- 全部 task 为 **infra**——协调者亲自实现（SDD 单模型分流规则），TDD 红-绿。
- 验证命令一律 `uv run pytest ...`（与 CI `uv run --frozen` 同构）。
- src/shenbi/ 禁 `print()`（structlog）、gate 检查器纯函数幂等。
- 新 Literal 状态值唯一定义于 `src/shenbi/contracts/enums.py`（本 plan 预计零新增）。
- 并发测试 POSIX-only（`pytest.mark.skipif(sys.platform == "win32")`），单用例墙钟 ≤30s，确定性交错（barrier/预置状态），不依赖纯时序。
- 每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审）。
- 测试不造手写 LLM fixture（G0.9）；本 plan 全部测试用真实代码路径 + 临时目录内构造的**状态文件**（非 LLM 产物，不受 G0.9 约束）。

## 文件结构（改动面总览）

- Modify: `src/shenbi/safe_write.py`（locked_transact + stale-takeover 活性）
- Modify: `src/shenbi/pipeline/filelock_utils.py`（holder 自检 + 模式记录）
- Modify: `src/shenbi/pipeline/crash_recovery.py`（latch + L1 自检）
- Modify: `src/shenbi/pipeline/cli.py`（cmd_init 单临界区、backfill 持锁）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（移除 materialize 调用点）
- Modify: `src/shenbi/trace/{writer,compaction,materialize}.py`（per-path 锁、key-merge）
- Modify: `src/shenbi/audit/record.py`（append helper fsync+时间戳）
- Modify: `src/shenbi/cost/ledger.py`（去 mkdir 副作用 + 目录 flock）
- Modify: `src/shenbi/gates/gate_manifest.py`（跨进程锁 + fail-loud）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（locked_transact 迁移 + genre 缓存键）
- Modify: `src/shenbi/dispatcher/modes/codex.py`（locked_transact 迁移）
- Modify: `src/shenbi/pipeline/truth_io.py`（锁注册表淘汰上界 + refcount）
- Modify: `src/shenbi/config/config_coherence.py`（F605 trail 失败回滚）
- Create: `src/shenbi/append_helper.py`（追加类统一 fsync+时间戳+目录锁）
- Create: `tools/lint_bare_writes.py`（豁免注记校验）+ justfile 接线
- Create: `tests/unit/pipeline/test_concurrency_regression.py`（T0/T6 套件）

---

### Task 1: T0 复现用例先行（红）

**Files:**
- Create: `tests/unit/pipeline/test_concurrency_regression.py`

**Interfaces:**
- Produces: 五个红测函数名（Task 2-9 翻绿时按名引用）：`test_t605_dual_writer_lost_update`、`test_t601_concurrent_integrity_findings_conservation`、`test_f531_trace_seq_duplicate`、`test_t604_emergency_cleanup_double_execution`、`test_f630_materialize_clobbers_foreign_keys`

- [ ] **Step 1: 写红测文件（全文）**

```python
"""T0 red-first reproduction suite for spec #37 (cluster C11).

Every test here reproduces a LIVE defect on main and is expected to FAIL
(red) until the corresponding fix task lands. Deterministic interleaving
strategies are mandatory — no pure-timing reliance. POSIX-only (flock).
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="flock POSIX-only")


def test_t605_dual_writer_lost_update(tmp_path: Path) -> None:
    """Two unlocked state writers alternating via barrier lose updates (T605)."""
    from shenbi.pipeline.machine import load_state, save_state
    from shenbi.pipeline.state import PipelineState

    save_state(tmp_path, PipelineState(project_dir=str(tmp_path)))
    barrier = threading.Barrier(2)
    N = 25  # per-thread increments

    def bump() -> None:
        barrier.wait(timeout=10)  # align start once, deterministic
        for _ in range(N):
            loaded = load_state(tmp_path)
            loaded.chapter_loop.current_chapter += 1
            save_state(tmp_path, loaded)

    t1, t2 = threading.Thread(target=bump), threading.Thread(target=bump)
    t1.start(); t2.start(); t1.join(timeout=25); t2.join(timeout=25)
    assert load_state(tmp_path).chapter_loop.current_chapter == 2 * N  # red: lost updates


def test_t601_concurrent_integrity_findings_conservation(tmp_path: Path) -> None:
    """5 concurrent per-chapter auditors appending findings must conserve lines (T601)."""
    from shenbi.pipeline.dispatch_helper import _append_integrity_findings

    target = tmp_path / "chapters" / "chapter-001.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    barrier = threading.Barrier(5)

    def append_one(i: int) -> None:
        barrier.wait(timeout=10)
        _append_integrity_findings(tmp_path, target, [f"finding-{i}"])

    threads = [threading.Thread(target=append_one, args=(i,)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=25)
    out = tmp_path / "audits" / ".integrity-findings-001.jsonl"
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5  # red: last-writer-wins drops lines


def test_f531_trace_seq_duplicate(tmp_path: Path) -> None:
    """Two TraceWriter instances appending concurrently must not duplicate seq (F531)."""
    from shenbi.contracts.enums import ActorRole
    from shenbi.trace.writer import TraceWriter

    barrier = threading.Barrier(2)
    K = 10  # appends per writer

    def write_many(tag: str) -> None:
        barrier.wait(timeout=10)
        w = TraceWriter(tmp_path)
        for i in range(K):
            w.append(actor=tag, actor_role=ActorRole.GATE, action="TEST",
                     target="t", payload={"i": i})

    t1 = threading.Thread(target=write_many, args=("a",))
    t2 = threading.Thread(target=write_many, args=("b",))
    t1.start(); t2.start(); t1.join(timeout=25); t2.join(timeout=25)
    seqs = [json.loads(ln)["seq"] for ln in
            (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(seqs) == len(set(seqs)) == 2 * K  # red: both start at seq=1


def test_t604_emergency_cleanup_double_execution(tmp_path: Path, monkeypatch) -> None:
    """Signal path + atexit must trigger emergency cleanup exactly once (T604)."""
    import shenbi.pipeline.crash_recovery as cr
    import shenbi.pipeline.machine as machine

    calls: list[str] = []
    # crash_recovery imports save_state locally (machine.save_state at :125)
    monkeypatch.setattr(machine, "save_state", lambda *a, **k: calls.append("save"))
    cr._emergency_state["project_dir"] = tmp_path
    cr._emergency_state["pipeline_state"] = object()  # truthy sentinel
    cr._emergency_flag = True
    cr._check_emergency_flag(tmp_path)   # step-boundary path
    cr._emergency_cleanup(tmp_path)      # atexit path fires again
    assert len(calls) == 1  # red: save_state called twice


def test_f630_materialize_clobbers_foreign_keys(tmp_path: Path) -> None:
    """materialize_progress must preserve keys it does not own (F630)."""
    from shenbi.trace.materialize import materialize_progress

    progress = tmp_path / "progress.json"
    progress.write_text(json.dumps({
        "custom_key": 1,
        "skills": {"x": {"generative": {"status": "DONE", "score": 95.0}}},
    }, ensure_ascii=False), encoding="utf-8")
    materialize_progress(tmp_path, total_skills=["x"], tier="T1")
    out = json.loads(progress.read_text(encoding="utf-8"))
    assert out.get("custom_key") == 1  # red: wholesale rebuild drops it
    assert out["skills"]["x"]["generative"]["status"] == "DONE"  # red: rebuilt as pending
```

- [ ] **Step 2: 跑红**

Run: `uv run pytest tests/unit/pipeline/test_concurrency_regression.py -v`
Expected: 5 FAIL（复现 bug）

- [ ] **Step 3: Commit**

```bash
git add tests/unit/pipeline/test_concurrency_regression.py
git commit -m "test: spec37 T0 red-first reproduction suite (T605/T601/F531/T604/F630)"
```

### Task 2: locked_transact + F206/F347 迁移

**Files:**
- Modify: `src/shenbi/safe_write.py`
- Modify: `src/shenbi/dispatcher/modes/codex.py:23-67`（`_record_completion`）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1126-1141`（`_append_integrity_findings`）

**Interfaces:**
- Produces: `def locked_transact(path: Path, mutator: Callable[[dict|str|None], dict|str], *, default: ... = None) -> None`——目录 flock 临界区内 read→mutator→safe_write 落盘。mutator 收到解析后内容（JSON dict 或 raw str），返回新内容。

- [ ] **Step 1: 红测**（并入 test_concurrency_regression.py：T601/F630 用例直接锁这个原语；新增 `test_locked_transact_mutual_exclusion`：两线程经 locked_transact 并发递增计数，断言终值==2N——先写测试再实现，测试 import `from shenbi.safe_write import locked_transact` → ImportError 红）
- [ ] **Step 2: 实现 locked_transact**（`_acquire_lock(path)` 包住 read→mutate→`safe_write`；JSON 文件自动 loads/dumps，mutator 收 dict；非 JSON 传 str）
- [ ] **Step 3: 迁移 `_record_completion`**：读改写段替换为 `locked_transact(progress_path, _mutate_progress(skill, test_type, score, output_files))`
- [ ] **Step 4: 迁移 `_append_integrity_findings`**：同上（mutator 追加行）
- [ ] **Step 5: 跑测**：`uv run pytest tests/unit/pipeline/test_concurrency_regression.py tests/unit/test_safe_write.py -v` → T601 红→绿，locked_transact 绿
- [ ] **Step 6: Commit** `fix: locked_transact primitive + migrate _record_completion/_append_integrity_findings (F206/F347, spec37 T1a)`

### Task 3: WriteLock holder 自检 + T604 latch + init/backfill 收敛

**Files:**
- Modify: `src/shenbi/pipeline/filelock_utils.py`
- Modify: `src/shenbi/pipeline/crash_recovery.py:67-110`
- Modify: `src/shenbi/pipeline/cli.py`（cmd_init :424-505、cmd_backfill_context :929）

**Interfaces:**
- Produces: `filelock_utils.holder_mode() -> Literal[None, "read", "write"]`（模块级 holder 标志，`WriteLock.__enter__/__exit__` 维护，记录线程 id，finally 清除）；`crash_recovery._CLEANUP_DONE: bool` latch。

- [ ] **Step 1: 红测**：`test_holder_mode_tracks_write_lock`（with WriteLock: assert holder_mode()=="write"；退出后 None）；`test_t604_emergency_cleanup_single_execution`（T604 红测翻绿：latch 使二次调用 no-op）
- [ ] **Step 2: 实现 holder 标志**（WriteLock/ReadLock enter/exit 维护；`_emergency_cleanup` 头部：`if holder_mode()=="write": 直接落盘；elif holder_mode()=="read": raise/释放重验路径`；加 latch）
- [ ] **Step 3: cmd_init 收进单 WriteLock 临界区**（存在性检查+种子写+save 全入；ReadLock 检查段改在 WriteLock 内直接 load）
- [ ] **Step 4: cmd_backfill_context 外层 `with WriteLock(project_path)`**
- [ ] **Step 5: 跑测**：`uv run pytest tests/unit/pipeline/ -k "holder or emergency or init or backfill" -v` + T605/T604 用例
- [ ] **Step 6: Commit** `fix: L1 holder self-check + T604 latch + cmd_init/backfill critical sections (T605/F327/T606, spec37 T1b)`

### Task 4: trace per-path 锁（F531/F536/F619）

**Files:**
- Create: `src/shenbi/trace/locks.py`（`def trace_lock(round_dir: Path) -> contextmanager`：flock `<round_dir>/trace.jsonl.lockfile`）
- Modify: `src/shenbi/trace/writer.py`（`__init__` 计数+`append` 收进 trace_lock 临界区）
- Modify: `src/shenbi/trace/compaction.py:48-76`（temp+replace 收进 trace_lock）
- Modify: `src/shenbi/audit/record.py`（`record_audit_outcome` 的 TraceWriter append 段在 trace 存在时经 trace_lock）

**Interfaces:**
- Produces: `shenbi.trace.locks.trace_lock(round_dir)` contextmanager（per-path flock；`.gitignore` 增 `*.lockfile` 与 `*.lock` 模式）

- [ ] **Step 1: 红测**（F531 翻绿用例已在 T0；新增 `test_trace_writer_compaction_mutual_exclusion`：一线程 compaction、一线程 append，barrier 对齐，断言无撕裂）
- [ ] **Step 2: 实现**；**Step 3: .gitignore 两模式**；**Step 4: 跑 F531 用例 + tests/unit/trace/**；**Step 5: Commit** `fix: trace per-path flock for TraceWriter/compaction/audit seam (F531/F536/F619, spec37 T1c)`

### Task 5: gate_manifest 跨进程锁 + fail-loud（F416）

**Files:**
- Modify: `src/shenbi/gates/gate_manifest.py`

**Interfaces:**
- Consumes: safe_write 目录 flock（L2 序：per-path → 目录）。
- Produces: `_manifest_lock` 返回跨进程 flock（`<manifest_dir>/pipeline-manifest.json.lockfile`）；`_load_gate_manifest` 损坏时 `raise ManifestCorruptError`（新异常类，定义于本文件，继承 `shenbi.exceptions.ShenbiError`），调用方 `record_gate_result` 捕获后结构化 log.error + 保留损坏副本 `pipeline-manifest.json.corrupt` 后重建。

- [ ] **Step 1: 红测**（写入坏 JSON manifest → 断言 `.corrupt` 副本存在且 log 含 manifest_corrupt；双线程 record_gate_result 并发断言两 gate 记录均在）
- [ ] **Step 2-4: 实现 + 跑测 + Commit** `fix: gate_manifest cross-process lock + fail-loud corruption (F416, spec37 T1d/T5)`

### Task 6: safe_write stale-takeover 活性双检 + 回退段测试（T603/F111）

**Files:**
- Modify: `src/shenbi/safe_write.py:63-91`
- Test: `tests/unit/test_safe_write.py`

- [ ] **Step 1: 红测**：`test_stale_takeover_requires_dead_holder`（活锁：另一进程/线程持有 `.lock` 且 mtime 新鲜 → takeover 不发生，等满超时）；`test_stale_takeover_on_stale_lock`（mtime>60s 旧 → 接管成功）；`test_oexcl_backoff_segment`（首次冲突→退避→获取）
- [ ] **Step 2: 实现**：O_EXCL 分支写 pid+timestamp 进锁文件；takeover 前检查 mtime 龄期（>STALE_LOCK_TTL=60s）且（POSIX）pid 不存活；不满足则继续退避至总超时（10s）后 TimeoutError（不再无条件 unlink）。Windows：保留超时接管 + `log.warning("lock_takeover_timeout_fallback")`
- [ ] **Step 3-4: 跑 `uv run pytest tests/unit/test_safe_write.py -v` 全绿 + Commit** `fix: stale-takeover liveness proof + O_EXCL fallback tests (T603/F111, spec37 T2)`

### Task 7: TokenLedger 读副作用/锁域 + genre 缓存键 + 注册表淘汰（T602/F510/F525/T407/T408/T607）

**Files:**
- Modify: `src/shenbi/cost/ledger.py:62-96`
- Modify: `src/shenbi/pipeline/dispatch_helper.py:212-221`
- Modify: `src/shenbi/pipeline/truth_io.py:55-71`

- [ ] **Step 1: 红测**：`test_ledger_ctor_no_mkdir`（构造 TokenLedger 指向不存在目录 → cost/ 不被创建）；`test_genre_cache_keyed_by_project_dir`（两 project_dir 同 chapter → 不串）；`test_path_lock_registry_bounded`（注册 1000 路径 → 条目数 ≤ 上界 256）
- [ ] **Step 2: 实现**：构造器去 mkdir（`record` 内 `self.ledger_path.parent.mkdir`）；`_write_lock` 弃用，record 落盘经 append helper（Task 9 的 fsync+目录锁）或目录 flock；`_genre_config_cache` 键改 `(str(project_dir), chapter)`；`_path_lock` 注册表 refcount+LRU 上界 256（仅淘汰从未持有条目，`_REGISTRY_LOCK` 下维护 refcount）
- [ ] **Step 3-4: 跑 cost/dispatch 相关测试 + Commit** `fix: ledger read-path purity + dir-flock + genre cache key + registry bound (T602/F510/F525/T407/T408/T607, spec37 T2/T3)`

### Task 8: 物化调用点移除 + key-merge（F630/F1113，裁定 b）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:768-782`（`_maybe_materialize_progress` 调用点 :2745/:3060 移除，函数降级为仅 trace 事件非空时执行）`:801-825`（`_auto_rebuild_progress_if_stale` 的重建分支移除，保留 staleness 日志）
- Modify: `src/shenbi/trace/materialize.py`（`materialize_progress` 落盘前读旧 progress.json，非自有键 merge 保留：`out = {**existing_non_derived, **out}`，其中 existing 中 `skills/completed_skill_names/remaining_*` 等 materialize 自有键以新值为准）

- [ ] **Step 1: 红测翻绿**：T0 的 F630 用例（预置 custom_key + DONE 键 → materialize → 键仍在且 DONE 面正确）；新增 `test_no_periodic_materialize_in_loop`（`_maybe_materialize_progress` 在 steps_done%5==0 且 trace 无事件时为 no-op——monkeypatch materialize_progress 断言未被调用）
- [ ] **Step 2-4: 实现 + 跑 chapter_loop/materialize 测试 + Commit** `fix: remove zero-event materialize call sites + key-level merge (F630/F1113 ruling b, spec37 T4)`

### Task 9: durability append helper + F605 回滚（F534/F605）

**Files:**
- Create: `src/shenbi/append_helper.py`（`def append_jsonl(path: Path, record: dict[str, object], *, timestamp_field: str = "timestamp") -> None`：目录 flock 临界区 open("a")+write+flush+fsync；记录自动带 timestamp）
- Modify: `src/shenbi/audit/record.py:36-39`（裸 open 替换为 append_jsonl）
- Modify: `src/shenbi/cost/ledger.py` record 落盘走 append_jsonl
- Modify: `src/shenbi/config/config_coherence.py:200-207`（Phase 2：trail 追加失败 → 回滚 genre-config.json 原内容 + 重抛；try/except 包 trail 循环，except 中 `safe_write(project_dir/"genre-config.json", 原config JSON)` 后 raise）

- [ ] **Step 1: 红测**：`test_append_jsonl_fsync_and_timestamp`（记录含 ISO timestamp；monkeypatch os.fsync 计数>0）；`test_config_trail_failure_rolls_back`（monkeypatch `_append_audit_trail` 第二次 raise → genre-config.json 内容==改动前 + ConfigError 上抛为 OSError 包装）
- [ ] **Step 2-4: 实现 + 跑测 + Commit** `fix: fsync+timestamp append helper + config-trail failure rollback (F534/F605, spec37 T5)`

### Task 10: 豁免 lint + T6 回归翻绿 + 全量门禁

**Files:**
- Create: `tools/lint_bare_writes.py`（grep 清点口径 `open\([^)]*['"](a|w|ab|wb|w\+|r\+)['\"]|mkstemp|os\.fdopen.*w|write_text|shutil\.(move|copy)` 于 src/shenbi/；命中且**同行或上一行**无 `# write-audit-exempt:` 注记 → exit 1 列出；白名单内置：safe_write.py/append_helper.py/compaction.py 自身与既有豁免站点在迁移任务中补注记）
- Modify: `justfile` check 链增 `uv run python tools/lint_bare_writes.py`
- Test: `tests/unit/test_lint_bare_writes.py`

- [ ] **Step 1: 红测**（构造 tmp 目录两文件：一裸 open("a") 无注记 → lint 报；一带注记 → 过）
- [ ] **Step 2: 实现 lint + justfile 接线**；对 src/ 现存命中逐个迁移或补 `# write-audit-exempt: <理由>`（预期豁免：gates 报告写、__pycache__ 无关、compaction 已入 trace 锁）
- [ ] **Step 3: T6 翻绿**：`uv run pytest tests/unit/pipeline/test_concurrency_regression.py -v` → 5/5 PASS（从复现翻转为验证互斥）
- [ ] **Step 4: 全量门禁**：`just check`（契约 lints + ruff/mypy/basedpyright + sync 幂等 + 全量 pytest）exit 0
- [ ] **Step 5: Commit** `test+chore: bare-write exemption lint + T6 regression flip green (spec37 T6)`

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1 并发套件全绿（T605/T601/T604，≤30s） | T1/T10 | `uv run pytest tests/unit/pipeline/test_concurrency_regression.py -v` |
| 2 裸写清单豁免 lint | T10 | `uv run python tools/lint_bare_writes.py` exit 0 |
| 3 物化不抹键/无空壳 | T8 | 同上 F630 用例 + `test_no_periodic_materialize_in_loop` |
| 4 trace seq 无重复/G7 零误报 | T4 | F531 用例 + `uv run pytest tests/unit/trace/ -v` |
| 5 审计轨迹先校验后写 | T9 | `test_config_trail_failure_rolls_back` |
| 6 just check 全绿 | T10 | `just check` exit 0 |

## Out of scope（显式声明）

- cap-raise 二次调用 trace 缺口（spec #36 已知残余，归后续 spec）。
- 空壳 progress.json 的运行时重建（spec v3 已声明 out of scope）。
- F520 重试 token 记账、F519 ledger OSError 防御——spec #36 交付面，本 spec 不动。
