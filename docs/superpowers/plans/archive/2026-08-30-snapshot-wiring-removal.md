# 快照子系统路径 3 移除（SDD #26）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec #26 三路裁决的路径 3，移除快照子系统死代码面（差分三件套 + step 15 + cmd_rollback + last_snapshot 字段），保留已接线的 crash 应急快照与 shenbi-snapshot-manage skill 路径。

**Architecture:** 纯删除 + 步骤表收缩 + 状态字段下线。恢复语义不降级：checkpoint REJECT→redo（自动）+ skill rollback（用户驱动）+ crash 应急快照三重覆盖已在位。所有 task 均为 **infra**（pipeline/state 多文件联动）→ 协调者亲自实现，不分派。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（uv run 同构）。

## Global Constraints

- spec：`docs/superpowers/specs/archive/2026-08-15-snapshot-subsystem-wiring-design.md`（路径 3 验收节）
- 死符号清单含 helper：`_get_core_snapshot_files`、`_has_minimum_chinese_chars`（chapter_loop.py，唯一调用方在死函数 `_snapshot_chapter_files` 内，属死链）
- 保留面：`crash_recovery.py` 全部（含其自身 `_snapshot_chapter_files:155`）、`skills/shenbi-snapshot-manage/`、CONDITIONAL_STEPS step 3
- step 编号是日志字段，步骤身份键是 `step.skill`（`add_step_done` 按技能名记账）——删 step 15 条目后把 step 16 的编号字段改为 15，`step_index` 为列表位置，跨版本 resume 的错位属可接受迁移注记（记 spec-deviations）
- 状态字面量单一信源 / structlog 无 print / gate 幂等 / conventional commits / 显式 pathspec commit（禁 `git add -A`）
- 验证一律 `uv run pytest ...` / `just check`（与 CI 同构）

---

### Task 1: 步骤表收缩——删 step 15 条目并重编号

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:247-256`（step 15 条目 + step 16 注释/编号）、`chapter_loop.py:133`（步骤列举注释）
- Test: `tests/unit/pipeline/test_chapter_loop.py`（新增 characterization）

**Interfaces:**
- Consumes: `CHAPTER_STEPS: list[ChapterStep]`（chapter_loop.py 现状；编号字段实名 `step_num`，chapter_loop.py:96）
- Produces: `CHAPTER_STEPS` 15 条（原 16 减一），`shenbi-chapter-revision` step_num=15；无 `pipeline-pre-revision-snapshot`

- [ ] **Step 1: 更新存量步骤表断言**（`tests/unit/pipeline/test_chapter_loop.py`）：
  - `:65` `assert len(CHAPTER_STEPS) == 16` → `== 15`
  - `:68` `range(1, 17)` → `range(1, 16)`
  - `:282/296/309` `step_index = 15  # last step (chapter-revision)` → `= 14`（同注释）；后续若有以 15 为完成态的断言按新表（完成判定是 `step_index >= len(CHAPTER_STEPS)`，需逐处核语义后改）
  - `:663-695`、`:763-772` 逐步测试：删除 pre-revision-snapshot 那一步的 `run_chapter_step` 调用与 `step_index == 14`（旧 15 号位）断言，后续索引整体 -1；顺带清理 `:663,666,692,763` 与 `test_chapter_loop_full.py:244,418` 的 `pre-revision-snapshot` 过时注释（对齐 Task 5 grep 门）及 M2 注释腐化：`test_chapter_loop.py:654` docstring「step 16 (chapter-revision)…」→ 15、`:746-749`「Steps 15 (snapshot)… step 16」重写为移除后步骤、`test_chapter_loop_full.py:7` 管线顺序 docstring 删 snapshot 字样
- [ ] **Step 2: 新增 characterization 测试**（加到 `tests/unit/pipeline/test_chapter_loop.py`）

```python
def test_step_table_has_no_pre_revision_snapshot():
    skills = [s.skill for s in CHAPTER_STEPS]
    assert "pipeline-pre-revision-snapshot" not in skills


def test_revision_step_follows_sensitivity_audit():
    skills = [s.skill for s in CHAPTER_STEPS]
    assert skills.index("shenbi-review-sensitivity") + 1 == skills.index("shenbi-chapter-revision")
```

- [ ] **Step 3: 跑测试确认新两条 FAIL**：`uv run pytest tests/unit/pipeline/test_chapter_loop.py -k "pre_revision or revision_step_follows" -v`
- [ ] **Step 4: 删除 step 15 条目**（chapter_loop.py 247-252 的 `ChapterStep(15, "pipeline-pre-revision-snapshot", ...)` 块与 `# Step 15: Pre-revision snapshot (deterministic)` 注释），step 16 的 `ChapterStep(16, ...)` 改 `ChapterStep(15, ...)`，`# Step 16:` 注释改 `# Step 15:`；同步修 `:127`（`16 core steps` → `15`）与 `:131-133` 注释列举（删 `pre-revision-snapshot` 字样）
- [ ] **Step 5: 全文件测试 PASS**：`uv run pytest tests/unit/pipeline/test_chapter_loop.py tests/unit/pipeline/test_chapter_loop_full.py -v`（不限 -k，存量+新增全绿）
- [ ] **Step 6: Commit**：`git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py tests/unit/pipeline/test_chapter_loop_full.py && git commit -m "refactor: remove no-op step 15 pre-revision-snapshot from chapter step table (spec #26 path 3)"`

**迁移注记（记 spec-deviations）**：`step_index` 为列表位置、无 heal；跨版本持久化 state 若停在新旧 15 号位（旧=revision、新=完成），resume 会静默跳过 revision 一步——记为已知迁移错位，框架预生产期可接受。`steps_done` 按技能名记账、`_FIRST/_LAST_AUDIT_IDX` 重算不受影响（audit 步均在索引 14 之前）。

### Task 2: chapter_loop 死代码四函数 + last_snapshot 状态面下线

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（删 62 行 import；删 `_prune_old_snapshots`(1583-1645)、`_get_core_snapshot_files`(1647-1666)、`_has_minimum_chinese_chars`(1668-1684)、`_snapshot_chapter_files`(1686-1811) 四函数整段）
- Modify: `src/shenbi/pipeline/state.py:171,274,355`（`last_snapshot` 字段：dataclass field、to_dict、from_dict 三处）
- Modify: `src/shenbi/pipeline/state_heal.py:3,76-95,107`（docstring 提及、`_heal_last_snapshot` 整函数、调用行）
- Modify: `src/shenbi/pipeline/cli.py:785`（注释删 `last_snapshot` 字样，保留 retry_budget/revision_count heal 说明）
- Test delete: `tests/unit/pipeline/test_snapshot_pruning.py`、`tests/unit/pipeline/test_last_snapshot.py`
- Test modify: `tests/unit/pipeline/test_snapshot_coverage.py`（删 chapter_loop import 与其测试类 `TestCoreSnapshotFiles`/`TestMinChineseChars`，保留 crash_recovery 测试）、`tests/unit/pipeline/test_state_heal.py`（删 `test_heals_last_snapshot_from_disk`）、`tests/unit/pipeline/test_adaptive_triggers.py`（删 `_snapshot_chapter_files` import 与 `TestFileSnapshot` 类）

**Interfaces:**
- Produces: `PipelineState` 无 `last_snapshot` 属性；`heal_state_counters` 返回不含 `last_snapshot_healed:` 动作

- [ ] **Step 1: 先删测试文件与测试面**（上列 delete/modify），跑 `uv run pytest tests/unit/pipeline/test_state_heal.py tests/unit/pipeline/test_adaptive_triggers.py -v` 确认现存测试无 import 错误
- [ ] **Step 2: 删 chapter_loop 四函数与 import**；`uv run python -c "from shenbi.pipeline import chapter_loop"` 确认模块可导入
- [ ] **Step 3: state.py 三处 + state_heal.py 删 heal 面 + cli.py 注释**；`uv run pytest tests/unit/pipeline/test_state.py tests/unit/pipeline/test_state_heal.py -v` PASS
- [ ] **Step 4: 残留 grep**：`grep -rn "last_snapshot\|_prune_old_snapshots\|_get_core_snapshot_files\|_has_minimum_chinese_chars\|_snapshot_chapter_files" src/` 仅允许命中 crash_recovery.py 自身实现与其调用（139 行）
- [ ] **Step 5: 全量快测**：`uv run pytest -n auto -m "not last" -q`（此时 snapshot_diff 尚在，其测试仍绿）
- [ ] **Step 6: Commit**：`git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/state.py src/shenbi/pipeline/state_heal.py src/shenbi/pipeline/cli.py tests/unit/pipeline/test_snapshot_pruning.py tests/unit/pipeline/test_last_snapshot.py tests/unit/pipeline/test_snapshot_coverage.py tests/unit/pipeline/test_state_heal.py tests/unit/pipeline/test_adaptive_triggers.py && git commit -m "refactor: remove dead snapshot trio + last_snapshot state field (spec #26 path 3)"`（删除文件加 `-u` 不需要——显式列路径即含删除）

### Task 3: cmd_rollback 删除

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:921-943`（`cmd_rollback` 整函数）
- Test delete: `tests/unit/pipeline/test_cli_rollback_removed.py`
- Test modify: `tests/unit/pipeline/test_cli.py:517-532`（删「cmd_rollback retained for direct callers」断言测试；保留 `test_help_does_not_list_rollback` 的等价断言若存在于 test_cli.py——help 不列 rollback 的性质已由子命令注册缺失天然保持）

**Interfaces:**
- Produces: `shenbi.pipeline.cli` 无 `cmd_rollback` 属性

- [ ] **Step 1: 删测试面** → **Step 2: 删函数** → **Step 3:** `uv run python -c "from shenbi.pipeline import cli; assert not hasattr(cli, 'cmd_rollback')"` + `uv run pytest tests/unit/pipeline/test_cli.py -q` PASS → **Step 4: Commit** `fix: remove dead cmd_rollback (subparser already removed; rollback served by shenbi-snapshot-manage skill) (spec #26 path 3)`

### Task 4: snapshot_diff 模块整体删除

**Files:**
- Delete: `src/shenbi/pipeline/snapshot_diff.py`、`tests/pipeline/test_snapshot_diff.py`
- Verify: `grep -rn "snapshot_diff\|create_differential_snapshot\|restore_from_snapshot" src/` 零输出；`tests/` 仅归档文档外零输出

- [ ] **Step 1: 删两文件** → **Step 2: grep 零残留**（命令+输出记 progress.md 验收证据）→ **Step 3:** `uv run pytest -n auto -m "not last" -q` 全绿 → **Step 4: Commit** `refactor: delete snapshot_diff module (differential snapshot engine dead-wired, spec #26 path 3)`

### Task 5: 文档与台账同步 + #57 失效注记

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md:63`（F303 状态 `specced` → `removed (spec #26 path 3)`）
- Modify: `docs/superpowers/specs/INDEX.md` #57 条目（加「**2026-08-30 注记**: #26 已裁决路径 3（移除）——本 spec 按其 T0 大部分自动失效，存活面仅 T4 truth-files.yaml/词面协调，待其自身价值门复核」）
- Modify: `docs/superpowers/specs/2026-08-16-audit-snapshot-unify-fix.md`（#57 spec 头加同义失效注记——其正文多处引用差分机制与 F351「step-15 空操作」，头部注记为权威失效声明，正文不逐条改）
- Modify: `docs/superpowers/specs/archive/2026-08-15-snapshot-subsystem-wiring-design.md`（本 spec 头 Status 加「三路裁决: 路径 3（移除）· 2026-08-30」——spec 自身在文档同步面内）
- Modify: `tests/unit/contracts/test_registry_pipeline_producers.py:42-44`（D20 注释：`chapter_loop._snapshot_chapter_files` 已删，改指 `crash_recovery._snapshot_chapter_files`——grep 该注释实际文本后改写）

- [ ] **Step 1: 五处文档改动** → **Step 2:** `uv run pytest tests/unit/contracts/test_registry_pipeline_producers.py -q` PASS → **Step 3:** `grep -rn "pre-revision-snapshot" --include="*.py" src/ tests/` 零输出（测试注释已在 T1 Step 1 清理；audit-runs 历史记录按 spec 豁免）→ **Step 4: Commit** `docs: sync F303 ledger + #57 invalidation note after spec #26 path-3 removal`

### Task 6: 契约生成物同步（deps.json）

**Files:**
- Regenerate: `tests/tiers/deps.json`（sha256 钉住了 chapter_loop.py/snapshot_diff.py/state.py/state_heal.py——T1-T4 改动后必脏）

- [ ] **Step 1:** `just generate`（即 `shenbi-sync-contracts`，禁手改生成物）→ `git diff --stat` 确认变更仅为 deps.json（及 docs/framework 若有）→ **Step 2:** `git add tests/tiers/deps.json docs/framework 2>/dev/null; git commit -m "chore: sync deps.json hashes after snapshot removal (spec #26 path 3)"`

### Task 7: 全量门禁

- [ ] **Step 1:** `just check` 全绿（含 shenbi-sync-contracts 幂等 diff——T6 先行使之为空 diff），完整输出粘贴 progress.md `## 门禁输出`
- [ ] **Step 2:** spec 路径 3 验收逐条跑：死符号清单全清 grep / `git grep create_differential_snapshot -- src/` 零输出 / `just check` 绿——记 `## 验收证据`
