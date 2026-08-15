> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C36——窄根因小簇，独立成 spec）| **依赖:** 无 | **范围:** src/shenbi/cost/report.py、pipeline/cli.py、skill_utils/escalation/check.py、skill_utils/foreshadowing_recall/recall.py、AGENTS.md 豁免规则 | **核心洞察:** "No print() in framework code"是 AGENTS.md 成文铁则，但 CLI 输出的豁免边界从未成文——6 处 print 既违规又无人拦（无 lint），规则与执法双缺

# C36 · print() 违禁清理与框架纯度豁免成文（print-purity）

## 元信息
- 簇：C36（print() 违禁散点），3 条（D102 代表 + F324 + F616——两条 M 为 D102 的分点复述），最高严重度 P1，证据等级=实验佐证（git grep 实跑）
- 成员：D102、F324、F616
- 来源：d1 机械扫描 + Z3/Z6 深读（D102：`git grep -n "print(" -- 'src/shenbi/*.py'`，2 处 _text_fingerprint 子串误报已剔除）

## 背景与根因
AGENTS.md 规定框架代码（src/shenbi/）禁用 `print()`、统一 structlog，但没有定义"用户面 CLI 输出"的豁免边界，也没有 lint 执法。现状 6 处直用 print：
- `src/shenbi/cost/report.py:93,95`（成本报告人面输出）
- `src/shenbi/pipeline/cli.py:945,947`（pipeline CLI 状态输出）
- `src/shenbi/skill_utils/escalation/check.py:149`（F616：CLI 输出 vs 禁令的边界裁决条）
- `src/shenbi/skill_utils/foreshadowing_recall/recall.py:61`（F324 关联站点）

根因不是"有人写错"，而是**规则颗粒度缺失**：人面 CLI 工具的表格/汇总输出天然该走 stdout，但"哪些入口算 CLI、CLI 内是否允许 print、还是必须经统一 output helper"从未裁决，于是各文件自行其是且无 lint 拦截。

## 目标
1. 豁免边界一页成文：框架内用户面输出的唯一合法通道与豁免清单
2. 6 处 print 全部整改（换通道或入豁免）；lint 执法进 `just check`，违规即红

## 任务分解
### R1 · 豁免规则裁决与成文（先裁决后动手）
- 两个候选方案（推荐 A）：
  - **A（推荐）**：引入 `shenbi.console`（薄封装：print 或 rich 转发 + 可测试性 hook），仅 `console.echo()` 允许产出用户面文本；AGENTS.md 修订为"No print() in framework code; user-facing output goes through shenbi.console"
  - **B**：完全豁免 `*/cli.py` 与 `*报告 main()` 的 print，lint 白名单按文件路径
- 无论 A/B：豁免对象枚举成文（docs/framework/logging.md 或 AGENTS.md 附注），非豁免面 print 为违规
- **验收**：规则文本合入；`git grep -n "print(" -- 'src/shenbi/*.py'` 与豁免清单逐行对得上

### R2 · 6 处整改
- 方案 A：4 文件 6 处改 `console.echo`；structlog 记录保持不变（这是用户面输出，非日志）
- 方案 B：escalation/check.py:149 与 recall.py:61 若非 CLI 入口（D102 证据显示二者为模块级 main），改 structlog `logger.info` 或补 CLI 入口后豁免
- **验收**：豁免清单外 `git grep -n "print(" -- 'src/shenbi/'` 零命中；`just test` 输出捕获用例（console.echo 可被 capsys 断言）

### R3 · lint 执法
- ruff 自定义规则或 `tools/lint_no_print.py`（若 ruff 不支持路径级豁免语义）：扫描 src/shenbi 非豁免面 print；接入 justfile check recipe 与 ci.yml（挂 C25 同步簇——由其统一 CI/just 清单，本 spec 只提供检查器）
- **验收**：故意在非豁免文件加 print → `just check` FAIL；豁免文件加 print → PASS

## 验收（簇级）
- `just check` 全绿；D102/F324/F616 三条 merged-into D102 回写关闭
- 豁免规则被 AGENTS.md 引用（Python Conventions 节修订一句话）

## 风险
- 方案 A 引入新公共模块——保持 ≤30 行薄封装，避免演变为日志框架二源（structlog 仍是唯一日志通道，console 只管用户面文本）
- F324/F616 原为 M 级"待裁决"条——本 spec 的裁决即其关闭依据，无需另行处理

## 验证命令
- 违规扫描（D102 同口径）：`git grep -n "print(" -- 'src/shenbi/*.py'`（剔除 _text_fingerprint 子串误报后，命中集 = 豁免清单 ∅）
- lint 执法负例：非豁免文件临时加 `print("x")` → `just check` FAIL；豁免文件同操作 → PASS
- 输出可测性：`pytest tests/unit/ -k console -q`（capsys 断言 console.echo）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`D102 <- F324, F616`
- 关联簇：lint 接入 ci.yml/justfile 的清单同步归 C25；AGENTS.md 修订行属本簇（Python Conventions 节一句话）
