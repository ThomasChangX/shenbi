> **Date:** 2026-08-16 | **Status:** Done (PR #176, 2026-09-07; Revised 2026-09-07 · 重审两轮：三类输出通道裁决 + 复用 cli_utils + ruff T20) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C36——窄根因小簇，独立成 spec）| **依赖:** 无 | **范围:** src/shenbi/cli_utils.py、cost/report.py、pipeline/cli.py、skill_utils/escalation/check.py、skill_utils/foreshadowing_recall/recall.py、AGENTS.md 豁免规则、pyproject.toml（ruff T20）| **核心洞察:** "No print() in framework code"是 AGENTS.md 成文铁则，但 CLI 输出的豁免边界从未成文——6 处 print 既违规又无人拦（无 lint），规则与执法双缺

# C36 · print() 违禁清理与框架纯度豁免成文（print-purity）

## 元信息
- 簇：C36（print() 违禁散点），3 条（D102 代表 + F324 + F616——两条 M 为 D102 的分点复述），最高严重度 P1，证据等级=实验佐证（git grep 实跑）
- 成员：D102、F324、F616
- 来源：d1 机械扫描 + Z3/Z6 深读（D102：`git grep -n "print(" -- 'src/shenbi/*.py'`，3 处 _text_fingerprint 子串误报已剔除（chapter_drafting.py:133,141,320））

## 背景与根因
AGENTS.md 规定框架代码（src/shenbi/）禁用 `print()`、统一 structlog，但没有定义"用户面 CLI 输出"的豁免边界，也没有 lint 执法。现状 6 处直用 print：
- `src/shenbi/cost/report.py:135,137`（成本报告人面输出）
- `src/shenbi/pipeline/cli.py:1065,1067`（pipeline CLI 状态输出）
- `src/shenbi/skill_utils/escalation/check.py:164`（F616：CLI 输出 vs 禁令的边界裁决条）
- `src/shenbi/skill_utils/foreshadowing_recall/recall.py:61`（F324 关联站点）

根因不是"有人写错"，而是**规则颗粒度缺失**：人面 CLI 工具的表格/汇总输出天然该走 stdout，但"哪些入口算 CLI、CLI 内是否允许 print、还是必须经统一 output helper"从未裁决，于是各文件自行其是且无 lint 拦截。

> **修订 2（2026-09-07 · 重审轮 2）**：撤销新建 `shenbi.console`——既有 `src/shenbi/cli_utils.py` 已含 `emit_json(data)`（`sys.stdout.write` + `ensure_ascii=False` + flush + `BrokenPipeError→SystemExit(0)`，8 个生产消费方：gates/cli、scoring、phase_runner、pipeline/cli、context_assemble、truth_embed、truth_index、dispatcher/modes/codex）且其 docstring 已裁决 stdout/stderr 通道分工。本 spec 改为**扩展 cli_utils**：新增 `echo(msg, *, err=False)`（对齐 emit_json 的 write/flush/BrokenPipe 语义，不用 print），6 处全部迁入；src/shenbi 对 T20 因此可达成**零 per-file-ignores**。lint 采用 ruff 内建 `T20`，豁免仅在框架外（tools/scripts/tests）。
>
> **修订 1（2026-09-07 · 设计审查）**：确立**三类输出通道**裁决——① 日志走 structlog（唯一日志通道）；② 人面文本走 `cli_utils.echo`；③ **机器可读 stdout 是独立契约面**（skills 层以 `python -m shenbi.skill_utils.*` 消费 JSON stdout，见 audit T14 证据），走 `cli_utils.emit_json`，不得混标为"用户面文本"。机器 stdout 的合法形态 = `cli_utils.emit_json` 或直接 `sys.stdout.write`（chapter_pattern/calibration 等既有 `sys.stdout.write` 站点合法、不在本 spec 迁移面）；**禁止的只是 `print()`**。

## 目标
1. 豁免边界一页成文：框架内三类输出通道的裁决与豁免清单
2. 6 处 print 全部整改（换通道）；lint 执法（ruff T20），src/shenbi 违规即红且零豁免

## 任务分解

### R1 · 豁免规则裁决与成文（先裁决后动手）
- **裁决（定案）**：扩展 `src/shenbi/cli_utils.py`（既有模块，非新建）：
  - 新增 `echo(msg: str, *, err: bool = False) -> None` —— 人面文本；`err=True` 写 stderr（保 report.py:135 / cli.py:1067 的 stderr 语义）。实现**对齐同文件 emit_json**：`(sys.stderr if err else sys.stdout).write(msg + "\n")` + flush + `BrokenPipeError → SystemExit(0)`——**不用 print**，故 src/shenbi 无需任何 per-file-ignores
  - 机器 JSON 复用既有 `emit_json`（`ensure_ascii=False` 语义保 check.py:164 中文 detail 字节级不变——**不得**引入 print/ensure_ascii 默认值回归）
  - 不设可测试性 hook（capsys 直接拦截 write/print，hook 属 YAGNI）；模块保持纯函数、无状态，过 mypy + basedpyright strict；echo 继承流编码（与 emit_json 同性质，非 UTF-8 locale 下中文同抛 UnicodeEncodeError——接受该一致性，不另行处理）
- AGENTS.md Python Conventions 修订一句："No `print()` in framework code (enforced by ruff T20, zero exemptions in src/shenbi); user-facing text goes through `shenbi.cli_utils.echo` (`err=True` for stderr), machine-readable CLI stdout through `shenbi.cli_utils.emit_json` or direct `sys.stdout.write`; use structlog for logging."；三类通道枚举成文于 `docs/framework/logging.md`（既有 5 行 stub，扩充为通道裁决正文；`docs/api/logging.md` 引用保持一致）
- **验收**：规则文本合入（AGENTS.md + docs/framework/logging.md）；`git grep -n "print(" -- 'src/shenbi/'` 剔除 `_text_fingerprint` 子串误报后**零命中**

### R2 · 6 处整改
- 人面文本 4 处改 `cli_utils.echo`：`cost/report.py:135`（err=True）、`:137`、`pipeline/cli.py:1065`、`:1067`（err=True）；structlog 记录保持不变（用户面输出，非日志）
- 机器 JSON 2 处改 `cli_utils.emit_json`：`escalation/check.py:164`（现已是 `ensure_ascii=False`，字节级不变）、`foreshadowing_recall/recall.py:61`（现为默认 `ensure_ascii=True`，迁入后**有意变更**为非转义 UTF-8，与 check.py 对齐——JSON 语义等价；recall CLI 的活消费方实为**零**：唯一相关 skill `shenbi-foreshadowing-recall` 已 DEPRECATED 且其流程直调 `recall_overdue_hooks` 不走 CLI stdout，故无字节敏感比对面；该模块存废另归 C37 裁决，本 spec 只迁通道不改去留）。两处均**不得**改 stderr/structlog 通道
- **验收**：`src/shenbi/` 内 `print(` 零命中（同上口径）；`pytest tests/unit/test_cli_utils.py -q`（T1 层；capsys 断言 echo stdout/err 双流 + emit_json 输出 `== json.dumps(obj, ensure_ascii=False) + "\n"`）
- INDEX #50 行的 file:line 摘要随落地 PR 同步为现行行号

### R3 · lint 执法
- ruff `select` 加 `"T20"`；`[tool.ruff.lint.per-file-ignores]` 框架外豁免三条（键加引号）：新增 `"tools/**" = ["T201"]`、`"scripts/**" = ["T201"]`，既有 `"tests/**" = ["BLE001"]` **合并为 `["BLE001", "T201"]`**（TOML 禁重复键，实测 ruff 遇 duplicate key 直接 config parse 失败）（tools/scripts 是 CLI 脚本、tests 有审计记录型 print，均合法人面输出；实跑基线：tools/scripts 83 处、tests 6 个文件 34 处均为存量合法；ruff 对多条匹配 per-file-ignores 取并集，无遮蔽）。src/shenbi 对 **T20 零豁免**（其既有 ~23 条 BLE001 per-file-ignores 属 spec #39 吞错豁免面，与本项无关）。ruff 已由 justfile check、`.pre-commit-config.yaml` ruff hook、ci.yml 三处既有接线运行——无需新增任何清单行，C25 合写面就此消解（C25 将来重排清单时对账即可）
- `tools/lint_no_print.py` 自定义脚本降为最后手段，仅在 T20 语义与豁免需求冲突时启用
- **验收**：src/shenbi 任一文件临时加 `print("x")` → `just check` FAIL；`tools/` 内 print 存量 → PASS

## 验收（簇级）
- `just check` 全绿；D102/F324/F616 三条 merged-into D102 回写关闭
- 豁免规则被 AGENTS.md 引用（Python Conventions 节修订一句话）

## 风险
- 扩展既有公共模块而非新建——增量 ≤15 行纯函数，不演变为日志框架二源（structlog 仍是唯一日志通道，cli_utils 只管 CLI 输出面）
- F324/F616 原为 M 级"待裁决"条——本 spec 的裁决即其关闭依据，无需另行处理

## 验证命令
- 违规扫描（D102 同口径）：`git grep -n "print(" -- 'src/shenbi/*.py'`（剔除 3 处 _text_fingerprint 子串误报后命中集 = ∅）
- lint 执法负例：src/shenbi 任一文件临时加 `print("x")` → `just check` FAIL；tools/ 存量 print → PASS
- 输出可测性：`pytest tests/unit/test_cli_utils.py -q`（T1；capsys 断言 echo/emit_json）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`D102 <- F324, F616`
- 关联簇：lint 采用 ruff T20 内建规则，经既有 ruff 接线运行，无新清单行——C25 合写面已消解；AGENTS.md 修订行属本簇（Python Conventions 节一句话）
