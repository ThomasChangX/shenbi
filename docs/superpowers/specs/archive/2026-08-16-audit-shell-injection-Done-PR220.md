> **Date:** 2026-08-16 | **Status:** Done (PR #220 · 2026-09-17 · SDD 全周期) — 原 Design (Revised 2026-09-17 · SDD #64 阶段 3 审查修正：T1 修复模式单一化为 positional-arguments 模式、验收 1/3 离线化、T2.7 裁决 B 为默认、shellcheck 覆盖全部 *.sh) | **Severity:** 🟠 P1（F1031 just 标准入口任意命令执行）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C26）| **代表 finding:** F002 | **簇规模:** 11 条 | **严重度上限:** P1
> **范围:** justfile（recipe 参数引用）、run_pipeline.sh、README 快速开始 | **证据等级:** 实验佐证（Z9-a + Z10-review-r1 + T12 实证注入；F1031/T1205 verified）
> **与既有 spec 关系:** C31（注入/越权安全面）的包装层半——C31 管 g4 判定/symlink/env/phase 参数，本 spec 只管 shell/just 包装层

# C26 · shell/just 包装层注入与误用修复（shell-injection）

## 背景（根因 + 证据）

**根因**：包装层（justfile recipe、run_pipeline.sh）复用 shell 字符串拼接而非参数化调用——自然语言 prompt 作为 recipe 参数插值进 shell 命令即成命令注入面；无人值守脚本又与人工门设计冲突，形成平行状态操作路径。

代表证据：
- **F1031**（P1，verified）：just **全部** recipe 参数插值不做 shell 引用——`just dispatch shenbi-worldbuilding generative /tmp/round "prompt; rm -rf ~"` 中 `;`/`$()`/空格 即执行任意命令或拆散 argv。AGENTS.md 把 just 目标文档化为标准入口，每个用户都是攻击面
- **F002**（P1，代表）：run_pipeline.sh:66-86 stuck≥3 时 python3 直改 pipeline-state.json 的 step_index+1 清 retry_counts；:88-97 error|failed 且 grep 命中 escalation/gate/dispatch 即自动 approve——**ESCALATION 的人工介入设计被脚本吞掉**（AGENTS.md "no gate can be skipped" 契约面）
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
1. 全 recipe 审计：`just --list` + 逐 recipe 读参数用法；含参数的 recipe 改写为**唯一规定模式**（justfile 已有 `set positional-arguments := true`）：**recipe 体不使用 `{{param}}` 插值自然语言/flag 值，改用 shell 位置参数引用** `"$1"`/`"$2"`/`"${@:N}"`（如 `dispatch skill test_type round_dir *prompt:` 体改 `uv run shenbi-dispatch "$1" "$2" "$3" "${@:4}"`）——just 在 shell 解析前做文本替换，`{{ }}` 插值无法安全转义（单引号包裹 `'{{prompt}}'` 会被 prompt 内单引号提前闭合，**已否决**；`env()` 传递与 `set dotenv-load` 冲突且多参 recipe 不适用，**已否决**）。**前置：justfile 顶部加 `set shell := ["bash", "-cu"]`**——`${@:N}` 是 bash 语法，just 默认 `sh -cu` 在 Linux CI（dash）下 Bad substitution 直接断 dispatch。`{{name}}` 等非自然语言参数同模式统一处理，recipe 签名（参数名/默认值）保持不变——用户面零感知（例外：T2.8 给 pipeline-init 增补性加 `*args` 透传，见该条）
2. F1032：pipeline-init/review 的 flag 值（project_dir/feedback）同模式修复（含空格 feedback 可用）；条件拼接改为 shell 内**空值守卫 + bash-3.2 安全惯用法**：just 对带默认值参数恒按位传参、`$#` 恒定，**argc 判断无效**——须 `if [ -n "$N" ]` 判空；**数组拼接在 bash<4.4（macOS 系统 bash 3.2）+ `set -u` 下空数组展开报 unbound variable**——惯用法 pin 为分支拼接（`if [ -n "$3" ]; then uv run pipeline review "$1" "$2" --feedback "$3"; else uv run pipeline review "$1" "$2"; fi`）或 `${A[@]+"${A[@]}"}`，禁裸 `"${A[@]}"`
3. 回归测试：PATH-shim stub harness（先例 `tests/test_round_exec_injection.py` + `tests/round-exec.sh:31-33`）——stub 脚本把收到的 `"$@"` 原样 dump 到文件，断言 argv 字面量到达；覆盖 `;`、`$()`、反引号、单双引号、空格、中文六类样本 × 全部含参 recipe（**recipe 清单由 `just --summary` 机械派生**，禁手维护清单防新增 recipe 漏网；`${@:N}` 的 bash 依赖使 harness 必须在 bash-shell justfile 下运行，macOS/Linux 双环境语义一致）。`just --dry-run` 输出会剥 shell 引号、无法区分安全与不安全 recipe 体，**不作为充分证据**；`*prompt` 传递的 argv 形态 pin 为"每个 shell 词一个 argv 条目"（stub 断言据此写）

### T2 · run_pipeline.sh 修复
4. F003/F1013/T1205：`python3 -c` 拼接全部消灭——state 读取改 `python3 - "$PROJECT_DIR/pipeline-state.json" <<'PY'` heredoc argv 传参（解释器与脚本分离，路径零拼接，不新增 `shenbi.*` CLI 面）；JSON 解析改 python argv 解析（注意 `pipeline resume` stdout 混日志与 JSON，`python -m json.tool` 只吃纯 JSON 不适用——解析须从输出提取 JSON 段后 `json.loads`，消灭 grep -o）
5. F1035：set -e 下的关键命令加显式 `|| { echo FATAL; exit 1; }` 守卫，FATAL 分支可达（负样本：含单引号 PROJECT_DIR 必须得到响亮报错而非静默死）
6. T1203：STATUS/PHASE 提取改 JSON 解析（与第 4 项合并：消灭 grep-of-stdout 污染面）；崩溃路径机器状态行定为脚本自身输出的定界行（`SHENBI_STATUS:...`），**仅 smoke 工具自产自销，不改 src/shenbi/ 生产代码新增输出契约**
7. F002/F1014：**默认裁决 B**——脚本降级为 smoke 工具：删除自动 approve 与直改 state JSON 全部路径（stuck≥3 改为停下报告并退出、ESCALATION 一律停人工 checkpoint），头注释 + README 声明"禁止用于生产 checkpoint"。裁决 A（白名单 `--auto-approve` + 走正规命令推进 step_index）**不做**——`shenbi-phase` 现无推进 step_index 的子命令（start/pre-skill/post-skill/pre-score/post-score/finalize，phase_runner.py:433-458），A 隐含新 CLI 面，违反 YAGNI；若未来 C12（裸崩守卫）落地后需要无人值守，另立 spec
8. README 示例实测（F902/F1030）：pipeline-init 例子加 `*args` 透传（`--auto` CLI flag 真实存在，cli.py:1098-1101）或改写为真实可跑形式；逐条 dry-run 验证

### T3 · 防线
9. shellcheck 进 pre-commit/CI（现状：全仓零 shellcheck——非"若已有则确认"，是净新增；hook 用 `shellcheck-py/shellcheck-py` mirror（CI 可移植，不依赖本地 system），覆盖仓库全部 `*.sh`（`files: \.sh$`），含 run_pipeline.sh、tools/*.sh、tests/round-exec.sh；有效性边界显式声明：shellcheck 只看展开后的 shell 脚本，**不覆盖 justfile recipe 插值**——F1031 类回归由 T1.3 矩阵 harness + 第 10 项头注释规约守）；注入回归样本矩阵固化成测试（T1.3 harness 进 tests/）
10. justfile 侧无法完全静态保证——补一段 justfile 头注释规约："新增 recipe 收自然语言参数必须走 T1 模式"（编码规约 + review 检查项）

### 批量清理（M 级成员）
本簇无 M 级成员（11 条全 P1/P2）。

## 验收标准（真实数据可复验）

1. 注入矩阵实测（**离线**，F947 规则）：PATH-shim stub（dump argv 到文件，先例 tests/test_round_exec_injection.py）+ 六类样本（`;`/`$()`/反引号/单双引号/空格/中文）× 全部含参 recipe——零命令执行、argv 字面量到达 stub；**禁真实 dispatch 取证**；矩阵与结果记录进 PR
2. run_pipeline.sh：PROJECT_DIR 含单引号/空格/括号时行为 = 响亮报错退出（非静默死、非语法破坏）；注入样本（括号平衡恶意串）不再执行任意 Python（T1205 复现手法反向验证）——**离线**：**stub 目标必须是 `uv` 本身**（PATH 前置 fake `uv` wrapper，对 `run pipeline resume` 参数回放 canned 输出后转真 uv 或直接退出——`uv run` 会把项目 venv bin 前置到 PATH，stub `pipeline` 会被真入口遮蔽，**stub pipeline 无效**）+ 构造本地路径直接运行脚本
3. 自动 approve 已移除（裁决 B）：对含 ESCALATION 的 blocked/stuck 状态运行脚本（**离线**：伪造 pipeline-state.json + PATH 前置 fake `uv` wrapper 回放 canned 状态——见验收 2 注：stub pipeline 会被 venv 入口遮蔽）→ 停在人工 checkpoint 报告退出（不 approve、不改 step_index、无任何 state JSON 写路径）
4. README 快速开始逐条验证（**离线**：pipeline-init/--auto、pipeline-status、pipeline-review 等 argparse 层命令实跑或 stub 验证；pipeline-resume 类会触发真实 LLM 的命令以 `just --dry-run` 验证命令行形态即可，禁真实 dispatch），输出与文档描述一致
5. shellcheck 对仓库全部 `*.sh`（run_pipeline.sh、tools/pre-push-check.sh、tests/round-exec.sh、tests/lock-tool-hashes.sh、tests/test-gates.sh）零 error（warning 白名单显式）；justfile 头注释规约存在（T3.10）；`just check` 全绿

## 风险与回滚

- **风险**：just 参数改 positional 模式改变用户调用习惯（README/AGENTS.md 的示例命令同步改）——保留 recipe 签名不变、只改内部传递，用户面零感知为目标（唯一例外：pipeline-init 增补性 `*args` 透传使 README `--auto` 例子可跑，向后兼容）
- **风险**：run_pipeline.sh 收紧自动 approve 后长跑无人值守场景中断——无 opt-in（白名单 flag 已随裁决 A 一并否决，见 T2.7），显式接受；文档声明 smoke 定位
- **风险**：F002 裁决 B 后无人值守长跑能力消失——显式接受（smoke 工具定位），未来无人值守需求由 `pipeline resume` + 外部编排承担，另立 spec
- **回滚**：justfile 与 run_pipeline.sh 均单文件 revert；注入矩阵测试为纯新增

## 簇成员清单（11 条，自查用）

F002-F003, F902, F1013-F1014, F1030-F1032, F1035, T1203, T1205（代表 F002）
