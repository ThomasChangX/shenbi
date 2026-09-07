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
  - `src/shenbi/scoring.py:240-256` `compute_score(dimensions, scores, kill_switch_triggered=False)`——`weight_mismatch` warning 于 total_weight != 100 且非 0 时触发（structlog → configure_logging 后 stderr，capsys 捕获）
  - `src/shenbi/pipeline/dispatch_helper.py:588` `def _input_key(full_path: Path, project_dir: Path) -> str`、`:603` `def _build_skill_prompt(skill, project_dir, prompt, chapter, uses_staging=False, shared_context=None, json_mode=False, path_context=None) -> tuple[str, str, list[str]]`

- [ ] **Step 1: F704 step 回滚站点重写**

删除 `test_cli.py:815-830`（`test_modify_rolls_back_step_index` 类站点，"Simulate MODIFY: step_index should roll back to 1" 测试体内自映射 step_index），替换为走 `cmd_review` 生产路径。**关键**：状态文件名是 `pipeline-state.json`（machine.py:23 `STATE_FILENAME`），且 `cmd_review` 内部 `load_state` 得到自己的 state 副本——断言必须打在 **重新 load 的 state** 上，不得用测试本地旧对象（否则假通过）：

```python
def test_modify_rolls_back_step_index_via_cmd_review(tmp_path, monkeypatch):
    """MODIFY decision rolls back step cursor through the production review path."""
    import argparse

    from shenbi.pipeline import cli as pipeline_cli
    from shenbi.pipeline.machine import load_state, save_state, set_checkpoint
    from shenbi.pipeline.state import CheckpointType, PipelineState, ReviewDecision

    project = tmp_path / "proj"
    (project / "truth").mkdir(parents=True)
    state = PipelineState.default(str(project))
    state.chapter_loop.current_chapter = 3
    state.chapter_loop.step_index = 5
    save_state(project, state)
    set_checkpoint(state, CheckpointType.CHAPTER_MEMO, chapter=3, artifact="plans/chapter-3-plan.md")
    save_state(project, state)

    monkeypatch.setattr(pipeline_cli, "_queue_re_dispatches", lambda *a, **k: None)

    feedback = project / "feedback.md"
    feedback.write_text("Fix the pacing in section 3", encoding="utf-8")

    args = argparse.Namespace(
        project_dir=str(project), decision=ReviewDecision.MODIFY.value, feedback=str(feedback),
    )
    rc = pipeline_cli.cmd_review(args)

    assert rc == 0
    reloaded = load_state(project)  # cmd_review 保存的是它自己的副本——必须重载
    assert reloaded.chapter_loop.step_index == 1  # CHAPTER_STEPS[1] = chapter-planning
    assert reloaded.chapter_loop.modify_feedback == "Fix the pacing in section 3"
```

注：review parser 字段为 `project_dir`（positional）/ `decision`（choices）/ `--feedback`（cli.py:1111-1113）——Namespace 字段名以 parser 定义为准核对。MODIFY 分支的 in-function import `discard_staging` 对无 staging 的 tmp 项目可容忍（`_load_staging_meta` 处理缺失），不需 monkeypatch。回滚映射为 CHAPTER_MEMO→1、STATE_SETTLE→**7**（cli.py:678-686；旧测试自模拟的 6 本身就是错的——pinned-bug 风险点，若暴露真差异按 finding 立案）。

- [ ] **Step 2: F704 prompt 注入站点重写**

删除 `test_cli.py:832-862`（`test_modify_injects_feedback_into_dispatch_prompt`，"Simulate dispatch prompt construction"），替换为：

```python
def test_modify_injects_feedback_into_dispatch_prompt(tmp_path, monkeypatch):
    """Feedback stored in modify_feedback reaches the real dispatch prompt (one-shot)."""
    from shenbi.pipeline import chapter_loop
    from shenbi.pipeline.state import PipelineState

    captured: dict[str, object] = {}

    class FakeResult:  # dispatch_skill 返回 SkillResult 形（success/returncode/stderr 等）
        success = True
        returncode = 0
        stderr = ""
        stdout = "ok"

    def fake_dispatch(skill, project_dir, prompt, *args, **kwargs):  # signature 对齐 dispatch_skill
        captured["skill"] = skill
        captured["prompt"] = prompt
        return FakeResult()

    monkeypatch.setattr(chapter_loop, "dispatch_skill", fake_dispatch)
    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.current_chapter = 3
    state.chapter_loop.step_index = 1  # chapter-planning，dispatched step
    state.chapter_loop.modify_feedback = "Fix the pacing in section 3"

    chapter_loop.run_chapter_step(state, tmp_path)

    assert "Fix the pacing in section 3" in str(captured.get("prompt", ""))
    assert state.chapter_loop.modify_feedback is None  # one-shot consumption
```

注：`run_chapter_step` 在 dispatch 后立即读 `result.success/.returncode/.stderr`（chapter_loop.py:3061+），fake 必须返回 SkillResult 形对象（如上 FakeResult）。若 chapter-planning 因 tmp_path 无产物在 G4 处失败，monkeypatch 该 step 的 G4 入口（最小面）并记 deviation。

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

    t = threading.Thread(target=try_second, daemon=True)  # daemon：失败路径 flock 无超时，防套件挂死
    t.start()
    t.join(timeout=2.0)
    # 先释放锁，再断言（断言失败时不应留下持锁线程阻塞解释器关闭）
    import os

    os.close(fd1)
    if lock1 is not None:
        lock1.unlink()
    t.join(timeout=2.0)  # 释放后再等线程退出，消除 release→assert 间唤醒窗口
    # 在持锁窗口内，第二个获取不得成功返回（此刻 results 只反映持锁窗口内的事实：
    # 记录于 release 前由 try_second 写入——将下面断言改为在 release 前快照）
    assert "second" not in results, f"mutual exclusion broken: {results.get('second')}"```

保留/补一条权限断言测试——**POSIX 下 `_acquire_lock` 走 flock 分支不产 lockfile**，须强制 O_EXCL fallback（monkeypatch `fcntl` 导入失败，同文件已有先例 `test_safe_write_lockfile_fallback_cleanup_posix`），在 fallback 产出 lockfile 后断言 `stat().st_mode & 0o777 == 0o600`，删除 raw `os.open`+`os.chmod` 自建 lockfile 的同义反复体。

- [ ] **Step 4: F702 weight_mismatch 双向断言**

`test_scoring.py:435-444` 删 `or True`。**注意：scoring 用 structlog，且 pytest 下 conftest 恢复 structlog 默认配置（默认打 stdout）——须先 `configure_logging()` 绑定 stderr 再断言**（conftest fixture 会在 teardown 恢复，安全）：

```python
def test_weight_mismatch_warns_and_clean_input_silent(capsys):
    """total_weight != 100 warns on stderr; == 100 stays silent — both pinned."""
    from shenbi.logging import configure_logging
    from shenbi.scoring import compute_score

    configure_logging()  # PrintLoggerFactory(file=sys.stderr)；conftest teardown 恢复
    dims = [{"num": 1, "weight": 60}, {"num": 2, "weight": 50}]  # 110 != 100
    compute_score(dims, {1: 100, 2: 100})
    assert "weight_mismatch" in capsys.read_outerr().err

    dims_ok = [{"num": 1, "weight": 60}, {"num": 2, "weight": 40}]  # == 100
    compute_score(dims_ok, {1: 100, 2: 100})
    assert "weight_mismatch" not in capsys.read_outerr().err
```

- [ ] **Step 5: F728 注入块自证壳清除**

`test_audit_context_cache.py:45-79` "Simulate the injection logic from _build_skill_prompt" 块删除，改为直接调 `_build_skill_prompt(shared_context=ctx)` 并断言 user_prompt 含注入字段、auditor 不需重读（对齐 `tests/unit/pipeline/test_dispatch_helper_read_suppression.py` 的真实 ctx 构造方式——复用其 fixture/构造代码，不新建 mock）。

- [ ] **Step 6: F729 期望键集 pin**

`test_dispatch_helper_keys.py:38-40` 恒真守卫改为硬编码期望列表 **并驱动真实注入块**（`_build_skill_prompt(shared_context=ctx)`，ctx 用 `build_shared_audit_context` 或复用 `tests/unit/pipeline/test_dispatch_helper_read_suppression.py` 的真实构造）：

```python
EXPECTED_INJECTION_KEYS = [
    "world/rules.md",             # C28 R1 (F312): canonical, 旧 truth/ 键是 phantom
    "truth/character_matrix.md",
    "style/style_profile.md",     # C28 R1 (F312): canonical
    "truth/pending_hooks.md",
]
def test_injection_block_keys_are_pinned(tmp_path):
    from tests.unit.pipeline.test_dispatch_helper_read_suppression import <ctx 构造 helper>

    ctx = <真实 SharedAuditContext 构造（复用 read_suppression 测试的写法）>
    _, user_prompt, _ = _build_skill_prompt(
        <chapter-planning skill>, tmp_path, "do it", 1, shared_context=ctx,
    )
    for key in EXPECTED_INJECTION_KEYS:
        assert key in user_prompt, f"injection key drifted: {key}"
```

生产注入键源为 dispatch_helper.py:707-727 `_INJECT_FROM_CACHE`（`world/rules.md`、`truth/character_matrix.md`、`style/style_profile.md`、`truth/pending_hooks.md`）——期望列表必须与该处对齐，`_INJECT_FROM_CACHE` 键漂移即红。`_input_key` 本体的相对路径语义另以 `assert _input_key(tmp_path / rel, tmp_path) == rel` 保持覆盖。

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
- Modify: `tests/unit/pipeline/test_bridge_tracker.py:13-24`、`tests/unit/gates/g4/test_state_settling.py:166-167`（F712）
- Modify: `tests/unit/gates/test_g6.py:637-640`（F713）
- Modify: `tests/unit/pipeline/test_field_filtering.py`（F719）

- [ ] **F703**：`assert len(result) >= 0` → `assert result == ["H001"]`（注释已声明只返回 H001；以实际 `_extract_hook_deliverables` 行为核对后 pin 精确值）
- [ ] **F705**：改写真实 `tests/tiers/deps.json` 的测试体整体换 `tmp_path` 复制（`shutil.copy` 源文件到 tmp）后操作；断言加"源文件未变"校验（`git status` 干净由验收 5 兜底）
- [ ] **F712**：两文件共 3 处 `pytest.skip("... not yet created")` 死守卫删除，直接执行；若执行暴露真失败按 pinned-bug 政策立案不回退
- [ ] **F713**：`if g610 is not None: assert ...` → `assert g610 is not None, "D16 check must exist"; assert g610["s"] != "SKIP"`（检查缺失即 FAIL）
- [ ] **F719**：docstring/测试名改为如实描述 `filter_to_fields` 本体单测（删"dispatch_helper read loop delegates"虚假集成声称），文件头注释同步
- [ ] 运行：`uv run pytest tests/unit/pipeline/test_review_checklist.py tests/unit/test_scoring.py tests/unit/pipeline/test_bridge_tracker.py tests/unit/gates/g4/test_state_settling.py tests/unit/gates/test_g6.py tests/unit/pipeline/test_field_filtering.py -q` → 全 PASS，skip 数较改前下降
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
- [ ] **F716**：7 站点逐一收紧（spec 标"8 存活"中 test_g2.py 站点已消失，实际处置 7 处）——每处改单一确定状态断言或注明 "gate must complete, not raise" 显式意图（test_g5.py:221、cost/test_report.py:34、test_parallel_dispatch.py:82、test_context_curation.py:30、test_scoring_anti_collapse.py:98-99、test_phase_runner.py:869-870、test_g0.py:215-216；F767 站点不碰）
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
  - `uv run pytest -n auto -m "not last"` 全绿 + `just test` 全绿，skip 数 == 526（基线持平或更低）
  - F705 修复后测试运行前后 `git status` 干净
  - `uv run pytest tests/unit/pipeline/test_dispatch_helper_read_suppression.py tests/pipeline/test_audit_context_cache.py --cov=src/shenbi/pipeline/dispatch_helper --cov-report=term` 中注入块行（dispatch_helper.py:707-727）覆盖 >0（验收 6）
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
| 6. 注入块覆盖不回退 | T1(F728)+T5 | `--cov=src/shenbi/pipeline/dispatch_helper` 注入块行 :707-727 覆盖 >0 |
| 7. 直测对象生产可达 | T1-T4 | basedpyright 门（just check 内含） |
