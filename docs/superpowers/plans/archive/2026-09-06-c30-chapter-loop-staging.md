# C30 章循环状态机与 staging 生命周期修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec #44（C30）修订后的 R1-R5：staging 清理谓词定稿、resume 游标锚定、步骤表去魔法索引/装配后移、SCR 缓存失效、审计波中途保存点。

**Architecture:** 全部为 infra task（涉及 `src/shenbi/pipeline/` 核心状态机、crash_recovery 锁协议、staging 提交路由），由协调者亲自实现（SDD 阶段 6 leaf/infra 分流规则）。谓词信源扩展 `checkpoint.py` 既有 `.staging-meta.json` 登记（不新建平行设施）；R1 叠加在 spec #37 one-shot latch/锁协议之上，不破坏其不变量。

**Tech Stack:** Python 3.11+，pathlib/json/structlog，pytest（`uv run pytest`），gate CLI（`shenbi-validate`）。

## Global Constraints

- `src/shenbi/` 禁 `print()`（structlog）；文件 I/O 用 `pathlib.Path`；gate 检查器幂等纯函数。
- 新状态/事件字面量以 `Literal` 定义于 `src/shenbi/contracts/enums.py`（`tools/lint_status_strings.py` 红即 Critical）。
- 原子写经 `src/shenbi/safe_write.py`（`safe_write` 等设施）；atexit 路径不得盲取 `WriteLock`。
- fixtures 只能引用 `tests/fixtures/` 真实产物（G0.9）；崩溃注入用确定性故障 hook，非真实信号 kill。
- 验证命令一律 `uv run pytest ...`（与 CI `uv run --frozen` 同构）。
- Conventional commits；每个 task commit 显式列文件路径（禁 `git add -A`）。
- Scope 裁决：T102/F1110/F305/F1153/F379 已在 main 修复，本 plan 不重复实现；F311 零消费面留 C37 裁决。
- **测试落点裁决（plan 审查 C1）**：本仓无 `tests/integration/pipeline/` 目录——pipeline 集成测试既有惯例落点为 `tests/pipeline/`，spec 验证命令中的 `tests/integration/pipeline/` 一律映射为 `tests/pipeline/`；同理 spec 的 `tests/unit/pipeline/ -k steps_migration` 映射为 `tests/pipeline/test_resume_anchor.py -k migration`（均记 spec-deviations）。R1/R2/R5 的链路级用例（确定性崩溃注入）落在对应 task 的测试文件内，标记 T2 层级。spec R1 正文「经 `write_safety` 原子写」的设施实名 `src/shenbi/safe_write.py`（`safe_write`），随 T1 spec-deviations 记一行。

## 现状签名（从源码复制，2026-09-06 main HEAD）

```python
# checkpoint.py
STAGING_DIR = "staging"
def staging_path(project_dir: Path | str, target_path: str) -> Path
def _load_staging_meta(project_dir: Path) -> dict[str, dict[str, str]]   # staging/.staging-meta.json
def commit_staging(project_dir: Path | str, target_paths: list[str]) -> list[Path]
def clear_staging(project_dir: Path | str) -> None                       # :130，rmtree 整目录

# crash_recovery.py（spec #37 协议已在此）
_cleanup_done: bool                       # one-shot latch
def _emergency_cleanup(project_dir: Path | None = None, state: PipelineState | None = None) -> None
# 步骤 4 现状：无条件 clear_staging(project_dir)（F318 根因）

# machine.py
def clear_checkpoint(state: PipelineState, decision: ReviewDecision) -> None   # :90，无 NONE 防御（F338）
def set_checkpoint(state, checkpoint_type, chapter=None, artifact=None, context=None, options=None) -> None

# cli.py
def _commit_staging_for_checkpoint(project_dir: Path, cp: CheckpointData) -> None   # :363
def cmd_review(args: argparse.Namespace) -> int   # MODIFY 块 :641-659：先 commit 再回退 step_index 重派（F323）
def cmd_resume(args: argparse.Namespace) -> int   # :791，checkpoint_history[-1] 猜测（F371）

# chapter_loop.py
class ChapterStep:  # step_num/skill/name/step_type/conditional/checkpoint/uses_staging/calls_context_assembly/is_audit/output_path
CHAPTER_STEPS: list[ChapterStep]          # :139；step-2 "shenbi-chapter-planning" calls_context_assembly=True（F358/T1602）
_FORESHADOWING_LIFECYCLE_IDX = 6          # :2299 字面量（F357）；_FIRST_AUDIT_IDX :291 为推导式先例

# scr_extractor.py
def extract_scr(project_dir: Path, chapter: int) -> StructuredChapterRepresentation   # :435，缓存无失效（F310）

# state.py
class ChapterLoopStateData:   # :184，含 current_chapter/current_step/step_index/chapter_states
class ChapterState: steps_done: list[str] = field(default_factory=list)   # :141（F797 旧代步名）
def add_step_done(...)   # state.py:222 线程安全追加（幂等）

# parallel_dispatch.py
def dispatch_reviews_parallel(...)   # :150，无中途保存点（F377）

# enums.py
# Literal 定义唯一信源：src/shenbi/contracts/enums.py
```

---

### Task 1: R1 · staging 清理谓词 + 紧急清理保护 + MODIFY 显式 discard

**Files:**
- Modify: `src/shenbi/pipeline/checkpoint.py`
- Modify: `src/shenbi/pipeline/crash_recovery.py:181-189`
- Modify: `src/shenbi/pipeline/cli.py:636-659`
- Modify: `src/shenbi/pipeline/machine.py`（Step 5 联动如触）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（Step 5 set_checkpoint 调用点标记）
- Test: `tests/pipeline/test_staging_lifecycle.py`（新建）

**Interfaces:**
- Produces（后续 task 无消费方；对外行为变更）：
  - `mark_staging_checkpointed(project_dir: Path, targets: list[str]) -> None`（checkpoint.py 新增）
  - `staging_checkpointed_targets(project_dir: Path) -> set[str]`（checkpoint.py 新增）
  - `clear_staging(project_dir: Path | str, *, preserve_checkpointed: bool = False) -> None`（签名扩展，默认值保旧调用方兼容）
  - `discard_staging(project_dir: Path, reason: str) -> None`（checkpoint.py 新增，审计日志走 structlog `staging_discarded`）

**复杂度:** infra · **test_kind:** tdd_red_green · **层级:** T1（单元，fixture 驱动）+ 现有 `tests/pipeline/test_crash_recovery.py` 回归

- [x] **Step 1: 写失败测试**（`tests/pipeline/test_staging_lifecycle.py`，fixture 输入用 `tests/fixtures/chapter-plan-example.md` 复制构造 project_dir——产物为真实 skill 输出，符合 G0.9）：

```python
"""C30 R1 staging lifecycle: checkpoint-preservation predicate + MODIFY discard."""
import shutil
from pathlib import Path
import pytest
from shenbi.pipeline.checkpoint import (
    clear_staging, commit_staging, discard_staging,
    mark_staging_checkpointed, staging_checkpointed_targets, staging_path,
)

@pytest.fixture
def project(tmp_path: Path) -> Path:
    plan = tmp_path / "staging" / "plans"
    plan.mkdir(parents=True)
    src = Path("tests/fixtures/chapter-plan-example.md")
    (plan / "chapter-1-plan.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "staging" / "plans" / "chapter-1-plan-decisions.json").write_text(
        Path("tests/fixtures/decisions/valid-chapter-decisions.json").read_text(encoding="utf-8"),
        encoding="utf-8")   # 真实 decisions 产物（G0.9），不手写
    return tmp_path

def test_uncheckpointed_staging_cleared_emergency(project):
    clear_staging(project, preserve_checkpointed=True)
    assert not staging_path(project, "plans/chapter-1-plan.md").exists()   # 从未进入 checkpoint → 清

def test_checkpointed_staging_survives_emergency(project):
    targets = ["plans/chapter-1-plan.md", "plans/chapter-1-plan-decisions.json"]
    mark_staging_checkpointed(project, targets)
    clear_staging(project, preserve_checkpointed=True)
    assert staging_path(project, "plans/chapter-1-plan.md").exists()       # 已进入 checkpoint → 保留
    assert staging_checkpointed_targets(project) == set(targets)

def test_marker_survives_new_process_simulated_crash(project):
    # 谓词跨进程：重载 meta（新进程视角）后标记仍在
    mark_staging_checkpointed(project, ["plans/chapter-1-plan.md"])
    assert staging_checkpointed_targets(project) == {"plans/chapter-1-plan.md"}

def test_reject_clears_everything_including_checkpointed(project):
    mark_staging_checkpointed(project, ["plans/chapter-1-plan.md"])
    clear_staging(project)   # 显式决策路径不保留
    assert not (project / "staging").exists()   # 整目录移除（含 .staging-meta.json），非"只删文件留目录"

def test_discard_staging_logs_and_clears(project):
    discard_staging(project, reason="modify")
    assert not (project / "staging").exists()

def test_commit_removes_checkpoint_marker(project):
    mark_staging_checkpointed(project, ["plans/chapter-1-plan.md"])
    commit_staging(project, ["plans/chapter-1-plan.md"])
    assert "plans/chapter-1-plan.md" not in staging_checkpointed_targets(project)
    assert (project / "plans" / "chapter-1-plan.md").exists()
```

- [x] **Step 2: 跑测确认失败**：`uv run pytest tests/pipeline/test_staging_lifecycle.py -q --no-cov` → Expected FAIL（`mark_staging_checkpointed` 不存在）
- [x] **Step 3: 实现**（checkpoint.py）：`mark_staging_checkpointed` 读 `_load_staging_meta`、给每个 target 写 `{"checkpointed": "true", **既有键}`、经 `safe_write` 原子回写 `.staging-meta.json`；`staging_checkpointed_targets` 返回键集合过滤 checkpointed；`clear_staging` 加 keyword 参数——`preserve_checkpointed=True` 时只删未标记文件与空目录（保留 `.staging-meta.json` 中标记条目）；`commit_staging` 成功后从 meta 删该 target 的 checkpointed 标记；`discard_staging(project, reason)` = `log.info("staging_discarded", reason=reason, targets=sorted(残留 targets))` + 全清
- [x] **Step 4: crash_recovery.py 步骤 4 改**：`clear_staging(project_dir)` → `clear_staging(project_dir, preserve_checkpointed=True)`，日志事件改 `staging_cleared_preserving_checkpointed`（保留条目数入 log）——不触锁（clear_staging 本无锁），latch 逻辑不动。顺手把该段既有 `except Exception: pass` 吞错改为 `except Exception as e: logger.warning("emergency_staging_clear_failed", error=str(e))`（best-effort 语义不变，可观测）
- [x] **Step 5: set_checkpoint 联动**（machine.py）：`set_checkpoint` 时对 `uses_staging` 步骤的产物调用 `mark_staging_checkpointed`？——不可行（machine 无产物清单）。改为：`cli.py _commit_staging_for_checkpoint` 与 `chapter_loop.py` auto-commit 路径在 **checkpoint 设置处**（`set_checkpoint` 调用点）以 `staged_decisions_targets` + output_path 构造 target 清单并标记。实际落点：`chapter_loop.py` 调 `set_checkpoint(CheckpointType.CHAPTER_MEMO/STATE_SETTLE, ...)` 的两处，标记 `staging/` 下当前章全部 staged 文件（用 `staged_decisions_targets` + step output_path）。**实现时 grep `set_checkpoint(` 全部调用点（全仓约 19 处：chapter_loop 7 + closure/error_handler/genesis/cli/triggers），产出裁决表记入 spec-deviations `### T1`**：仅 `uses_staging` 步的 checkpoint 标记；与 T2 的 `consumed` 字段（clear_checkpoint 侧）正交不冲突——T2 改 history 条目写侧，T1 改 staging 标记侧，无共享行
- [x] **Step 5b: 链路级集成用例（T2 层级，spec R1 验收「approve 后 sidecar 入 committed truth」）**：在 `test_staging_lifecycle.py` 追加——构造 staged plan+sidecar → `mark_staging_checkpointed` → 构造 `CheckpointData(type=CHAPTER_MEMO, chapter=1)` → 调 `cli._commit_staging_for_checkpoint(project, cp)` → 断言 `plans/chapter-1-plan.md` 与 `plans/chapter-1-plan-decisions.json` 均在 committed 路径且 staging 标记清空；再模拟 crash（`clear_staging(project, preserve_checkpointed=True)`）后重跑 approve → 产物仍完整
- [x] **Step 6: cli.py MODIFY 块改**（F323）：

```python
# 旧：if decision in (APPROVE, MODIFY): _commit_staging_for_checkpoint(...)
if decision == ReviewDecision.APPROVE:
    _commit_staging_for_checkpoint(project_dir, cp)
elif decision == ReviewDecision.MODIFY:
    # C30 F323：人工编辑为基线 = 对旧 staging 显式 discard（同一审计谓词），
    # 不 commit 旧 staging 再让重派 LLM 覆盖人工编辑。
    discard_staging(project_dir, reason="modify_baseline_human_edit")
elif decision == ReviewDecision.REJECT:
    clear_staging(project_dir)
```

  注意：MODIFY 分支下人工编辑已直接落在 committed 路径（review 前），discard 不丢人工编辑；如调用点存在「staging 中有非 cp 产物的人工编辑」场景，实现时打开文件核实并在 spec-deviations 记录裁决
- [x] **Step 7: 跑测 + 回归**：`uv run pytest tests/pipeline/test_staging_lifecycle.py tests/pipeline/test_crash_recovery.py -q --no-cov` → 全 PASS；`uv run pytest tests/pipeline -k "staging or checkpoint" -q --no-cov` → PASS（T102 回归基线复用）
- [x] **Step 8: Commit**：`git add src/shenbi/pipeline/checkpoint.py src/shenbi/pipeline/crash_recovery.py src/shenbi/pipeline/cli.py src/shenbi/pipeline/machine.py src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_staging_lifecycle.py && git commit -m "fix: C30 R1 staging lifecycle predicate — checkpointed survival, emergency preserve, MODIFY explicit discard (F318/F323)"`

---

### Task 2: R2 · resume 游标锚定 + 步名版本化迁移

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（版本常量 + 迁移表）
- Modify: `src/shenbi/pipeline/cli.py:791-910`（cmd_resume 锚定 + 事件消费）
- Modify: `src/shenbi/pipeline/machine.py:90-116`（clear_checkpoint consumed 字段）
- Modify: `src/shenbi/contracts/enums.py`（如需新字面量）
- Test: `tests/pipeline/test_resume_anchor.py`（新建）

**Interfaces:**
- Consumes: `CHAPTER_STEPS`（chapter_loop）、`state.chapter_loop.{current_chapter, step_index}`、`chapters/chapter-N.md` 提交产物
- Produces:
  - `PIPELINE_STEPS_VERSION: int`（chapter_loop 模块常量，初始 2）
  - `STEP_NAME_MIGRATIONS: dict[int, dict[str, str]]`（旧代步名→新名，按版本号索引）
  - `committed_chapter_anchor(project_dir: Path) -> int`（chapter_loop 新增：`max(n for chapters/chapter-N.md 存在)`，无产物返回 0）
  - `migrate_steps_done(steps: list[str]) -> tuple[list[str], bool]`（chapter_loop 新增：按迁移表逐版本迁移，返回 (迁移后列表, 是否发生迁移)）

**复杂度:** infra · **test_kind:** tdd_red_green（迁移）+ characterization（先锁 cmd_resume 现行为再改，spec 风险节要求）· **层级:** T1 + T2（resume 链）

- [x] **Step 1: characterization 锁现行为**（防 pin 旧 bug：只锁「无 checkpoint 时 resume 不改 current_chapter」这一将被保留的面向）：在 `tests/pipeline/test_resume_anchor.py` 写 fixture 驱动用例：构造 `tests/fixtures/` 真实章节产物（`tests/fixtures/chapters/` 或 `chapter-N-draft.md` 族）落 `chapters/chapter-1..3.md`，state `current_chapter=4, step_index=0`，跑 `cmd_resume` 的锚定纯函数（不跑全 CLI——`_orchestrate_to_checkpoint` 会 dispatch；**只测新增纯函数 + cmd_resume 中锚定段的独立可测提取**，提取为 `_clamp_resume_cursor(cl: ChapterLoopStateData, project_dir: Path) -> None` 便于 T1 直测）
- [x] **Step 2: 失败测试**：

```python
def test_anchor_clamps_uncommitted_chapter(tmp_path):
    for n in (1, 2, 3):
        (tmp_path / "chapters").mkdir(exist_ok=True)
        (tmp_path / "chapters" / f"chapter-{n}.md").write_text(f"# 第{n}章\n", encoding="utf-8")
    cl = ChapterLoopStateData(current_chapter=6, step_index=0)   # 「当前章零进展」判据 = cl.chapter_states.get("6") 无 steps_done（ChapterState 才有该字段）
    _clamp_resume_cursor(cl, tmp_path)
    assert cl.current_chapter == 4   # 锚=已提交 3，恢复从 4 续，不回 1 也不越 6 静默覆盖

def test_anchor_noop_when_mid_committed_chapter(tmp_path):
    # 已提交章内的修订中断（当前章 steps_done 有内容）不动游标
    cl = ChapterLoopStateData(current_chapter=3, step_index=2,
                              chapter_states={"3": ChapterState(steps_done=["shenbi-chapter-drafting"])})
    _clamp_resume_cursor(cl, tmp_path)
    assert cl.current_chapter == 3

def test_steps_done_migration_v1_to_v2():
    migrated, changed = migrate_steps_done(["shenbi-foreshadowing-plant"])
    assert changed and migrated == ["shenbi-foreshadowing-lifecycle"]
```

- [x] **Step 3: 跑测失败**：`uv run pytest tests/pipeline/test_resume_anchor.py -q --no-cov` → FAIL
- [x] **Step 4: 实现**：
  - `committed_chapter_anchor`：glob `chapters/chapter-*.md` 取最大 N（regex `chapter-(\d+)\.md`，排除 `*-emergency.md` 等带 label 副本——匹配仅 `chapter-N.md` 精确形态）
  - `_clamp_resume_cursor`：`anchor = committed_chapter_anchor(pd)`；仅当 `cl.current_chapter > anchor + 1` 且当前章零进展（`cs = cl.chapter_states.get(str(cl.current_chapter))`，`cs is None or not cs.steps_done`——steps_done 在 ChapterState 上，ChapterLoopStateData 无此字段）→ `cl.current_chapter = anchor + 1`，`cl.step_index = 0`，`log.warning("resume_cursor_clamped", old=…, new=…)`
  - 事件消费：`clear_checkpoint`（machine.py）给 history 条目加 `"consumed": False`；`cmd_resume` 取尾部第一条 `decision=="approve" and not consumed` 的事件做 phase 转换（替换现 `history[-1]` 直读），转换后置 `consumed=True`。字面量 `"approve"` 已有 `ReviewDecision` 枚举承载，不新增裸串
  - `PIPELINE_STEPS_VERSION = 2`；`STEP_NAME_MIGRATIONS = {1: {"shenbi-foreshadowing-plant": "shenbi-foreshadowing-lifecycle", "shenbi-foreshadowing-track": "shenbi-foreshadowing-lifecycle", "shenbi-foreshadowing-recall": "shenbi-foreshadowing-lifecycle", "shenbi-context-composing": "pipeline-context-prepare", ...}}`——实现时 grep 旧步名全集（audit 证据：55 章 steps_done 旧代名），映射去重后写入
  - `cmd_resume` 在 state heal 后对每章 `steps_done` 跑 `migrate_steps_done`，发生迁移即 WARN + save_state
- [x] **Step 5: 快照 pin 测试**（强制 `PIPELINE_STEPS_VERSION` 与步骤表一致）：`tests/pipeline/test_chapter_steps_restructured.py` 已有步骤表测试——追加断言 `CHAPTER_STEPS` 的 `tuple(s.skill for s in CHAPTER_STEPS)` == 硬编码快照，且测试注释「步骤表重命名/重排必须 bump PIPELINE_STEPS_VERSION 并更新 STEP_NAME_MIGRATIONS 与本快照」
- [x] **Step 6: 跑测 + 回归**：`uv run pytest tests/pipeline/test_resume_anchor.py tests/pipeline/test_chapter_steps_restructured.py -q --no-cov`；`uv run pytest tests/pipeline -k resume -q --no-cov` → 全 PASS
- [x] **Step 7: Commit**：`git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/cli.py src/shenbi/pipeline/machine.py src/shenbi/contracts/enums.py tests/pipeline/test_resume_anchor.py tests/pipeline/test_chapter_steps_restructured.py && git commit -m "fix: C30 R2 resume cursor anchoring + steps_done versioned migration (F371/F1114/F797)"`

---

### Task 3: R3 · 装配触发后移 + 魔法索引推导化 + clear_checkpoint NONE 防御

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:149-165`（step-2 表项）、`:2299`（索引）、`:2774-2777`（装配入口守卫）
- Modify: `src/shenbi/pipeline/machine.py:90-116`（NONE 防御）
- Test: `tests/pipeline/test_step3_assembly_gate.py`（新建）、`tests/pipeline/test_chapter_steps_restructured.py`（扩展）

**Interfaces:**
- Consumes: `ChapterStep.calls_context_assembly`、`assemble_context`、`_FIRST_AUDIT_IDX` 推导先例
- Produces: `_FORESHADOWING_LIFECYCLE_IDX` 改为推导式（名字保留，验收 grep 零**字面量赋值**）

**复杂度:** infra · **test_kind:** tdd_red_green · **层级:** T1

- [x] **Step 1: 失败测试**：

```python
def test_step2_does_not_call_assembly():
    step2 = CHAPTER_STEPS[0 + 1]  # step_num 2
    assert step2.calls_context_assembly is False     # T1602：plan 不存在时不得装配
def test_step3_calls_assembly_with_plan_guard():
    step3 = CHAPTER_STEPS[2]
    assert step3.calls_context_assembly is True      # 装配移至 step-3 首入口
def test_foreshadowing_idx_derived_not_literal():
    import re
    src = Path("src/shenbi/pipeline/chapter_loop.py").read_text(encoding="utf-8")
    assert not re.search(r"_FORESHADOWING_LIFECYCLE_IDX\s*=\s*6\b", src)   # 字面量清零（含空格变体）
def test_assembly_guard_skips_when_plan_missing(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("shenbi.pipeline.context_assemble.assemble_context",
                        lambda *a, **k: calls.append(1) or (_ for _ in ()).throw(AssertionError("must not assemble")))
    # step-3 入口、plan 缺失 → 跳过装配且不写 fallback（调用计数 == 0）
    ...  # 构造 state，走装配守卫函数，断言 calls == [] 且无 context/chapter-N-context.md 生成
def test_clear_checkpoint_none_noop():
    state = PipelineState()
    state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE)
    clear_checkpoint(state, ReviewDecision.APPROVE)
    assert state.checkpoint_history == []   # F338：NONE 不入 history
```

- [x] **Step 2: 确认失败**：`uv run pytest tests/pipeline/test_step3_assembly_gate.py -q --no-cov` → FAIL
- [x] **Step 3: 实现**：
  - step-2 表项删 `calls_context_assembly=True`
  - 装配入口（chapter_loop.py:2774 `if step.calls_context_assembly:`）加 plan 存在性守卫：`plan = project_dir/"plans"/f"chapter-{n}-plan.md"`；不存在且当前 step 是 step-3 → 允许（首入口）但 assemble 内部已有 read 错误面——改为：装配前置校验 plan，缺失则 `log.error("assembly_skipped_no_plan", step=step.skill)` 并跳过（不再写废弃 fallback，:1276-1278 的 fallback 写盘分支删除或收紧为 step-3 显式路径）；实现时打开 :2760-2790 与 fallback 写盘段核实落点
  - `_FORESHADOWING_LIFECYCLE_IDX = 6` → 推导式（`_FIRST_AUDIT_IDX` 同法）：如 `_FORESHADOWING_LIFECYCLE_IDX = next(i for i, s in enumerate(CHAPTER_STEPS) if s.skill == "shenbi-foreshadowing-lifecycle")`
  - `clear_checkpoint` 开头：`if cp.type == CheckpointType.NONE: state.pending_checkpoint = CheckpointData(type=CheckpointType.NONE); return`（no-op 不入 history）
  - **改表必须 bump**：`PIPELINE_STEPS_VERSION` 与快照 pin 同步（T2 已建机制；本 task 不重排步序只改标志位，版本不变——若实现中发现需重排，bump 并补迁移表）
- [x] **Step 4: 跑测 + 回归**：`uv run pytest tests/pipeline/test_step3_assembly_gate.py tests/pipeline/test_chapter_steps_restructured.py tests/pipeline/test_resume_anchor.py -q --no-cov`；`uv run pytest tests/pipeline -k "steps or assembly or context" -q --no-cov`
- [x] **Step 5: F380 回归锁定**：在 `test_chapter_steps_restructured.py` 追加——新章首步 `CHAPTER_STEPS[0].skill == "pipeline-volume-align"` 且 volume-boundary approve 后 resume 进编排从 step-1 起（若现测试已覆盖则引用其名并确认存在，不重复）
- [x] **Step 6: Commit**：`git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/machine.py tests/pipeline/test_step3_assembly_gate.py tests/pipeline/test_chapter_steps_restructured.py && git commit -m "fix: C30 R3 assembly trigger gate + derived lifecycle idx + NONE checkpoint guard (T1602/F358/F357/F338/F380)"`

---

### Task 4: R4 · SCR 缓存 (path,size,mtime) 失效 + state 完成校验降级

**Files:**
- Modify: `src/shenbi/pipeline/scr_extractor.py:435-460`
- Modify: `src/shenbi/pipeline/chapter_loop.py`（完成标记前产物校验——落点为 `state.add_step_done(` 调用族前置校验，grep 全部调用点逐处加；:1343-1346 的 curation post-check 是 curation 输出校验且发生在入表前，非 F1112 落点）
- Test: `tests/pipeline/test_scr_cache_invalidation.py`（新建）

**Interfaces:**
- Consumes: `extract_scr` 现签名（不变，向后兼容）；缓存 schema 自管
- Produces: 缓存 JSON 增加 `_cache_key` 字段 `{"size": int, "mtime_ns": int}`（chapter file 的 stat）

**复杂度:** infra · **test_kind:** tdd_red_green · **层级:** T1

- [x] **Step 1: 失败测试**（章节文件用 `tests/fixtures/chapter-2-draft.md` 真实产物）：

```python
def test_scr_cache_invalidated_on_revision(tmp_path):
    (tmp_path / "chapters").mkdir(parents=True)   # mkdir 先于 copy
    shutil.copy("tests/fixtures/chapter-2-draft.md", tmp_path / "chapters" / "chapter-2.md")
    first = extract_scr(tmp_path, 2)
    # 模拟修订：改写章节文件（内容不同、可能同秒）
    p = tmp_path / "chapters" / "chapter-2.md"
    p.write_text(p.read_text(encoding="utf-8") + "\n新增段落", encoding="utf-8")
    second = extract_scr(tmp_path, 2)
    assert second.paragraph_stats != first.paragraph_stats or second.extracted_at != first.extracted_at
def test_scr_cache_hit_when_unchanged(tmp_path):
    ...  # 连续两次调用：第二次走缓存（monkeypatch extractor 计数为 0 或断言返回同一 extracted_at）
def test_cache_key_uses_size_and_mtime(tmp_path):
    ...  # 同 size 不同 mtime_ns → 失效（os.utime 显式改）
```

- [x] **Step 2: 确认失败**：`uv run pytest tests/pipeline/test_scr_cache_invalidation.py -q --no-cov` → FAIL（现缓存恒命中）
- [x] **Step 3: 实现**：`extract_scr` 缓存读取前 stat `chapter_path` 得 `(size, mtime_ns)`；缓存 JSON 顶层存 `"_cache_key": {"size":…, "mtime_ns":…}`；不匹配则重提取并回写（json 经 `safe_write` 原子写，如该模块未用则与仓库写惯例核对）。`StructuredChapterRepresentation(**cached)` 需剥离 `_cache_key` 键（cached.pop）
- [x] **Step 4: state 完成校验降级**（F1112 残余）：落点 = `chapter_loop.py` 中 `state.add_step_done(` 调用族（grep 全部调用点）：有 `output_path` 的步在入表前校验产物存在（`output_path.format`/replace N 后 resolve 到 project_dir），缺失则**不入表** + `log.warning("step_output_missing_downgraded", step=…, expected=…)`——降级 = 不声称完成（而非事后移除）。字面量入 log 事件名，不新增状态字面量；如需新的完成标志字段，`Literal` 入 enums.py
- [x] **Step 5: 跑测 + 回归**：`uv run pytest tests/pipeline/test_scr_cache_invalidation.py -q --no-cov`；`uv run pytest tests/pipeline -k "scr or extract" -q --no-cov`；相关 chapter_loop 测试族
- [x] **Step 6: Commit**：`git add src/shenbi/pipeline/scr_extractor.py src/shenbi/pipeline/chapter_loop.py src/shenbi/contracts/enums.py tests/pipeline/test_scr_cache_invalidation.py && git commit -m "fix: C30 R4 SCR cache (path,size,mtime) invalidation + step-output downgrade (F310/F1112)"`

---

### Task 5: R5 · 审计波/触发器扇出中途保存点 + 回写

**Files:**
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:150-190`（或其 chapter_loop 调用波处）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（波调用处闭包）
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（回写 C30 状态）
- Test: `tests/pipeline/test_wave_midpoint_save.py`（新建）

**Interfaces:**
- Consumes: `dispatch_reviews_parallel(tasks, ...)`、`as_completed` 循环
- Produces: `on_task_complete: Callable[[int, DispatchResult], None] | None = None` keyword 参数（**回调契约：仅成功完成的任务回调；失败/异常任务不回调**，重放范围由未完成段定义，契约写 docstring）

**复杂度:** infra · **test_kind:** tdd_red_green · **层级:** T1 + T2

- [x] **Step 1: 失败测试**（确定性故障注入：fake `dispatch_skill` 对指定 skill 名**返回** `DispatchResult(success=False)` 持久失败——走 failure 分支而非 exception 分支；fixture 输入用 `tests/fixtures/audits/` 真实审计产物）：

```python
def test_partial_wave_results_survive_crash(tmp_path, monkeypatch):
    # 注意：_dispatch_with_retry 对 success=False 重试 MAX_RETRIES=2 次——失败注入必须
    # 按 task 持久失败（不能全局计数只失败一次），并 patch MAX_RETRIES=0 + time.sleep
    # 消除真实 backoff。DispatchResult 字段 (success, returncode, stdout, stderr)；
    # project_dir 在 ReviewTask 上而非函数 kwarg。
    import shenbi.pipeline.parallel_dispatch as pd
    monkeypatch.setattr(pd, "MAX_RETRIES", 0)
    monkeypatch.setattr(pd.time, "sleep", lambda s: None)
    from shenbi.pipeline.parallel_dispatch import ReviewTask, dispatch_reviews_parallel
    completed_cb = []
    def fake_dispatch_skill(skill, *a, **k):
        from shenbi.pipeline.dispatch_helper import DispatchResult
        if skill == FAILING_SKILL:   # 按名持久失败，重试也不得成功
            return DispatchResult(success=False, returncode=1, stdout="", stderr="injected failure")
        return DispatchResult(success=True, returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(pd, "dispatch_skill", fake_dispatch_skill)
    # 两个真实 READ_ONLY_AUDIT 审计 skill 名（assert_parallelizable 跑真实 classify_skill_write_safety）
    tasks = [ReviewTask(OK_SKILL, project_dir=tmp_path, prompt=<真实审计产物内容>, ...),
             ReviewTask(FAILING_SKILL, project_dir=tmp_path, prompt=<...>, ...)]
    dispatch_reviews_parallel(tasks, on_task_complete=lambda i, r: completed_cb.append(i))
    assert completed_cb == [0]   # 成功者回调（可 save）、失败者不回调
    # 重放范围 = 未成功段：调用方以回调集合差集构造重放清单（同文件加用例断言差集逻辑）
```

- [x] **Step 2: 确认失败** → **Step 3: 实现**：`dispatch_reviews_parallel` 的 `as_completed(futures)` 循环内，每个成功完成的 future 即调 `on_task_complete(idx, result)`（异常/失败任务不回调，docstring 定契约）；chapter_loop 并行审计波调用处传闭包：合并该 skill 的 audit_results 进 state（走既有 `add_step_done`/audit_results 串行化设施，state.py:222 线程安全面）+ `save_state`。触发器扇出处（若 parallel 波之外的扇出点存在，grep `dispatch_reviews_parallel(` 全部调用方逐一接回调）——裁决记 spec-deviations `### T5`
- [x] **Step 4: 跑测 + 回归**：`uv run pytest tests/pipeline/test_wave_midpoint_save.py -q --no-cov`；`uv run pytest tests/pipeline -k "parallel or wave or review" -q --no-cov`
- [x] **Step 5: ledger 回写**：`docs/superpowers/audit-runs/2026-08-15/findings-ledger.md` 中 C30 的 14 条本 spec 关闭改 `closed-by PR（本 PR #）`、5 条按 spec closed-by 标签（T102/F1110→#120、F305→#63、F1153→ac466632+2b00ff53、F379→8d3f5c7e）、T1108 移交注记、F311 视 C37（保持 open + 注记）。PR 号在 merge 前未知——回写用 `fixed by SDD #44`，merge 后 squash SHA 由归档 commit 补
- [x] **Step 6: Commit**：`git add src/shenbi/pipeline/parallel_dispatch.py src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_wave_midpoint_save.py docs/superpowers/audit-runs/2026-08-15/findings-ledger.md && git commit -m "fix: C30 R5 parallel wave midpoint save points + ledger write-back (F377)"`

---

## 验收覆盖表（spec 验收 → task → 可执行验证）

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 staged sidecar approve 后入 committed truth | T1 | `uv run pytest tests/pipeline/test_staging_lifecycle.py -k commit -q --no-cov` |
| R1 atexit（latch + manifest 重建）不丢产物 | T1 | `uv run pytest tests/pipeline/test_staging_lifecycle.py tests/pipeline/test_crash_recovery.py -q --no-cov` |
| R2 F371 场景恢复零覆盖 | T2 | `uv run pytest tests/pipeline/test_resume_anchor.py -q --no-cov` |
| R2 旧 state fixture 迁移测试 | T2 | `uv run pytest tests/pipeline/test_resume_anchor.py -k migration -q --no-cov` |
| R3 step-2 不空跑装配、停顿 ≤1（调用计数代理） | T3 | `uv run pytest tests/pipeline/test_step3_assembly_gate.py -q --no-cov` |
| R3 `git grep _FORESHADOWING_LIFECYCLE_IDX` 零字面量 | T3 | `git grep -E "_FORESHADOWING_LIFECYCLE_IDX\s*=\s*6\b" -- src/` → 空 |
| R3 F380 回归锁定 | T3 | `uv run pytest tests/pipeline/test_chapter_steps_restructured.py -q --no-cov` |
| R4 修订后 SCR 含新文本 | T4 | `uv run pytest tests/pipeline/test_scr_cache_invalidation.py -q --no-cov` |
| R4 state claims 与产物一致性 | T4 | T4 Step 4 降级逻辑测试（同上文件补用例） |
| R5 崩溃注入重放 ≤ 当前段 | T5 | `uv run pytest tests/pipeline/test_wave_midpoint_save.py -q --no-cov` |
| 簇级 `just check` 全绿 | 全部 | `just check` |
| spec 验证命令（staging/checkpoint 族） | T1 | `uv run pytest tests/pipeline -k "staging or checkpoint" -q --no-cov` |
| spec 验证命令（resume 族） | T2 | `uv run pytest tests/pipeline -k resume -q --no-cov` |

G3.4 评分：本 plan 无生成物评分场景（全部确定性修复 + fixture 驱动测试），不涉及 dispatch 评分。

## Self-Review

- Spec 覆盖：R1(F318/F323)=T1、R2(F371/F1114/F797)=T2、R3(T1602/F358/F380/F357/F338)=T3、R4(F310/F1112)=T4、R5(F377)=T5；F311 留 C37（spec 裁决）；T1108 移交不实现。✓
- 占位符扫描：无 TBD；两处「实现时 grep 调用点逐一裁决」为显式现场裁决指令（有明确裁决记录去向 spec-deviations），非占位。✓
- 类型一致：`mark_staging_checkpointed/staging_checkpointed_targets/discard_staging/clear_staging(preserve_checkpointed=)` T1 定义 T1 消费；`committed_chapter_anchor/migrate_steps_done/_clamp_resume_cursor` T2 定义；`on_task_complete` T5 定义。✓
