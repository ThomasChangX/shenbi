# C14 弱断言/自证测试修复 Implementation Plan（spec #52）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 spec #52（C14）的 25 条存活弱断言/自证测试全部改写为真实生产行为断言，生产代码零改动（红灯验证的临时破坏不落库）。

**Architecture:** 全部改动限于 tests/。五个 P1 自证壳改为走生产入口（`cmd_review` / `run_chapter_step`+monkeypatch `dispatch_skill` 捕获 prompt / `_build_skill_prompt` / `_input_key` 期望键集 pin / `_acquire_lock` 真实互斥）；P2/M 批量按 finding 逐条机械改写；末 task 跑红灯验证与验收证据。

**Tech Stack:** pytest（markers: unit/integration/property/last）、hypothesis、monkeypatch、tmp_path、caplog。运行一律 `uv run pytest`（与 CI `uv run --frozen` 同构）。

## Global Constraints

- 生产代码零改动（src/shenbi/ 不动；红灯验证临时改→还原，不 commit）
- 每条改写后的断言必须满足：真实输入 → 真实生产调用 → 对真实输出断言
- skip 数不增（基线 526）；`pytest -n auto -m "not last"` 全绿
- 并发类测试用 barrier/event 确定性同步，禁 sleep
- fixture 只能引用 tests/fixtures/ 真实产物（G0.9）
- commit 用 conventional commits，显式列文件路径（禁 git add -A）
- 每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审）

---

### Task 1: T1 P1 五连修复——自证壳重写（F704/F701/F702/F728/F729）

**Files:**
- Modify: `tests/unit/pipeline/test_cli.py:815-862`（F704 两站点）
- Modify: `tests/unit/test_safe_write.py:62-100`（F701）
- Modify: `tests/unit/test_scoring.py:435-444`（F702）
- Modify: `tests/pipeline/test_audit_context_cache.py:45-79`（F728）
- Modify: `tests/pipeline/test_dispatch_helper_keys.py`（F729）

**Interfaces:**
- Consumes（生产，零改动）:
  - `src/shenbi/pipeline/cli.py:617` `def cmd_review(args: argparse.Namespace) -> int`（MODIFY 回滚映射在 :678-686）
  - `src/shenbi/pipeline/chapter_loop.py:2615` `def run_chapter_step(state: PipelineState, project_dir: Path | str) -> bool`（反馈注入块 :3033-3039）；`dispatch_skill` 从 `shenbi.pipeline.chapter_loop` 名字空间 monkeypatch（已 import 于 :58）
  - `src/shenbi/pipeline/machine.py:69/90` `set_checkpoint` / `clear_checkpoint(state, decision)`
  - `src/shenbi/safe_write.py:113` `def _acquire_lock(path: Path) -> tuple[int, Path | None]`
  - `src/shenbi/scoring.py:240-256` `compute_score(dimensions, scores, kill_switch_triggered=False)`——`weight_mismatch` warning 于 total_weight != 100 且非 0 时触发（caplog WARNING 捕获）
  - `src/shenbi/pipeline/dispatch_helper.py:588` `def _input_key(full_path: Path, project_dir: Path) -> str`、`:603` `def _build_skill_prompt(skill, project_dir, prompt, chapter, uses_staging=False, shared_context=None, json_mode=False, path_context=None) -> tuple[str, str, list[str]]`

- [ ] **Step 1: F704 step 回滚站点重写**

删除 `test_cli.py:815-830`（`test_modify_rolls_back_step_index` 类站点，"Simulate MODIFY: step_index should roll back to 1" 测试体内自映射 step_index），替换为走 `cmd_review` 生产路径：

```python
def test_modify_rolls_back_step_index_via_cmd_review(tmp_path, monkeypatch):
    """MODIFY decision rolls back step cursor through the production review path."""
    import argparse

    from shenbi.pipeline import cli as pipeline_cli
    from shenbi.pipeline.machine import set_checkpoint
    from shenbi.pipeline.state import CheckpointType, PipelineState, ReviewDecision

    project = tmp_path / "proj"
    (project / "truth").mkdir(parents=True)
    state = PipelineState.default(str(project))
    state.chapter_loop.current_chapter = 3
    state.chapter_loop.step_index = 5
    state_save = project / "state.json"
    state.save(str(state_save))
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=3, artifact="plans/chapter-3-plan.md")
    state.save(str(state_save))

    monkeypatch.setattr(pipeline_cli, "_commit_staging_for_checkpoint", lambda *a, **k: None)
    monkeypatch.setattr(pipeline_cli, "_queue_re_dispatches", lambda *a, **k: None)

    feedback = project / "feedback.md"
    feedback.write_text("Fix the pacing in section 3", encoding="utf-8")

    args = argparse.Namespace(
        project_dir=str(project), decision=ReviewDecision.MODIFY.value, feedback=str(feedback),
    )
    # 依照 cmd_review 实际 argparse 字段名调整（先 grep add_argument 核对）
    rc = pipeline_cli.cmd_review(args)

    assert rc in (0, None)
    assert state.chapter_loop.step_index == 1  # CHAPTER_STEPS[1] = chapter-planning
    assert state.chapter_loop.modify_feedback == "Fix the pacing in section 3"
```

注：`cmd_review` 的 argparse 字段集先 `grep -n "add_argument" src/shenbi/pipeline/cli.py` 核对后对齐；若 cmd_review 需要 review 子命令分发（`shenbi-pipeline review`），字段名以其 review parser 为准。

- [ ] **Step 2: F704 prompt 注入站点重写**

删除 `test_cli.py:832-862`（`test_modify_injects_feedback_into_dispatch_prompt`，"Simulate dispatch prompt construction"），替换为：

```python
def test_modify_injects_feedback_into_dispatch_prompt(tmp_path, monkeypatch):
    """Feedback stored in modify_feedback reaches the real dispatch prompt (one-shot)."""
    from shenbi.pipeline import chapter_loop
    from shenbi.pipeline.state import PipelineState

    captured: dict[str, object] = {}

    def fake_dispatch(skill, project_dir, prompt, *args, **kwargs):  # signature 对齐 dispatch_skill
        captured["skill"] = skill
        captured["prompt"] = prompt
        return "ok"

    monkeypatch.setattr(chapter_loop, "dispatch_skill", fake_dispatch)
    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.current_chapter = 3
    state.chapter_loop.step_index = 1  # chapter-planning，dispatched step
    state.chapter_loop.modify_feedback = "Fix the pacing in section 3"

    chapter_loop.run_chapter_step(state, tmp_path)

    assert "Fix the pacing in section 3" in str(captured.get("prompt", ""))
    assert state.chapter_loop.modify_feedback is None  # one-shot consumption
```

注：`dispatch_skill` 在 chapter_loop 中的调用形参先 `grep -n "dispatch_skill(" src/shenbi/pipeline/chapter_loop.py` 核对并对齐 fake 签名；`run_chapter_step` 前置（G4/重试等）若对 tmp_path 状态有要求，用 `PipelineState.default` + 最小 chapter 配置满足；若 step 1 的 chapter-planning 因 contract 缺失抛错，monkeypatch 该 step 的 G4 校验入口（最小面）并记录 deviation。

- [ ] **Step 3: F701 lockfile 互斥重写**

`test_safe_write.py:62-100` 的两个 chmod 同义反复测试改为真实 `_acquire_lock` 互斥验证：

```python
def test_lockfile_mutual_exclusion_via_acquire_lock(tmp_path):
    """Second _acquire_lock on a held O_EXCL lockfile blocks until release."""
    import threading

    from shenbi.safe_write import _acquire_lock

    target = tmp_path / "data.json"
    target.write_text("{}", encoding="utf-8")
    fd1, lock1 = _acquire_lock(target)
    assert fd1 >= 0
    results: dict[str, object] = {}

    def try_second():
        try:
            fd2, lock2 = _acquire_lock(target)
            results["second"] = (fd2, lock2)
            import os

            os.close(fd2)
            if lock2 is not None:
                lock2.unlink()
        except Exception as exc:  # noqa: BLE001 - record for assertion
            results["error"] = exc

    t = threading.Thread(target=try_second)
    t.start()
    t.join(timeout=2.0)
    # 在持锁窗口内，第二个获取不得成功返回
    assert "second" not in results, f"mutual exclusion broken: {results['second']}"
    import os

    os.close(fd1)
    if lock1 is not None:
        lock1.unlink()
```

保留/补一条权限断言测试（走真实 `_acquire_lock` 产出的 lockfile，断言 `stat().st_mode & 0o777 == 0o600`），删除 raw `os.open`+`os.chmod` 自建 lockfile 的同义反复体。

- [ ] **Step 4: F702 weight_mismatch 双向断言**

`test_scoring.py:435-444` 删 `or True`，改为：

```python
def test_weight_mismatch_warns_and_clean_input_silent(caplog):
    """total_weight != 100 warns; == 100 stays silent — both directions pinned."""
    import logging

    from shenbi.scoring import compute_score

    dims = [{"num": 1, "weight": 60}, {"num": 2, "weight": 50}]  # 110 != 100
    with caplog.at_level(logging.WARNING):
        compute_score(dims, {1: 100, 2: 100})
    assert any("weight_mismatch" in r.getMessage() for r in caplog.records)

    caplog.clear()
    dims_ok = [{"num": 1, "weight": 60}, {"num": 2, "weight": 40}]  # == 100
    with caplog.at_level(logging.WARNING):
        compute_score(dims_ok, {1: 100, 2: 100})
    assert not any("weight_mismatch" in r.getMessage() for r in caplog.records)
```

- [ ] **Step 5: F728 注入块自证壳清除**

`test_audit_context_cache.py:45-79` "Simulate the injection logic from _build_skill_prompt" 块删除，改为直接调 `_build_skill_prompt(shared_context=ctx)` 并断言 user_prompt 含注入字段、auditor 不需重读（对齐 `tests/unit/pipeline/test_dispatch_helper_read_suppression.py` 的真实 ctx 构造方式——复用其 fixture/构造代码，不新建 mock）。

- [ ] **Step 6: F729 期望键集 pin**

`test_dispatch_helper_keys.py:38-40` 恒真守卫改为硬编码期望列表：

```python
EXPECTED_KEYS = [
    "truth/world_rules.md",
    "truth/character_matrix.md",
    "truth/style_profile.md",
    "truth/pending_hooks.md",
]
def test_injection_keys_are_canonical(tmp_path):
    from shenbi.pipeline.dispatch_helper import _input_key

    for rel in EXPECTED_KEYS:
        assert _input_key(tmp_path / rel, tmp_path) == rel
```

期望列表以当前 main 生产 SharedAuditContext 实际注入文件集为准（`grep -n "shared_context" src/shenbi/pipeline/dispatch_helper.py` 核对），key 漂移即红。

- [ ] **Step 7: 运行本文件测试**

Run: `uv run pytest tests/unit/pipeline/test_cli.py tests/unit/test_safe_write.py tests/unit/test_scoring.py tests/pipeline/test_audit_context_cache.py tests/pipeline/test_dispatch_helper_keys.py -q`
Expected: 全 PASS，无新增 skip。

- [ ] **Step 8: Commit + audit**

```bash
git add tests/unit/pipeline/test_cli.py tests/unit/test_safe_write.py tests/unit/test_scoring.py tests/pipeline/test_audit_context_cache.py tests/pipeline/test_dispatch_helper_keys.py
git commit -m "test: C14 T1 — rewrite five self-proving shells to production-path assertions (F704/F701/F702/F728/F729)"
```

产出 `.superpowers/sdd/audit-T1.md`（fresh-context 重审）后方可进 Task 2。

---

### Task 2: T2a P2 批量改写之一（F703/F705/F712/F713/F719）

**Files:**
- Modify: `tests/unit/pipeline/test_review_checklist.py:207-209`（F703）
- Modify: `tests/unit/test_scoring.py:517-556`（F705）
- Modify: `tests/test_bridge_tracker.py:13-24`、`tests/unit/gates/g4/test_state_settling.py:166-167`（F712）
- Modify: `tests/unit/gates/test_g6.py:637-640`（F713）
- Modify: `tests/unit/pipeline/test_field_filtering.py`（F719）

- [ ] **F703**：`assert len(result) >= 0` → `assert result == ["H001"]`（注释已声明只返回 H001；以实际 `_extract_hook_deliverables` 行为核对后 pin 精确值）
- [ ] **F705**：改写真实 `tests/tiers/deps.json` 的测试体整体换 `tmp_path` 复制（`shutil.copy` 源文件到 tmp）后操作；断言加"源文件未变"校验（`git status` 干净由验收 5 兜底）
- [ ] **F712**：两文件共 3 处 `pytest.skip("... not yet created")` 死守卫删除，直接执行；若执行暴露真失败按 pinned-bug 政策立案不回退
- [ ] **F713**：`if g610 is not None: assert ...` → `assert g610 is not None, "D16 check must exist"; assert g610["s"] != "SKIP"`（检查缺失即 FAIL）
- [ ] **F719**：docstring/测试名改为如实描述 `filter_to_fields` 本体单测（删"dispatch_helper read loop delegates"虚假集成声称），文件头注释同步
- [ ] 运行：`uv run pytest tests/unit/pipeline/test_review_checklist.py tests/unit/test_scoring.py tests/test_bridge_tracker.py tests/unit/gates/g4/test_state_settling.py tests/unit/gates/test_g6.py tests/unit/pipeline/test_field_filtering.py -q` → 全 PASS，skip 数较改前下降
- [ ] Commit `test: C14 T2a — concrete-value assertions, tmp_path isolation, dead-skip removal (F703/F705/F712/F713/F719)`（显式列 6 文件）→ 产出 audit-T2.md

---

### Task 3: T2b P2 批量改写之二（F731/F733/F734/F735/F743/F744/F739/F740）

**Files:**
- Modify: `tests/integration/test_docs_accuracy.py:64,85,94,102`（F731）
- Modify: `tests/gates/test_gate_manifest.py:15`（F733）
- Modify: `tests/integration/test_gate_cli.py:469-471`（F734）
- Modify: `tests/pipeline/test_crash_recovery.py:144-159`（F735）
- Modify: `tests/unit/pipeline/test_state_heal.py`（F743）
- Modify: `tests/pipeline/test_budgeted_truncate.py:31`（F744）
- Modify: `tests/pressure-tests/prompts/snapshot-skip-pressure.md`（F739）
- Modify: `tests/pressure-tests/prompts/audit-skipping-pressure.md`（F740）

- [ ] **F731**：3 处死 skip 删除直接执行；:64 条件 skip 核对条件真伪后处置（真条件保留并注明）
- [ ] **F733**：`@pytest.mark.last` 错标移除（该测试应入快测套件）；历史 list 分支补一条真实行为测试（构造 list 形态 gate result 走 `record_and_retrieve`，断言等价）——若分支确为死代码则记 deviation 移交（不删生产）
- [ ] **F734**：`assertIn(state["state"], ["scored","finalized"])` → pin 单一期望值（以 `cmd_finalize` 生产语义核对：finalize 后 state 应为确定值）
- [ ] **F735**：TestEmergencyCleanup 两测试补真实断言（cleanup 后 staging 目录清空/隔离区内容落位）；删除对生产从不调用的 `state.save` side_effect 幻设
- [ ] **F743**：补 `current_step == CHAPTER_STEPS[step_index]` 一致性校验测试（真实 heal 路径：构造错位 state → heal → 断言对齐）；夹具错位索引修正
- [ ] **F744**：`"chapter" in str(...)` 近恒真 → pin 精确键/结构断言（截断测试已由 #43 覆盖，只处理恒真面）
- [ ] **F739/F740**：提示词文本与 `src/shenbi/audit/snapshot.py` 记录级差分语义、`chapter_loop.py:461 CASCADABLE_AUDITS` 级联语义对齐改写（删"完整副本/全 33 维必跑"表述，改为差分/可级联真实语义）
- [ ] 运行：`uv run pytest tests/integration/test_docs_accuracy.py tests/gates/test_gate_manifest.py tests/integration/test_gate_cli.py tests/pipeline/test_crash_recovery.py tests/unit/pipeline/test_state_heal.py tests/pipeline/test_budgeted_truncate.py -q` → 全 PASS；skip 数不增
- [ ] Commit `test: C14 T2b — dead skips, marker fix, pinned states, heal consistency, prompt semantics (F731/F733-F735/F743/F744/F739/F740)` → 产出 audit-T3.md

---

### Task 4: M 级批量清理（F715/F716/F718/F745/F746/F747/F748）

**Files:**
- Modify: `tests/unit/test_plugins_generate.py:53-72`（F715）
- Modify: 8 站点（F716，清单见 spec :50）
- Modify: `tests/unit/test_phase_runner_property.py:48-52`（F718）
- Modify: `tests/pipeline/test_parallel_steps.py:16-25,89-92`（F745）
- Modify: `tests/pipeline/test_title_gate_integration.py:38-46,201-218`（F746）
- Modify: `tests/property/contracts/test_registry_consistency.py:42-45`（F747）
- Modify: `tests/pipeline/test_audit_cascading.py`（F748）

- [ ] **F715**：MASTER_PATH 手工保存/恢复改 `monkeypatch.setattr(gen_mod, "MASTER_PATH", tmp_copy)`（异常安全由 monkeypatch 保证）+ 名实对齐
- [ ] **F716**：8 站点逐一收紧——每处改单一确定状态断言或注明 "gate must complete, not raise" 显式意图（test_g5.py:221、cost/test_report.py:34、test_parallel_dispatch.py:82、test_context_curation.py:30、test_scoring_anti_collapse.py:98-99、test_phase_runner.py:869-870、test_g0.py:215-216；F767 站点不碰）
- [ ] **F718**：`seed` 形参真实 `st.seed(...)` draw 或删形参（`data.draw` 或直接去参）
- [ ] **F745**：`executed_concurrently` 用 `threading.Barrier(2)` 在 fake dispatch 内交错验证真并发（两线程都到 barrier 才放行，超时即 FAIL）；single-writer 守卫优先行为验证（并发两写 → 串行化结果一致），否定性主张保留文本级则注明论证
- [ ] **F746**：`test_returns_empty_for_missing_file` 改名 `test_raises_for_missing_file`；short title 测试补过 `_run_g4_checks` 真实 gate 断言
- [ ] **F747**：`@given(st.data())` 改真实 draw（`data.draw(st.sampled_from(...))` 进入断言）或删装饰器
- [ ] **F748**：删"Wait, 1 from ch1..."困惑注释；补 unknown-skill（不在任何清单）分支真实测试
- [ ] 运行：`uv run pytest tests/unit/test_plugins_generate.py tests/unit/gates/test_g5.py tests/unit/cost/test_report.py tests/unit/pipeline/test_parallel_dispatch.py tests/unit/pipeline/test_context_curation.py tests/unit/test_scoring_anti_collapse.py tests/unit/test_phase_runner.py tests/unit/gates/test_g0.py tests/unit/test_phase_runner_property.py tests/pipeline/test_parallel_steps.py tests/pipeline/test_title_gate_integration.py tests/property/contracts/test_registry_consistency.py tests/pipeline/test_audit_cascading.py -q` → 全 PASS
- [ ] Commit `test: C14 T4 — M-tier cleanup: fixture safety, tightened assertions, real draws, barrier concurrency (F715/F716/F718/F745-F748)` → 产出 audit-T4.md

---

### Task 5: T3 红灯验证 + 验收证据汇总

**Files:** 无新改动（临时破坏→还原，不落库；证据进 PR 描述与 progress.md）

- [ ] 对 T1-T4 触及的每个测试文件执行 1 处"破坏生产 → 红 → 还原"（如：compute_score 改 warning 为 silent → F702 测试红；_input_key 改返回 basename → F729 红；cmd_review 回滚映射改错值 → F704 红）。每处记录：破坏点、变红测试、还原确认（`git diff src/` 空）
- [ ] 验收命令逐条跑并记录：
  - `grep -rn "or True" tests/ --include="*.py"` → 仅 allowlist 1 命中
  - `grep -rn "assert len(.*) >= 0" tests/` → 零命中
  - `grep -n "from shenbi\|import shenbi" tests/pipeline/test_audit_context_cache.py tests/unit/pipeline/test_cli.py` → 非空 + 人工复查无重实现块
  - `uv run pytest -n auto -m "not last"` 全绿，skip 数 == 526（基线持平或更低）
  - F705 修复后测试运行前后 `git status` 干净
- [ ] Commit（如有 meta 记录文件；否则零 commit，证据直接进 progress.md）→ 产出 audit-T5.md

---

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. or True / >=0 grep | T1(F702)/T2a(F703)+T5 | grep 命令输出 |
| 2. 无重实现块 + import | T1(F704/F728)+T5 | grep + 人工复查 |
| 3. 红灯验证记录 | T5 | PR 描述 |
| 4. 全绿无新 skip | T5 | pytest 摘要 |
| 5. deps.json 不被改写 | T2a(F705)+T5 | git status |
| 6. 注入块覆盖不回退 | T1(F728) | pytest 相关文件 PASS |
| 7. 直测对象生产可达 | T1-T4 | basedpyright 门（just check 内含） |
