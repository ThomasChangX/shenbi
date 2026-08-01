# 消除 cyclic-import 簇（pipeline + dispatcher/audit，10 sites）Spec

> **Date:** 2026-08-02
> **Series:** 架构债清理（独立，承接 PR #25 §9 follow-up）
> **Depends on:** Issue #24；PR #25（已合并 `56fe7e7`，引入 10 条 `# py/cyclic-import` 注释压制）
> **Status:** 设计中（Design）
> **Severity:** 🟡 Medium（功能零影响；阻碍 CodeQL 归零 + 模块边界清晰化）
> **目的:** 通过把跨环共享的纯函数/常量/类型下沉到中性 `_shared` 模块，将两个真实 import 环（4-node + 3-node）改造为 DAG，使 CodeQL `py/cyclic-import` 告警从 10 归零，并删除全部 10 条压制注释。

---

## 1. 背景

### 1.1 来由

PR #25（`eliminate-existing-warnings`，squash `56fe7e7`，2026-08-01 合并）修复了 94 条 CodeQL 告警中的 83 条。剩余 12 条中：

- **10 条 `py/cyclic-import`**：位于两个真实 import 环上。PR §9 决定**不在该 PR 内重构**，用注释 `# py/cyclic-import (CodeQL): cycle with X — lazy import where needed; see follow-up. Spec §9 no refactor.` 临时标注，follow-up 即 Issue #24。
- **1 条 `py/unused-import`**：`dispatch_helper.py:57` 的 `write_truth_file` re-export（`# noqa: F401` 锚点）。CodeQL 不认 `# noqa`。
- **1 条 false-positive**：record 在别处，非本 spec 范围。

本 spec 处理 **10 条 cyclic + 1 条 unused-import**（共 11 条，对齐 Issue #24 全部内容）。

### 1.2 为什么必须重构（不能继续压注释）

`py/cyclic-import` 是 **CodeQL 图级别** 检查：

- **不**遵守 `# noqa` / `# type: ignore` / 行内注释（与 ruff / pyright 不同）。
- **只**看模块依赖图拓扑——只有让图变成 DAG（有向无环图），告警才会消失。

实测：PR #25 的 10 条 `# py/cyclic-import` 注释对 CodeQL **完全无效**，告警数未减。这是 CodeQL 的设计行为，非 bug。

### 1.3 当前功能影响

**零。** Python 的 lazy import（函数内 `import`）在运行时正常解析；`TYPE_CHECKING` 块更不触发。两个环都不阻塞当前任何功能。这是纯**工程债 / 质量基线**问题。

---

## 2. 诊断：两个真实环（已逐边核实）

> 下表行号基于 main HEAD `ad3b998`（2026-08-02）。Issue #24 正文行号是 PR #25 分支当时的快照，有少量偏移；环结构不变。

### 2.1 Cluster 1：pipeline 4-节点环

```
triggers ──► dispatch_helper ──► plan_skeleton ──► context_assemble ──┐
     ▲                                                                │
     └────────────────────────────────────────────────────────────────┘
```

| 边 | 方向 | 位置 | 类型 |
|---|---|---|---|
| triggers → dispatch_helper | `from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4` | `triggers.py:55` | top |
| triggers → dispatch_helper | `from shenbi.pipeline.dispatch_helper import run_gate_g3` | `triggers.py:645` | lazy |
| dispatch_helper → plan_skeleton | `from shenbi.pipeline.plan_skeleton import generate_plan_skeleton` | `dispatch_helper.py:689` | lazy |
| plan_skeleton → context_assemble | `from shenbi.pipeline.context_assemble import _BRIDGE_ACTIVATION_WINDOW` | `plan_skeleton.py:32` | top |
| plan_skeleton → context_assemble | `from shenbi.pipeline.context_assemble import _resolve_volume_at_runtime` | `plan_skeleton.py:200` | lazy |
| **context_assemble → triggers** | `from shenbi.pipeline.triggers import read_volume_boundaries` | `context_assemble.py:208`（在 `_resolve_volume_at_runtime` 体内） | lazy |

**回边（构成环的唯一边）**：`context_assemble → triggers`（L208）。

**关键依赖事实**：`_resolve_volume_at_runtime`（定义于 `context_assemble.py:201`）**本身就调用** `read_volume_boundaries`（定义于 `triggers.py:326`）。两者同属"volume map 解析"职责域——`read_volume_boundaries` 解析 `outline/volume_map.md` 得到分卷末章集合，`_resolve_volume_at_runtime` 基于该集合计算 `(volume_name, ch_start, ch_end)`。这是**语义耦合**，不只是语法环。

### 2.2 Cluster 2：dispatcher/audit 环

```
executor ──► write_audit ──► executor        (2-节点环，实质)
   │            ▲
   └──► record ─┘  (TYPE_CHECKING，类型注解环)
```

| 边 | 方向 | 位置 | 类型 |
|---|---|---|---|
| executor → record | `from shenbi.audit.record import record_audit_outcome` | `executor.py:259` | lazy |
| executor → write_audit | `from shenbi.audit.write_audit import audit_writes` | `executor.py:263` | lazy |
| **write_audit → executor** | `from shenbi.dispatcher.executor import derive_output_files` | `write_audit.py:30`（在 `_declared_patterns` 体内） | lazy |
| **record → write_audit** | `from shenbi.audit.write_audit import AuditResult` | `record.py:16` | TYPE_CHECKING |

**回边**：`write_audit → executor`（L30，运行时环）+ `record → write_audit`（L16，仅类型注解环）。

**重要消歧（同名异类）**：codebase 有**两个无关的 `AuditResult` 类**——
- `shenbi.pipeline.audit_layer.AuditResult`（L85，chapter_loop 用，**不在本环**）
- `shenbi.audit.write_audit.AuditResult`（L20，本环，`record.py` 引用的就是它）

字段集不同，互不通用。本 spec 的 `AuditResult` 一律指后者（`write_audit.AuditResult`：`skill`/`violations`/`drift`/`checked_files`）。

---

## 3. 修复方案：下沉共享符号到中性 `_shared` 模块

### 3.1 总原则

环的本质是"双方互相需要对方的符号"。打破方式：识别出**被环内多个成员依赖、但自身不依赖任何环内成员**的符号，把它们迁移到一个新的中性模块。迁移后，原模块对中性模块形成**单向**依赖（`模块 → _shared`），回边消失，图变 DAG。

**不下沉的判断标准**（守住职责边界，避免 `_shared` 沦为杂物间）：
- 模块的核心职责符号（如 `dispatch_skill` / `audit_writes` / `generate_plan_skeleton`）**保留原地**。
- 只下沉：纯常量、纯函数（无环内反向依赖）、共享类型（dataclass）。

### 3.2 Cluster 1 修复 → 新建 `src/shenbi/pipeline/_shared.py`

下沉 3 个符号（构成完整 volume-map 解析域）：

| 下沉符号 | 当前位置 | 类型 | 依赖（确认无环内反向依赖） | 被谁用 |
|---|---|---|---|---|
| `_BRIDGE_ACTIVATION_WINDOW` | `context_assemble.py:45` | 常量（`= 3`） | 无 | `plan_skeleton` (top) |
| `read_volume_boundaries` | `triggers.py:326` | 纯函数 | 仅 `VOLUME_MAP_PATH`/`_END_RE`/`_RANGE_RE`（同下沉）+ `re`/`pathlib` | `context_assemble` (lazy) |
| `_resolve_volume_at_runtime` | `context_assemble.py:201` | 纯函数 | 仅调 `read_volume_boundaries`（同下沉） | `plan_skeleton` (lazy) |

**附带下沉的私有常量**（`read_volume_boundaries` 的依赖）：
- `VOLUME_MAP_PATH = "outline/volume_map.md"`（`triggers.py:78`）
- `_END_RE` / `_RANGE_RE`（`triggers.py:316`/`320`）

#### 迁移后边的变化

```
                          ┌──────────────────▼
                          ▼                   │
              _shared.py（新，无环内依赖）     │
                          ▲                   │
                          │                   │
triggers ──► dispatch_helper ──► plan_skeleton ─► context_assemble
   ▲                                                         │
   │                                                         │
   └──── context_assemble 仍直接调 read_volume_boundaries ──┘  ← 回边消失！
         （改成 from shenbi.pipeline._shared import read_volume_boundaries）
```

`context_assemble → triggers` 这条回边**消失**（改为 `context_assemble → _shared`）。4-节点环被打断。

#### Re-export 策略（向后兼容）

`read_volume_boundaries` 被 **5 处运行时消费者 + 1 处测试** 直接 import（全部经 `from shenbi.pipeline.triggers import read_volume_boundaries`）：
- `src/shenbi/pipeline/closure.py:30`（**顶层 import**，load-bearing）
- `src/shenbi/pipeline/chapter_loop.py:976`（lazy）
- `src/shenbi/pipeline/cli.py:154`（lazy）
- `src/shenbi/pipeline/triggers.py:360`（模块内自调，`is_volume_boundary`）
- `src/shenbi/pipeline/context_assemble.py:209`（lazy，本环回边，Phase 1 后改指 `_shared`）
- `tests/unit/pipeline/test_triggers.py:40`（测试锚点）

下沉后 `triggers.py` 的 re-export 是 **MANDATORY**（非"为安全"）—— 删 re-export 会让 `closure.py` 顶层 import 在 import-time 崩溃，`chapter_loop`/`cli` 运行时崩。re-export 行：

```python
# triggers.py —— 下沉后保留 re-export（MANDATORY：closure.py 顶层 import + 3 处运行时消费者依赖此 surface）
from shenbi.pipeline._shared import read_volume_boundaries, VOLUME_MAP_PATH  # noqa: F401
```

> `_BRIDGE_ACTIVATION_WINDOW` / `_resolve_volume_at_runtime` 经核实**无 src/tests 直接 import**（grep 零命中；仅 `context_assemble.py` 自身用 `_BRIDGE_ACTIVATION_WINDOW`，Phase 1 已改 import 自 `_shared`）。这两个 `_`-前缀符号的 re-export 是 **可选**（§6.2 Option A/B）。

### 3.3 Cluster 2 修复 → 新建 `src/shenbi/audit/_shared.py`

下沉 2 个符号：

| 下沉符号 | 当前位置 | 类型 | 依赖（确认无环内反向依赖） | 被谁用 |
|---|---|---|---|---|
| `derive_output_files` | `executor.py:110` | 纯函数 | `load_contract`（contracts 包，非环内）+ `resolve_or_skip` + `ContractError` | `write_audit` (lazy L30) |
| `AuditResult` | `write_audit.py:20` | frozen dataclass | 无 | `record` (TYPE_CHECKING L16) + `write_audit`/`executor` 自用 |

#### 迁移后边的变化

```
                ┌─────────────▼
                ▼              │
        _shared.py（新）       │  derive_output_files, AuditResult
                ▲              │
        ┌───────┴──────┐       │
        │              │       │
   write_audit     record      │
        ▲              ▲       │
        │              │       │
        └── executor ──┘       │
            (单向 → record, write_audit, _shared)
```

- `write_audit → executor`（L30）改为 `write_audit → _shared`，运行时环消失。
- `record → write_audit`（L16 TYPE_CHECKING）改为 `record → _shared`，类型注解环消失。

> **依赖方向说明**（plan 阶段注意）：`executor.py`（在 `dispatcher/` 包）改为顶部 `from shenbi.audit._shared import derive_output_files`，使 `dispatcher → audit` 包级依赖出现。这是有意接受的——`audit/_shared.py` 是 **叶子模块**（只 import `shenbi.contracts.*` + 标准库，不回 import `dispatcher`/`audit.write_audit`/`audit.record`，Phase 1 核实过 `derive_output_files` 函数体）。`audit` 前缀是组织性的（包内私有 `_shared`），非语义层。`derive_output_files` 本质是 contracts-resolving helper（`load_contract` + `resolve_or_skip` 的薄封装），非 "audit" 概念；放在 `audit/_shared` 而非 `contracts/paths.py` 是为最小改动（避免改 `contracts` 包导入方向）。

#### Re-export 策略

- `derive_output_files` 被 **2 处运行时消费者 + 1 处测试** 直接 import（全部经 `from shenbi.dispatcher.executor import derive_output_files`）：
  - `src/shenbi/phase_runner.py:190`（lazy，T2 phase 状态机用）
  - `src/shenbi/audit/write_audit.py:31`（lazy，`_declared_patterns`——本环回边，Phase 2 后改指 `_shared`）
  - `tests/unit/test_dispatcher_executor.py:13`（测试锚点，多行绝对导入块）
  - 另：`executor.py` 自身在 L218/L245 内部调用（经顶部 re-export 解析）。
  - re-export 在 `executor.py` 顶部 `from shenbi.audit._shared import derive_output_files  # noqa: F401` 是 **MANDATORY**（`phase_runner.py` + 测试依赖此 surface）。
- `AuditResult` 被 `tests/unit/audit/test_record.py:7` 直接 import（`from shenbi.audit.write_audit import AuditResult`），且 `src/shenbi/audit/__init__.py:8` 把它列为公开 API（`from shenbi.audit.write_audit import AuditResult, audit_writes`）。需在 `write_audit.py` 保留 re-export：`from shenbi.audit._shared import AuditResult  # noqa: F401`。
  - **消歧订正（Phase 1 核实）**：原 spec 误引 `tests/unit/pipeline/test_audit_layer.py:21` 作为锚点——该测试 import 的是 `shenbi.pipeline.audit_layer.AuditResult`（同名异类，§2.2 列出的 out-of-cycle 类），**不依赖** `write_audit` 的 re-export。`write_audit.AuditResult` 的真实测试消费者是 `test_record.py:7`。

### 3.4 附带：消除第 11 条告警（`write_truth_file` re-export）

Issue #24 末尾提到的 `dispatch_helper.py:57` `py/unused-import`：

```python
# dispatch_helper.py:57（当前）
from shenbi.pipeline.truth_io import write_truth_file  # noqa: F401  # pyright: ignore[reportUnusedImport]
```

这条 re-export 的**唯一消费者**是 `tests/unit/pipeline/test_dispatch_write_semantics.py:46`：
```python
with patch("shenbi.pipeline.dispatch_helper.write_truth_file") as mock_wtf:
```

**根因**：`patch` 需要在 `dispatch_helper` 模块命名空间里能找到 `write_truth_file`，因此加了 re-export。但 CodeQL 不认 `# noqa`。

**修复（两种选项，§6.3 决策）**：

- **选项 A（推荐，彻底）**：核实 `dispatch_helper` 运行时是否真的用 `write_truth_file`（grep 显示 `dispatch_helper` 体内无调用，仅 re-export 行）。若运行时不用，删除 re-export 行；同时把 test 的 patch 路径改为 `shenbi.pipeline.truth_io.write_truth_file`（真实定义处）。告警自然消失。
- **选项 B（保守）**：把 `write_truth_file` 的真实 import 移到 `dispatch_helper` 顶部并实际调用（若确有调用点），消除"unused"判定。

倾向选项 A（需在 plan 阶段 grep 确认 `dispatch_helper` 运行时零调用 `write_truth_file`）。

---

## 4. 实施阶段（4 阶段，含验证点）

> 每阶段结束必须过 `just check` 的相关子集；全量验证在 Phase 4。

### Phase 1：新建 `pipeline/_shared.py`，下沉 volume-map 解析域

**改动文件**：
1. 新建 `src/shenbi/pipeline/_shared.py`：迁移 `_BRIDGE_ACTIVATION_WINDOW`、`VOLUME_MAP_PATH`、`_END_RE`、`_RANGE_RE`、`read_volume_boundaries`、`_resolve_volume_at_runtime`。
2. `src/shenbi/pipeline/triggers.py`：删除上述符号定义，顶部加 `from shenbi.pipeline._shared import read_volume_boundaries, VOLUME_MAP_PATH  # noqa: F401`（re-export 守测试锚点）。删除 L208 的 cyclic 注释。
3. `src/shenbi/pipeline/context_assemble.py`：删除 `_BRIDGE_ACTIVATION_WINDOW`/`_resolve_volume_at_runtime` 定义。顶部 import `from shenbi.pipeline._shared import _BRIDGE_ACTIVATION_WINDOW, _resolve_volume_at_runtime`（`_BRIDGE_ACTIVATION_WINDOW` 仍被 `_load_volume_context` 在 L287 使用，**必须**一并 import，否则 NameError）。L208 的 `from shenbi.pipeline.triggers import read_volume_boundaries` 改为 `from shenbi.pipeline._shared import read_volume_boundaries`（回边消失）。删除 cyclic 注释。
4. `src/shenbi/pipeline/plan_skeleton.py`：L32/L200 的 `from shenbi.pipeline.context_assemble import ...` 改为指向 `_shared`。删除 cyclic 注释。

**验证**：
- `pytest tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_plan_skeleton.py -v` 全绿。
  - `test_triggers.py` 覆盖 `read_volume_boundaries`（L218/L224 用例）；`test_context_assemble.py` 覆盖 `_load_volume_context`（L287 用 `_BRIDGE_ACTIVATION_WINDOW`，catch C1 类 NameError）；`test_plan_skeleton.py` 覆盖 `generate_plan_skeleton`（用 `_resolve_volume_at_runtime`）。
- `ruff check src/shenbi/pipeline/_shared.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/plan_skeleton.py`。
- `grep -rn "py/cyclic-import" src/shenbi/pipeline/` 应只剩 Cluster 1 中已处理的 0 条（Cluster 2 在 Phase 3）。

### Phase 2：新建 `audit/_shared.py`，下沉 derive_output_files + AuditResult

**改动文件**：
1. 新建 `src/shenbi/audit/_shared.py`：迁移 `derive_output_files`（连同其依赖 `load_contract`/`resolve_or_skip`/`ContractError` 的 import）、`AuditResult` dataclass。
2. `src/shenbi/dispatcher/executor.py`：删除 `derive_output_files` 定义，顶部加 `from shenbi.audit._shared import derive_output_files  # noqa: F401`（re-export）。
3. `src/shenbi/audit/write_audit.py`：删除 `AuditResult` 定义，加 `from shenbi.audit._shared import AuditResult  # noqa: F401`。L30 的 `from shenbi.dispatcher.executor import derive_output_files` 改为 `from shenbi.audit._shared import derive_output_files`。删除 cyclic 注释。
4. `src/shenbi/audit/record.py`：L16 的 `from shenbi.audit.write_audit import AuditResult` 改为 `from shenbi.audit._shared import AuditResult`。删除 cyclic 注释。
5. `src/shenbi/dispatcher/executor.py`：L259/L263 的 cyclic 注释删除（import 语句本身保留——它们指向 `audit.record`/`audit.write_audit`，是合法单向依赖）。

**验证**：
- `pytest tests/unit/test_dispatcher_executor.py tests/unit/audit/test_record.py -v` 全绿。
  - `test_dispatcher_executor.py` 覆盖 `derive_output_files`（L13 import）；`test_record.py` 覆盖 `write_audit.AuditResult`（L7 import，是 cycle 内那个 AuditResult 的真实消费者）。注：`test_audit_layer.py` 测的是 `audit_layer.AuditResult`（同名异类、out-of-cycle），与本 phase 无关，不纳入。
- `grep -rn "py/cyclic-import" src/shenbi/` 应返回 **0 条**。

### Phase 3：消除 `write_truth_file` re-export（第 11 条告警）

**前置确认**（plan 阶段做，已 Phase 1 核实）：`grep -n "write_truth_file" src/shenbi/pipeline/dispatch_helper.py` 返回 4 hit——L57（re-export 本身）+ L1034/L1137/L1214（docstring/comment 文本提及，非可执行调用）。运行时零调用，走选项 A 成立。

**改动**（选项 A）：
1. `src/shenbi/pipeline/dispatch_helper.py`：删除 L53-57 整块（4 行解释注释 + 1 行 re-export）。
2. `tests/unit/pipeline/test_dispatch_write_semantics.py`：`TestAppendDedupNotRoutedInDispatch.test_append_dedup_truth_file_is_written_whole_not_upserted`（L37-58）—— 删除 L46-47 的 `with patch("shenbi.pipeline.dispatch_helper.write_truth_file") as mock_wtf:` + `mock_wtf.return_value = None` 包裹层，以及 L55 的 `mock_wtf.assert_not_called()`。**保留** L57-58 的正面断言（whole-file 写入经 `safe_write`）。注：该 patch 本就是 vacuous negative-assertion（`_write_parsed_outputs` 从不调 `write_truth_file`，patch 拦截的符号永不分发），删 re-export 后 patch 目标不存在，整个 `with` 块失去意义。改后测试仍验证真实信号（whole-file 写入行为）。

**验证**：
- `pytest tests/unit/pipeline/test_dispatch_write_semantics.py -v` 全绿。
- `grep -n "import.*write_truth_file" src/shenbi/pipeline/dispatch_helper.py` 返回空（确认 re-export 行已删；docstring/comment 文本提及不在 grep 模式内）。

### Phase 4：全量验证 + CodeQL 重扫确认归零

1. `just check`（lint_status_strings + lint_repo_consistency + lint-contracts + ruff check + ruff format --check + mypy + basedpyright + shenbi-sync-contracts idempotency + pytest）。**基线**：2787 passed + 4 last-marked，85.03% coverage（PR #25 后 main 实测值）。**不回归**。
2. 推 branch，开 PR，等 CodeQL 扫描。**验收标准**：`py/cyclic-import` = **0**，`py/unused-import` 在 `dispatch_helper.py` = **0**。
3. 若 CodeQL 仍报残留：plan 阶段须列出每条的 file:line + 当前依赖路径，判断是否漏迁或环拓扑判断有误（回 §2 重新核实边）。

---

## 5. 验证标准（验收清单）

| # | 标准 | 命令 / 证据 |
|---|---|---|
| V1 | `just check` 全绿，测试数不回归（≥2787 passed） | `just check` 末尾 pytest 输出 |
| V2 | coverage 不回归（≥85.03%） | `just check` 覆盖率行 |
| V3 | codebase 内零 `# py/cyclic-import` 注释 | `grep -rn "py/cyclic-import" src/shenbi/` 返回空 |
| V4 | CodeQL `py/cyclic-import` 告警 = 0 | PR 的 CodeQL 扫描结果 |
| V5 | CodeQL `py/unused-import`（dispatch_helper.py:57）= 0 | 同上 |
| V6 | 被迁移符号的既有测试全绿 | Phase 1/2/3 各阶段 pytest |
| V7 | ruff/mypy/basedpyright 对新 `_shared` 模块全绿 | `just check` 内的 lint 阶段 |
| V8 | `__init__.py` 公开 API 不变（`AuditResult` 仍可 `from shenbi.audit import AuditResult`） | `python -c "from shenbi.audit import AuditResult; print(AuditResult)"` |

---

## 6. 待决策项（plan 阶段定，spec 只记选项）

### 6.1 `_shared.py` 命名

- **选项 A（推荐）**：`_shared.py`（下划线前缀表"包内私有，勿从外部直接 import"）。
- **选项 B**：按职责命名——`pipeline/_volume_map.py`（volume 解析域）、`audit/_contract_extract.py`（契约提取 + 审计结果类型）。语义更清晰但跨两个符号职责略杂。

### 6.2 `_BRIDGE_ACTIVATION_WINDOW` / `_resolve_volume_at_runtime` 是否保留 re-export

> 仅适用于这两个 `_`-前缀符号。`read_volume_boundaries` / `VOLUME_MAP_PATH` 的 re-export 是 **MANDATORY**（§3.2 已述 5 处运行时消费者），不在此决策项内。

- **选项 A（推荐）**：保留 re-export（成本极低，守未知外部 import）。
- **选项 B**：不保留（`_` 前缀本就不保证稳定，强制调用方迁移到 `_shared`）。

### 6.3 `write_truth_file` re-export 处置

- **选项 A（推荐）**：删 re-export + 改 test patch 路径（彻底，前提是 `dispatch_helper` 运行时零调用）。
- **选项 B**：保留但改为实际调用（若 plan 阶段发现确有调用点）。

### 6.4 PR 拆分

- **选项 A（推荐）**：单 PR（11 条告警同一根因簇，三 Phase 强相关，合并审阅更清晰）。
- **选项 B**：拆 3 PR（每 Phase 一个），降低单 PR 体量但增加 review 轮次。

---

## 7. 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 迁移符号时遗漏私有依赖（如 `_END_RE` 漏迁） | 中 | import error，pytest 即刻红 | Phase 1/2 后立即跑相关模块测试 |
| re-export 忘加导致外部 import 断裂 | 低 | `ImportError`，CI 红 | V8 显式验证 `__init__.py` 公开 API |
| CodeQL 对"图改变"判定与预期不符（如把 `_shared` 视为环的一部分） | 低 | 告警不归零 | V4 CodeQL 重扫；若残留，回 §2 重核边 |
| 同名 `AuditResult` 误迁移（迁成 `audit_layer.AuditResult`） | 低 | chapter_loop 类型错配 | §2.2 已消歧；Phase 2 改动前 grep 确认 `write_audit.AuditResult` 字段 |
| `write_truth_file` patch 路径改错（选项 A） | 中 | test 静默不再 patch 真实符号 | Phase 3 后跑 `test_dispatch_write_semantics.py` + 手查 mock 是否被调用 |

**回滚**：纯重构，无数据/契约/schema 变更。任一 Phase 失败直接 `git revert`，不影响其他。三 Phase 互相独立可分别回滚。

---

## 8. 不做的事（Out of Scope）

1. **不重构环内成员的核心职责**（如把 `dispatch_skill` 也下沉）——那会制造巨型 `_shared`，违反 §3.1 原则。
2. **不处理第 12 条 CodeQL false-positive**（非 cyclic/unused 类，需单独诊断）。
3. **不借机"顺便"优化 volume_map 解析逻辑**——本 spec 是纯迁移，行为零变更。任何逻辑改进另开 spec。
4. **不改 `audit_layer.AuditResult`**（同名异类，不在本环）。
5. **不动 `__init__.py` 的公开 API 声明**（只改内部 import 来源，公开 surface 保持稳定）。

---

## 9. 相关

- **Issue #24**：本 spec 的来源，跟踪这 10 + 1 条告警。
- **PR #25**（`56fe7e7`）：引入注释压制的 PR，§9 决策"no refactor, follow-up"。
- **`docs/superpowers/specs/archive/2026-08-01-eliminate-existing-warnings-plan.md`**：PR #25 的 plan，§9 同一决策。
- **CodeQL `py/cyclic-import` 文档**：图级别检查，不认 `# noqa`，唯一解法是改变依赖图拓扑。
