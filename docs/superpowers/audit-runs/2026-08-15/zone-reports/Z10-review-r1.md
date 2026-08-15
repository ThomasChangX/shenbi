# Z10 区第 1 轮复核报告（fresh context）

- 轮次: R1（标准双角度复核）
- 角度: (a) justfile ↔ workflows ↔ 文档三方调用形状对账（含 recipe 变量展开/缺省值语义，实跑 `just --dry-run` 与 CLI help）；(b) run_pipeline.sh / tools / scripts 全部 shell+python 脚本的语义边界（set -e 交互、未加引号展开、管道失败、exit code 传播、引用断链重扫）
- 编号段: 新增 F1030–F1036（7 条）；复读 F1001–F1029（29 条）
- 只读声明: 除本报告外未创建/修改/删除任何仓库文件；未运行 pytest、未运行 shenbi-dispatch / pipeline 子命令（pipeline init --help 为 argparse 帮助输出，不触发任何 cmd_* 逻辑）；未做 git 写操作。验证用临时文件全部位于 /tmp/z10r1/（含复制 justfile recipe 的语义复现实验）。
- 审查日期: 2026-08-15

## 总体结论

初审 29 条**零误报**——逐条复读代码事实后未发现任何一条与仓库现状矛盾；其中 3 条初审标注"未验证"（F1007/F1013/F1015）本轮以实跑或上游源码取证升级为 verified。但初审方法存在两个系统性盲区：**(1) 全部 justfile/脚本检查为静态读，从未实跑 just 或复现 bash 语义**，导致 recipe 插值不引用（shell 注入，F1031，本轮唯一新 P1）与 set -e 静默死（F1035/F1036）不可见；**(2) Z10.files 不含 command-to-give.md / README.md / docs/skills/index.md**（归 Z9），三方对账缺文档腿，导致 README 快速开始命令直接报错（F1030）、执行协议引用已删除脚本（F1034）、四文档技能计数漂移（F1033）漏报。

新发现 7 条：P1×1（F1031）、P2×6。收敛判定：**未收敛**（第 1 轮复核仍产出 1 条 P1，且新产出集中在初审方法结构性覆盖不到的"动态语义"面）。

---

## 一、漏报（新 finding，F1030–F1036）

### F1030 | README 快速开始 `just pipeline-init ... --auto` 直接报错：recipe 不支持透传 `--auto` | 漏报 | P2

- **证据**（实跑）:
  - `just --dry-run pipeline-init outline-example.md ./my-novel --auto` → `error: justfile does not contain recipe '--auto'`，RC=1
  - `just --dry-run pipeline-init outline-example.md ./my-novel` → `uv run pipeline init outline-example.md --project-dir ./my-novel`，RC=0
  - README.md:46（Pipeline 运行一节的第一个示例命令）: `just pipeline-init outline-example.md ./my-novel --auto`
  - justfile:102-103: `pipeline-init seed project_dir=""` —— 固定两参，无条件透传
  - `uv run pipeline init --help`：CLI 本身**支持** `--auto`（"Reduce checkpoints for automated/Codex-driven runs"）
- **根因**: 三方形状断裂——CLI 支持 `--auto`，README 照 CLI 写，justfile recipe 未加可选透传（如 `*extra_args`）。三方中 nobody 对齐。
- **验证**: 上列命令实跑输出（非推断）。
- **影响面**: README "Pipeline 运行" 章节全部 4 条命令中的第 1 条 100% 报错；自动化/Codex 运行模式（--auto 的目标场景）经 just 完全不可达，只能绕过 just 直接调 `uv run pipeline init`。
- **建议方向**: recipe 增加 `*extra` 透传段并用位置参数拼接，或 README 删除 `--auto`（并补一条 `--auto` 的直接 CLI 用法）。

### F1031 | just 全部 recipe 的参数插值不做 shell 引用 → dispatch 的自然语言 prompt 含元字符时执行任意命令/断参 | 漏报 | P1

- **证据**（实跑，复现 recipe 字节级同构）:
  - justfile:2-3 `set dotenv-load := true` + `set positional-arguments := true`；justfile:66-67 `dispatch skill test_type round_dir *prompt:` → `uv run shenbi-dispatch {{skill}} {{test_type}} {{round_dir}} {{prompt}}`
  - 在 /tmp/z10r1/ 用相同 settings 与相同 recipe 形状复现（just 1.52.0）：
    - `just dispatch a b c "x1; touch /tmp/z10r1/injected" 'y$(echo z)'` → 实际执行后 `/tmp/z10r1/injected` 与 `/tmp/z10r1/yz` **两个文件被创建**（`;` 命令分隔与 `$( )` 命令替换都被 shell 解释）
    - 单值参数同样不引用：`just dispatch "a;touch /tmp/z10r1/s1" b c p1` → `/tmp/z10r1/s1` 被创建
    - `just --dry-run dispatch shenbi-worldbuilding generative /tmp/round "prompt with spaces"` → `uv run shenbi-dispatch shenbi-worldbuilding generative /tmp/round prompt with spaces`（prompt 被拆成 3 个 argv）
  - 受保护的真实 recipe 未直接执行（铁则禁止 shenbi-dispatch）；复现 recipe 与 justfile:66-67 参数结构/插值位置逐字一致，且 --dry-run 对真实 recipe 的展开形态已单独取证。
- **根因**: just 1.52 对 `{{param}}` 插值（单值与变参 alike）不做 shell quoting，recipe 行整体交 sh 解释；repo 内没有任何 `{{quote(...)}}` 或 `"$@"` 用法。AGENTS.md:Key Commands 将 `just dispatch <skill> <type> <round> "<prompt>"` 文档化为标准 dispatch 入口，而 prompt 按定义是自然语言（引号/括号/`$`/反引号是中文与英文 prompt 的常见字符）。
- **验证**: 上列实跑文件创建结果 + `just --version` = 1.52.0。
- **影响面**: (1) 功能面——prompt 含空格时 shenbi-dispatch 收到的 argv 已被拆散（多余位置参数），含引号/`$` 时 prompt 被静默截断或改写 → **静默错误的 dispatch 输入**；(2) 安全面——prompt/skill/round_dir 中的元字符在调用者无预期的情况下执行任意 shell 命令（本框架中 prompt 常来自 scenario/LLM 产出，不是调用者手敲）。同构风险覆盖 `gate`（`{{args}}` 变参）与全部 `pipeline-*` recipe。
- **建议方向**: recipe 行改用位置参数形态（`positional-arguments` 已开启，`"$1" "$2" "$3"` + `shift 3; "$@"` 天然安全）；或单值参数用 `{{quote(x)}}`。

### F1032 | pipeline-init / pipeline-review 的 just 表达式把 flag 值字符串拼接进命令行，含空格值必断参 | 漏报 | P2

- **证据**（实跑）:
  - `just --dry-run pipeline-review ./my-novel approve "some feedback here"` → `uv run pipeline review ./my-novel approve --feedback some feedback here`（6 个词）
  - src/shenbi/pipeline/cli.py:985-989（review 子命令 argparse 定义）: 仅 2 个 positional（project_dir, decision）+ `--feedback` 单值 → `feedback`、`here` 成为多余 positional，argparse 报 `unrecognized arguments` RC=2
  - justfile:111: `{{ if feedback != "" { "--feedback " + feedback } else { "" } }}` —— 裸字符串拼接，无引号；justfile:103 的 `--project-dir ` 拼接同理（初审在 justfile 小节把 pipeline-init 一例记为 "M 级观察" prose，未立案，且未覆盖 review）
- **根因**: just 表达式输出直接进入 shell 行；`--feedback` 后的值未加引号。feedback 按用途就是自然语言句子（AGENTS.md: `just pipeline-review <dir> <decision>`，README 示例 `just pipeline-review ./my-novel approve`），含空格是常态而非边界。
- **验证**: --dry-run 输出 + argparse 定义并读（未运行 pipeline review 子命令本身）。
- **影响面**: 任何含空格的 feedback / project_dir 经 just 调用必失败；`--project-dir ./my novel` 类路径同理。
- **建议方向**: `{"--feedback " + "'" + feedback + "'"}` 不可靠（内嵌引号），应改为 recipe 用 `"$4"` 位置参数或 just 的 shell 内嵌 `--feedback {{quote(feedback)}}`。

### F1033 | 技能计数四文档漂移：59 / 67 / 69 / 69 vs 磁盘 74（F1023 只抓到 AGENTS.md 一处） | 漏报 | P2

- **证据**（文件行号 + 实跑）:
  - command-to-give.md:85（第五步）: "全部 59 个 skill 的 generative、bug-hunt、clean 均 ≥ 94 → 开始 T2"
  - README.md:16/:18/:22: "67 个写作技能"；README.md:88: "全部 69 个技能的完整目录"
  - docs/skills/index.md:3-5: "67 个写作技能和 2 个元技能"；:189: "Total unique skills: 69"
  - `ls skills | wc -l` → **74**（本轮实跑；与初审 F1023 的磁盘数一致）
  - 对照：deps.json 由 `shenbi-sync-contracts` 从 `ALL_SKILLS`（gates/shared.py:240，动态枚举 skills/ 目录）再生成且 CI 幂等门守护（ci.yml:81,88），故 deps.json 侧是新鲜的——4 处文档计数全部落后于受 CI 保护的生成物
- **根因**: 计数为手写 prose，无生成或 lint 约束；技能库从 59→69→74 演进时各文档停留在不同历史点。
- **验证**: 上列行号并读 + ls 计数实跑。
- **影响面**: 最重是 command-to-give.md 的 59——它是 AGENTS.md 指认的执行协议（"Execution protocol"），T1→T2 推进判据按 59 计会把 15 个技能排除在 T1 门之外；README 的 67/69 并存还自相矛盾（同一文档两个数）。
- **建议方向**: 四处计数改为引用单一来源（deps.json 派生数）或由 lint_repo_consistency 增加计数一致性检查；至少统一为当前值并注明"以 deps.json 为准"。

### F1034 | command-to-give.md:48 引用已删除的 tests/dispatch-subagent.sh（执行协议核心步骤的死引用） | 漏报 | P2

- **证据**（实跑命令输出）:
  - `ls tests/dispatch-subagent.sh` → `No such file or directory`
  - `git log --oneline --all -- tests/dispatch-subagent.sh` → `0f68102 feat(P-1.E PR-22): rename novel-output → skill-output + delete dispatch shim`（先于 PR-20 已缩为 4 行 shim，PR-22 删除）
  - 全仓 grep "dispatch-subagent"（排除 audit-runs）：唯一活引用 = command-to-give.md:48（"使用 `bash tests/dispatch-subagent.sh <skill> generative <round_dir> \"<prompt>\"`"）
- **根因**: dispatch 体系迁移到 `shenbi-dispatch`（ADR 0009）后，执行协议文档第 6 步（每个 generative 测试的评分 subagent 派发）未同步改写。
- **验证**: ls/git log/grep 三命令实跑。
- **影响面**: command-to-give.md 的 Generative 协议第 6 步是每个 T1 skill 必经步骤；按文档执行会在第一次评分派发时 bash 报错。替换入口已存在（`just dispatch` / `shenbi-dispatch`），但协议未指向它。
- **建议方向**: :48 改为 `just dispatch <skill> generative <round_dir> "<评分指令>"` 或 `uv run shenbi-dispatch ...`。注：command-to-give.md 归 Z9 区文件清单——若 Z9 已立案则并号，未立案则本条补位（跨区协查）。

### F1035 | run_pipeline.sh :26 与 :70-79 无守卫命令在 set -euo pipefail 下静默死，`*)  FATAL` 分支对最常见失败形态不可达 | 漏报 | P2

- **证据**（实跑复现，脚本行复制到 /tmp/z10r1/pipe-test.sh、interp-test.sh）:
  - :26 `STATUS=$(echo "$OUTPUT" | grep -o '"status": "[^"]*"' | tail -1 | cut -d'"' -f4)` 无 `|| echo ""` 守卫（:27 CP、:28 PHASE 都有）。复现：OUTPUT 无 status JSON → 脚本 RC=1 退出、**无任何输出**（"SHOULD NOT REACH HERE" 未打印）——grep 无匹配 RC=1 → pipefail → 赋值失败 → set -e 终止，stderr 亦无提示
  - :70-79 卡死推进分支的内嵌 python3 无 `|| true` 且 `2>/dev/null` 吞 stderr。复现：PROJECT_DIR 含单引号（F1013 场景）→ python 语法错误 → 脚本 RC=1 静默死，最后一条日志停在 "STUCK: ... Advancing past it."，无错误信息
  - 对照：:99-101 的 `*) log "FATAL: unexpected status"` 只能捕获"匹配到 status 但值未知"的情形；最常见的"输出里根本没有 status"（uv 环境错、网络错、非 JSON traceback）走不到任何 log
- **根因**: 错误路径守卫不一致（:27/:28 防了，:26/:70-79 没防），作者默认命令替换失败不会传播——pipefail 下会。F1013（$PROJECT_DIR 内插）只覆盖了"语法错误被吞"，未覆盖"set -e 使整脚本无日志终止"。
- **验证**: 两个 replica 实跑 RC=1 且零输出（见 /tmp/z10r1/）；bash 版本为 macOS 自带。
- **影响面**: run_pipeline.sh 的自我定位是无人值守自动推进（auto-approve、stuck 检测），静默死意味着夜跑无人发现、pipeline.log 尾部无死因；一切 `uv run pipeline resume` 非 JSON 输出（uv 自身报错、超时、包未装）都触发。
- **建议方向**: :26 加 `|| true` 后统一走 `*)` 分支报 FATAL；:70-79 的 python 失败要么显式 log+exit 非零，要么 `|| { log "advance failed"; exit 1; }`——关键是死前必须留一行日志。

### F1036 | pre-push-check.sh:74 死代码计数管道在零命中时被 set -e 整钩击穿：检查的理想态（0 个抑制）反而令 pre-push 崩溃 | 漏报 | P2

- **证据**（实跑复现，管道原样复制到 /tmp/z10r1/unused-test.sh）:
  - `set -euo pipefail` 下 `UNUSED_COUNT=$(grep -r 'reportUnusedFunction' src/shenbi/ --include='*.py' | grep -v test_ | grep -v __pycache__ | wc -l | tr -d ' ')`：在无匹配目录运行 → **RC=1 整脚本终止**（grep -r 零命中 RC=1 → pipefail → 赋值失败 → set -e）；"all lines 含 test_" 被 `grep -v` 过滤空的形态同理
  - 真实仓库当前计数实测 = 13（走 WARNING 分支，当前绿）——与 pyproject 各处"P-1.D/PR-25 清理后移除抑制"的路线图对照，清零之日即 hook 崩溃之时
- **根因**: 管道作者防了"if 比较"却没防"赋值本身"；注释自述 "仅 WARNING 非阻断" 与零命中即崩的实际语义相反。
- **验证**: replica 实跑 RC=1；真实仓库 13 的计数实跑。
- **影响面**: tools/pre-push-check.sh 是 AGENTS.md PR 协议第 1/4 条的执行体（"不通过不 push"）；清理完 reportUnusedFunction（仓库明示目标态）后每次 push 都会被无提示击穿，且错误信息完全不指向根因（set -e 无输出）。
- **建议方向**: 管道尾部加 `|| true`（wc 兜底为 0），或改 `grep -r ... || true | ...`。

---

## 二、误报 / 事实修正（F1001–F1029 逐条复读）

**结论：29 条中 0 条整条误报。** 逐条代码事实复读结果：

| 编号 | 复读结果 | 本轮补充证据 |
|---|---|---|
| F1001 | 成立 | 实跑 `grep -rn "lint_contract_graph\|lint_contract_fields" .github/ .pre-commit-config.yaml tools/pre-push-check.sh` → RC=1（零接线）；ci.yml:53-56 vs justfile:52-55 并读 |
| F1002 | 成立 | justfile:14-24 与 ci.yml:44-45/57-60/83 并读复核。**补充事实**：AGENTS.md PR 协议给出的"等价命令"（ruff+format+mypy+basedpyright+`pytest -n auto -m "not last" --cov-fail-under=85`）除缺 lint 外还缺 `-m "last"` 第二段 pytest——"等价"双向都不成立，建议并入 F1002 描述 |
| F1003 | 成立 | `git ls-files .codex-plugin/` → 0；`git check-ignore -v .codex-plugin/` → `.gitignore:20`；目录不存在 |
| F1004 | 成立 | 本轮独立复算：master.json 列 59 / 磁盘 74 / missing 15 名单与初审逐字一致 / extra 0 |
| F1005 | 成立 | plugins/master.json:3 `0.2.0` vs pyproject.toml:3 与 src/shenbi/__init__.py:12 `0.1.0` |
| F1006 | 成立 | codeql.yml:12-15 `on: push` 无 branches；ci.yml:3-4 有对照 |
| F1007 | 成立，**升级为 verified** | 初审"未验证"。本轮从安装的 pre-commit 源码取证：`pre_commit/commands/run.py::_run_single_hook` 返回 `files_modified or bool(retcode)`，`_run_all_hooks` 用 `retval |=` 聚合——autofix 改文件与 hook 真失败**同返 1**，workflow 的 "1 = autofix 预期" 注释与实现相反，真实失败会照样建 PR |
| F1008 | 成立 | .pre-commit-config.yaml:42 `rev: v1.33.0` vs uv.lock `yamllint 1.38.0`（本轮从锁文件正则提取） |
| F1009 | 成立 | grep `pytest.mark.order\|pytest_ordering` 全仓 RC=1；锁内 pytest-ordering 0.6 / pytest-randomly 4.1.0 并存 |
| F1010 | 成立 | tools/compare_mutation_score.py:5 docstring "Used by CI in PR-35"；workflows 无 mutmut 接线（grep 仅命中 ci.yml 纯度 lint 步骤名的 "mutation" 字样）；唯一消费 justfile:95 |
| F1011 | 成立 | 接线 grep RC=1；且本轮实跑 `tools/audit-skill-descriptions.py` 于真实 skills/ → "OK: all descriptions compliant" RC=0——工具可用、纯粹未接线（强化"应挂门"建议） |
| F1012 | 成立 | CI/just/pre-push grep RC=1，仅 .pre-commit-config.yaml:79-83；check_fixture_mirror.py:12 确无 sys.path.insert（其余 tools 均有） |
| F1013 | 成立，**升级为 verified 且影响上修** | 初审"未验证"。本轮 replica 实跑：PROJECT_DIR 含单引号 → 内嵌 python 语法错误；且 :70-79 无 try/except、无 `\|\| true` → **整脚本静默死**（比初审所述 "CURRENT_STEP 恒 unknown" 更重，:31-38 才是吞错续跑的位点）。静默死部分以 F1035 立案，F1013 主体维持 |
| F1014 | 成立 | run_pipeline.sh:89 `grep -q "escalation\|gate\|dispatch"` 原文并读；框架错误消息普遍含 gate/dispatch 字样，error≠blocked 亦被放行 |
| F1015 | 成立，**升级为 verified** | 初审"未验证"。本轮实跑：venv python 直接从无 src/shenbi 的目录运行 → RC=0 零输出（假绿）；另在 /tmp 伪项目放置违规文件 `{"status": "PASS"}` → 命中 RC=1，证明它扫的是 CWD 相对路径而非仓库 |
| F1016 | 成立 | lint_status_strings.py:51-74 Visitor 仅 visit_Dict/visit_Assign 并读 |
| F1017 | 成立 | generic.py:304-334 grep `g4_decisions` → 恰 7 技能，与 frozenset 7 元素逐一相符（本轮复算） |
| F1018 | 成立 | generate_autocheck_docs.py:123 `_PATTERN.sub(block, ...)` repl 未转义；当前常量无反斜杠（潜在未触发，定性不变） |
| F1019 | 成立 | `git ls-files novel-output/` → **1260 个已跟踪文件**；`git check-ignore novel-output` RC=1；.gitignore:91 vs :96-97 |
| F1020 | 成立 | `git check-ignore -v novel-xiaotiac-test-20260815 pipeline.log` → RC=1（均未忽略） |
| F1021 | 成立 | release.yml:23-38 裸 `git log --format='- %s (%h)'` vs cliff.toml commit_parsers 并读 |
| F1022 | 成立（行号微修） | 595 行脚本、"Run once" :8、CLASSIFICATION :22 起——初审写 ":22-518"，表实际延至约 :560；不影响结论 |
| F1023 | 成立（扩展为 F1033） | AGENTS.md 69 vs 74 复核属实；四文档漂移面见 F1033 |
| F1024 | 成立 | pyproject:359 mypy 3.12 vs :8 requires 3.11 vs :378 basedpyright 3.11 |
| F1025 | 成立 | justfile:92-95 守卫提示 "requires Plan 2"；`tests/baselines/mutation-score.txt` 存在（本轮文件存在性清单核实） |
| F1026 | 成立 | docs.yml 全文无 concurrency；ci.yml:7-9 有 |
| F1027 | 成立 | scan(roots) 形参在 :91 循环中未被引用（TARGET_GLOBS 常量直用） |
| F1028 | 成立 | CODEOWNERS 全文并读：默认 `*` 与 4 条分区条目同为 @ThomasChangX |
| F1029 | 成立 | AC-003.md:6 dotted 记法 `弧段/卷级.高光` vs 正文 `卷级高光/伏笔纪律` 斜杠合写并读 |

**事实修正类小项**（不构成误报）：
1. F1013 影响描述偏轻（见上，静默死以 F1035 补位）。
2. 初审运行门面对照矩阵中 "pre-push :70 有 loadscope+120 但无 --hypothesis-profile=ci" —— 复核属实，且注意 pre-push:70 另有 `--cov-fail-under=85` 而 justfile:23 无，方向与 CI 一致，维持 M 备注归类。
3. 初审 justfile 小节 "pipeline-init 拼接未加引号——M 级观察" 属**低判**：feedback/project_dir 含空格是常态输入且 argparse 必败，正式立案为 F1032（P2），见严重度异议表。

---

## 三、覆盖空洞（初审方法缺口）

1. **文档腿缺席**：Z10.files 未含 command-to-give.md、README.md、docs/skills/index.md（三者归 Z9），导致调用形状三方对账只剩两方——F1030/F1033/F1034 全部落在这个缝里。建议汇总 agent 将 Z9/Z10 的命令引用面做一次跨区并查。
2. **零实跑 just**：初审对 justfile 仅静态读，未用 `just --dry-run`（只读、零副作用）核对任何 recipe 的展开形态。F1031（注入）/F1032（断参）/F1030（--auto 报错）三条在 dry-run 一分钟内即可现形。
3. **零 bash 语义复现**：run_pipeline.sh / pre-push-check.sh 的 set -e × pipefail × 命令替换交互没有 replica 验证，4 条标"未验证"的 finding 中 2 条（F1013/F1015）本轮一次补验为真，另挖出 F1035/F1036 两条静默死。
4. **pre-commit 语义取证缺失**：F1007 基于公开语义"推断"，实际安装版源码（`_run_single_hook` 返回值）可直接取证，本轮已补。
5. **残余未覆盖点**（登记给第 2 轮，非 finding）：
   - run_pipeline.sh:14 `exec > >(tee -a ...)` 进程替换——脚本退出不等待 tee，日志尾部可能截断/交错（M 级候选，未立案）；
   - run_pipeline.sh blocked 分支 `uv run pipeline review ... | tail -1` 失败时虽有 set -e 兜底但同样无死前日志（与 F1035 同族，轻一档）;
   - ci.yml:29-30 macOS 全矩阵 continue-on-error → PR 的 macOS 质量门实际仅 advisory（注释自述为 uv sync 超时所迫，属文档化决策，未立案）;
   - executor_config 加载（dispatch_helper.py:135-145）文件缺失时静默 `{}` 无 WARN——因 executor_config.toml 为 repo 内跟踪文件且全框架路径皆假设 repo checkout（PROJECT=parents[3] 模式遍布 src/），单点立案意义有限，记 M 级观察。
6. **负结果记录**（防第 2 轮重复追）：`grep -q` 早退 + pipefail SIGPIPE 理论疑点（run_pipeline.sh:89 / pre-push:44）在 macOS bash 以 200KB 输入实测 5/5 均 MATCHED，**不成立，勿立案**。

---

## 四、严重度异议表

| 对象 | 初审判定 | 异议 | 理由 |
|---|---|---|---|
| F1031（新） | — | 定 P1 | prompt 是自然语言、含元字符是常态而非边界：空格即断参（正常路径功能错误），引号/`$` 即静默改写 dispatch 输入或执行意外命令；入口由 AGENTS.md 文档化 |
| F1030（新） | — | 定 P2（P1 候选说明） | 若按"正常路径功能错误"严格解读 README 快速开始可争 P1；因失败为即时报错、去 `--auto` 即绕过、无静默错误结果，定 P2。留汇总 agent 裁量 |
| justfile pipeline-init 未引号（初审 prose 观察，非正式 finding） | M 级观察 | 应升 P2 并正式立案（已作 F1032） | 实测 --dry-run 证明含空格 feedback/project_dir 必致 argparse RC=2；feedback 天然是句子，触发面非边界 |
| F1013 | P2 | 维持 P2，影响描述加重 | 实测补验成立且 :70-79 位点后果为静默死（已由 F1035 承接），不构成升降级依据 |
| F1003 | P1（初审已论证 P0 候选→P1） | 无异议 | 同意 P1：job 其余 diff 路径真实生效、发布产物不含 plugin.json |
| F1004 | P1 | 无异议 | 59/74 复算一致，缺 15 含整个 score-* 子系统 |
| 其余 23 条（F1001/F1002/F1005-F1012/F1014-F1029） | 各级 | 无异议 | 事实全部复核成立，严重度与 §8.1 决策表相称 |

---

## 五、收敛判定意见

- **判定：未收敛，但接近。** 依据：(1) 初审 29 条零误报、事实准确率极高——事实层已收敛；(2) 本轮 7 条新发现中 1 条 P1（F1031），且全部来自初审**方法结构上不做**的动作（实跑 just、bash 复现、读文档腿）——方法层未收敛。
- **第 2 轮建议范围**（无需再全量扫 53 文件）：
  1. 复读本轮 F1030–F1036 七条的事实与严重度（重点 F1031 的修复方案安全性：位置参数化后 `--dry-run` 回归）；
  2. 覆盖空洞 §三.5 登记的 4 个残余点（tee 竞态 / blocked 分支死前日志 / macOS advisory 门 / executor_config 静默 {}）择级立案；
  3. 与 Z9 做一次命令引用面跨区并查（command-to-give.md / README / docs/skills/index.md 的计数与命令引用，F1033/F1034 可能与 Z9 撞号需并号）。
- 若第 2 轮仅产出 M 级及以下且无新 P1/P2，即可宣布该区收敛。
