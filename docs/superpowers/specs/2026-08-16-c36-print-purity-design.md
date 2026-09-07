> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-07 · 设计审查修订：三类输出通道裁决 + ruff T20) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C36——窄根因小簇，独立成 spec）| **依赖:** 无 | **范围:** src/shenbi/cost/report.py、pipeline/cli.py、skill_utils/escalation/check.py、skill_utils/foreshadowing_recall/recall.py、AGENTS.md 豁免规则 | **核心洞察:** "No print() in framework code"是 AGENTS.md 成文铁则，但 CLI 输出的豁免边界从未成文——6 处 print 既违规又无人拦（无 lint），规则与执法双缺

# C36 · print() 违禁清理与框架纯度豁免成文（print-purity）

## 元信息
- 簇：C36（print() 违禁散点），3 条（D102 代表 + F324 + F616——两条 M 为 D102 的分点复述），最高严重度 P1，证据等级=实验佐证（git grep 实跑）
- 成员：D102、F324、F616
- 来源：d1 机械扫描 + Z3/Z6 深读（D102：`git grep -n "print(" -- 'src/shenbi/*.py'`，2 处 _text_fingerprint 子串误报已剔除）

## 背景与根因
AGENTS.md 规定框架代码（src/shenbi/）禁用 `print()`、统一 structlog，但没有定义"用户面 CLI 输出"的豁免边界，也没有 lint 执法。现状 6 处直用 print：
- `src/shenbi/cost/report.py:135,137`（成本报告人面输出）
- `src/shenbi/pipeline/cli.py:1065,1067`（pipeline CLI 状态输出）
- `src/shenbi/skill_utils/escalation/check.py:164`（F616：CLI 输出 vs 禁令的边界裁决条）
- `src/shenbi/skill_utils/foreshadowing_recall/recall.py:61`（F324 关联站点）

根因不是"有人写错"，而是**规则颗粒度缺失**：人面 CLI 工具的表格/汇总输出天然该走 stdout，但"哪些入口算 CLI、CLI 内是否允许 print、还是必须经统一 output helper"从未裁决，于是各文件自行其是且无 lint 拦截。

## 目标
1. 豁免边界一页成文：框架内用户面输出的唯一合法通道与豁免清单
2. 6 处 print 全部整改（换通道或入豁免）；lint 执法进 `just check`，违规即红

## 任务分解

> **修订（2026-09-07 · 设计审查后）**：确立**三类输出通道**裁决——① 日志走 structlog（唯一日志通道）；② 人面文本走 `console.echo`；③ **机器可读 stdout 是独立契约面**（skills 层以 `python -m shenbi.skill_utils.*` 消费 JSON stdout，见 audit T14 证据），走 `console.emit_json`，不得混标为"用户面文本"。lint 采用 ruff 内建 `T20`（flake8-print）+ `per-file-ignores` 豁免 `src/shenbi/console.py`（ruff 无自定义规则能力，自定义脚本降为最后手段）。

### R1 · 豁免规则裁决与成文（先裁决后动手）
- **裁决（定案，替代原 A/B 二选一）**：引入 `shenbi.console` 薄封装（≤30 行含类型注解，须过 mypy + basedpyright strict）：
  - `echo(msg: str, *, err: bool = False)` —— 人面文本，`err=True` 写 stderr（保 report.py:135 / cli.py:1067 的 stderr 语义）
  - `emit_json(obj: object) -> None` —— 机器可读 stdout（`print(json.dumps(obj))` 转发），供 skill_utils CLI 契约输出
  - **不设可测试性 hook**（capsys 直接拦截 print，hook 属 YAGNI）；模块是纯转发器，无状态
- AGENTS.md Python Conventions 修订为："No `print()` in framework code; user-facing text goes through `shenbi.console.echo` (err=True for stderr), machine-readable CLI stdout through `shenbi.console.emit_json`; use structlog for logging"；豁免面与三类通道枚举成文于 `docs/framework/logging.md`（该文件已存在）
- **验收**：规则文本合入（AGENTS.md + docs/framework/logging.md）；`git grep -n "print(" -- 'src/shenbi/*.py'` 命中集 ⊆ `src/shenbi/console.py` 且逐行与豁免清单对得上

### R2 · 6 处整改
- 人面文本 4 处改 `console.echo`：`cost/report.py:135`（err=True）、`:137`、`pipeline/cli.py:1065`、`:1067`（err=True）；structlog 记录保持不变（用户面输出，非日志）
- 机器 JSON 2 处改 `console.emit_json`：`escalation/check.py:164`、`foreshadowing_recall/recall.py:61`（stdout JSON 是 skill 调用契约，**不得**改 stderr/structlog）
- **验收**：`src/shenbi/` 内豁免面外 `print(` 零命中；`pytest tests/unit/test_console.py -q`（T1 层；capsys 断言 echo stdout/err 双流 + emit_json 输出 == json.dumps）
- INDEX #50 行的 file:line 摘要随落地 PR 同步为现行行号

### R3 · lint 执法
- ruff `select` 加 `"T20"`；`[tool.ruff.lint.per-file-ignores]` 加 `src/shenbi/console.py = ["T201", "T203"]`（对齐既有 BLE001 per-file-ignores 模式）。ruff 已由 justfile check、`.pre-commit-config.yaml` ruff hook、ci.yml 三处既有接线运行——**无需新增任何清单行，C25 合写面就此消解**（C25 仅在将来重排清单时与本项对账）
- `tools/lint_no_print.py` 自定义脚本降为最后手段：仅当 T20 语义与豁免需求冲突时启用，且须对齐 `tools/lint_no_fs_mutation.py` 的 pre-commit local hook 模式
- **验收**：非豁免文件临时加 `print("x")` → `just check` FAIL；`src/shenbi/console.py` 内加 print → PASS（per-file-ignores 生效）

## 验收（簇级）
- `just check` 全绿；D102/F324/F616 三条 merged-into D102 回写关闭
- 豁免规则被 AGENTS.md 引用（Python Conventions 节修订一句话）

## 风险
- 方案 A 引入新公共模块——保持 ≤30 行薄封装，避免演变为日志框架二源（structlog 仍是唯一日志通道，console 只管用户面文本）
- F324/F616 原为 M 级"待裁决"条——本 spec 的裁决即其关闭依据，无需另行处理

## 验证命令
- 违规扫描（D102 同口径）：`git grep -n "print(" -- 'src/shenbi/*.py'`（剔除 _text_fingerprint 子串误报后，命中集 = 豁免清单 ∅）
- lint 执法负例：非豁免文件临时加 `print("x")` → `just check` FAIL；豁免文件同操作 → PASS
- 输出可测性：`pytest tests/unit/test_console.py -q`（T1；capsys 断言 console.echo/emit_json）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`D102 <- F324, F616`
- 关联簇：lint 采用 ruff T20 内建规则，经既有 ruff 接线运行，无新清单行——C25 合写面已消解（其将来重排清单时对账即可）；AGENTS.md 修订行属本簇（Python Conventions 节一句话）
