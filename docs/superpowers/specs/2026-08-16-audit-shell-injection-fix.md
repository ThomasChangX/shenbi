> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1（F1031 just 标准入口任意命令执行）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C26）| **代表 finding:** F002 | **簇规模:** 11 条 | **严重度上限:** P1
> **范围:** justfile（recipe 参数引用）、run_pipeline.sh、README 快速开始 | **证据等级:** 实验佐证（Z9-a + Z10-review-r1 + T12 实证注入；F1031/T1205 verified）
> **与既有 spec 关系:** C31（注入/越权安全面）的包装层半——C31 管 g4 判定/symlink/env/phase 参数，本 spec 只管 shell/just 包装层

# C26 · shell/just 包装层注入与误用修复（shell-injection）

## 背景（根因 + 证据）

**根因**：包装层（justfile recipe、run_pipeline.sh）复用 shell 字符串拼接而非参数化调用——自然语言 prompt 作为 recipe 参数插值进 shell 命令即成命令注入面；无人值守脚本又与人工门设计冲突，形成平行状态操作路径。

代表证据：
- **F1031**（P1，verified）：just **全部** recipe 参数插值不做 shell 引用——`just dispatch shenbi-worldbuilding generative /tmp/round "prompt; rm -rf ~"` 中 `;`/`$()`/空格 即执行任意命令或拆散 argv。AGENTS.md 把 just 目标文档化为标准入口，每个用户都是攻击面
- **F002**（P1，代表）：run_pipeline.sh:73-91 stuck≥3 时 python3 直改 pipeline-state.json 的 step_index+1 清 retry_counts；:93-102 error|failed 且 grep 命中 escalation/gate/dispatch 即自动 approve——**ESCALATION 的人工介入设计被脚本吞掉**（AGENTS.md "no gate can be skipped" 契约面）
- **F902**（P1）：README pipeline-init 示例命令实测失败；F1030（P2）：README 快速开始 `--auto` 例子实跑即报错（just pipeline-init 不透传 flag）——入口文档给的命令跑不通
- **F003/F1013/T1205**（P2，T1205 实证升级）：run_pipeline.sh 用 `python3 -c` 拼接 `$PROJECT_DIR`——PROJECT_DIR 含单引号即语法破坏；**括号平衡前提可执行任意 Python**（T1205 复现）；`grep -o '"status"'` 解析 JSON 脆弱
- **F1014**（P2）：error 分支 `grep -q "escalation|gate|dispatch"` 过宽自动放行——框架错误消息普遍含这些词，error≠blocked 亦被 approve
- **F1035**（P2）：:26/:70-79 无守卫命令在 set -e 下静默死（FATAL 分支不可达——实测：含单引号路径时整脚本静默死而非报错）
- **T1203**（P2）：STATUS/PHASE 被 agent stderr 日志预览污染（崩溃路径无机器状态行）
- **F1032**（P2）：pipeline-init/review 的 just 表达式拼接 flag 值无引号——含空格 feedback 必致 argparse 失败

## 目标

1. **注入面封死**：just recipe 的自然语言参数全部经安全插值传递（`sh -c` 单命令串 + 变量引用，或参数化调用）；run_pipeline.sh 的 python 调用改 argv 传参 + JSON 工具解析
2. **人工门语义恢复**：run_pipeline.sh 的自动 approve/stuck 改状态机路径收敛为白名单或显式降级为 smoke 工具
3. 入口文档可执行：README 示例命令逐条实测通过

## 任务分解

### T1 · justfile 注入修复（P1 优先）
1. 全 recipe 审计：`just --list` + 逐 recipe 读参数用法；含自然语言参数（prompt/feedback/decision）的 recipe 改写——just 的参数插值默认不做 shell 引用，统一改为：
   - recipe 内单引号包裹 `'{{prompt}}'`（just 的 `{{ }}` 不展开单引号内再解释——注意 just 特有语义：插值发生在 shell 命令字符串层，需用 `"$@"`-型模式或 `sh -c` + env 传递）
   - 或推荐模式：`PROMPT := env("PROMPT")` / recipe 收参后经 `python -m` 入口 argv 传递，shell 层零自然语言拼接
2. F1032：pipeline-init/review 的 flag 值同模式修复（含空格 feedback 可用）
3. 回归测试：新增一个最小 harness（或 shellcheck + 手工矩阵）覆盖 `;`、`$()`、反引号、单双引号、空格、中文参数六类样本——每个 recipe 对六类样本行为为"字面量传参"而非执行/拆散

### T2 · run_pipeline.sh 修复
4. F003/F1013/T1205：`python3 -c` 拼接改 `python3 -m shenbi.<module> --arg "$PROJECT_DIR/..."` argv 传参；JSON 解析改 `python3 -m json.tool`/jq 提取（消灭 grep -o）
5. F1035：set -e 下的关键命令加显式 `|| { echo FATAL; exit 1; }` 守卫，FATAL 分支可达（负样本：含单引号 PROJECT_DIR 必须得到响亮报错而非静默死）
6. T1203：STATUS/PHASE 提取加定界（如取 JSON 字段而非日志 grep；崩溃路径输出机器可读状态行）
7. F002/F1014：自动 approve 策略改白名单（仅显式 `--auto-approve <type-list>` 允许的类型；ESCALATION 永不自动）+ stuck 处理改走 `shenbi-phase` 正规命令而非直改 state JSON；或裁决 B：脚本降级为 smoke 工具并在头注释+README 声明"禁止用于生产 checkpoint"
8. README 示例实测（F902/F1030）：pipeline-init 与 --auto 例子逐条跑通或改写为真实可跑形式

### T3 · 防线
9. shellcheck 进 pre-commit/CI（若已有则确认覆盖 run_pipeline.sh 与 tools/*.sh）；注入回归样本矩阵固化成测试（T1.3 的 harness 进 tests/ 或 tools/ 自检脚本）
10. justfile 侧无法完全静态保证——补一段 justfile 头注释规约："新增 recipe 收自然语言参数必须走 T1 模式"（编码规约 + review 检查项）

### 批量清理（M 级成员）
本簇无 M 级成员（11 条全 P1/P2）。

## 验收标准（真实数据可复验）

1. 注入矩阵实测：`just dispatch <skill> <type> <dir> "prompt; echo PWNED"` 等六类样本 × 全部含参 recipe——零命令执行、argv 完整到达（dispatch 日志中 prompt 原样可见）；矩阵与结果记录进 PR
2. run_pipeline.sh：PROJECT_DIR 含单引号/空格/括号时行为 = 响亮报错退出（非静默死、非语法破坏）；注入样本（括号平衡恶意串）不再执行任意 Python（T1205 复现手法反向验证）
3. 自动 approve：对含 ESCALATION 的 stuck 状态运行脚本 → 停在人工 checkpoint（不 approve、不改 step_index）；白名单机制实测一类允许、其余拦截
4. README 快速开始逐条复制可跑（pipeline-init、--auto 例子），输出与文档描述一致
5. shellcheck 对 run_pipeline.sh + tools/*.sh 零 error（warning 白名单显式）；`just check` 全绿

## 风险与回滚

- **风险**：just 参数改 env/argv 模式改变用户调用习惯（README/AGENTS.md 的示例命令同步改）——保留 recipe 签名不变、只改内部传递，用户面零感知为目标
- **风险**：run_pipeline.sh 收紧自动 approve 后长跑无人值守场景中断——提供显式 opt-in（白名单 flag）+ 文档说明，不静默恢复旧行为
- **风险**：F002 改走 shenbi-phase 正规命令引入对 CLI 稳定性的依赖——CLI 面改动与 C12（裸崩守卫）排期协调
- **回滚**：justfile 与 run_pipeline.sh 均单文件 revert；注入矩阵测试为纯新增

## 簇成员清单（11 条，自查用）

F002-F003, F902, F1013-F1014, F1030-F1032, F1035, T1203, T1205（代表 F002）
