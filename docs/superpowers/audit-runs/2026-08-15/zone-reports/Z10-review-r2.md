# Z10 区第 2 轮复核报告（fresh context）

- 轮次: R2（按 r1 建议范围 + 两项强制新角度）
- 角度: (a) 产物路径与缓存一致性（coverage.xml / sbom / deps.json / 生成器 diff 范围 / HF 与 uv 缓存 key 对账）；(b) 失败可见性（错误被日志淹没、非零退出被吞、continue-on-error 滥用）；外加 r1 建议的命令引用面跨区并查（CI 完整性"配置齐全但范围错位"同类洞）
- 编号段: 新增 F1037–F1042（6 条）；复读 r1 的 F1030–F1036 全部 7 条（含实跑重验）；初审 29 条抽验 10 条（实跑）
- 只读声明: 除本报告外未创建/修改/删除任何仓库文件；验证脚本与输出全部位于 /tmp/z10r2/；未运行 pytest、未运行 shenbi-dispatch / pipeline 子命令（`pipeline review --help`、`shenbi-score --help` 等为 argparse/usage 帮助输出，不触发 cmd_* 逻辑；`shenbi-validate G0 --help` 意外执行了 G0 对伪 seed 的只读检查并返回 FAIL JSON，无写副作用）；未做 git 写操作；gh 仅只读查询（run list / jobs / logs / dependency-graph）。novel-output 只读。
- 审查日期: 2026-08-15

## 总体结论

r1 的 7 条**零误报**——全部实跑重验成立（F1031 的注入复现 `/tmp/z10r2/{injected,yz,s1}` 三个文件全部创建；F1035 两个 replica RC=1 零输出；F1036 零命中 RC=1、真实计数 13）。r1 登记的 4 个残余点中：**tee 竞态为负结果（5/5 不复现，不立案）**、review 管道死亡有可见错误尾行（并入 F1035 修复建议）、macOS continue-on-error 维持不立案（src 无 darwin 专属代码路径）、executor_config 静默 {} 维持 M 级观察。本轮在两个强制新角度 + 跨区并查下新发现 **6 条（P2×4、M×2，零新 P0/P1）**，其中 F1040（部分 pytest 运行强制 fail_under=85 → 测试全过也报 Coverage failure）从安装版 pytest-cov 7.1.0 源码 + 仓库现存 21.9% coverage.xml 双重取证。初审 29 条抽验 10 条实跑复核全部成立，零误报；一处事实扩展（F1002 的 "just check = 全部 CI 检查" 过度承诺同样出现在 installation.md:78 与 CONTRIBUTING.md:19）。

跨区并查的关键新证据：GitHub dependency graph **已完整解析 uv.lock**（193 包、含 docs 组）→ ci.yml 的 dependency-review job 非空转门，且在 PR-diff 层面部分补偿 T1303 的 docs 组审计缺口；但 deps.json 本身缺 5 技能（69/74，= 跨区已知 F1212，本轮佐证仍未修复），修正 r1 在 F1033 中 "deps.json 侧是新鲜的" 的表述。

---

## 一、漏报（新 finding，F1037–F1042）

### F1037 | 覆盖率质量门的自述阈值与实施值漂移：branch 78 vs 文档承诺 80；fail_under 85 vs 注释自述 89（"not 90"） | 漏报 | P2

- **证据**（文件 + git 历史实查）:
  - tests/unit/test_coverage_thresholds.py:23 `BRANCH_THRESHOLD_PCT = 78` vs :2 docstring "must meet the permanent >=80% floor" 与 :30 "PR-56 removed the xfail after Phase 3 raised branch coverage past 80%"
  - pyproject.toml:446-452 注释链自述 ">=90% line / >=80% branch… 89 (not 90) to accommodate Windows"，实际 `fail_under = 85`
  - git 历史：`dd1fc62`（#19，"fix: P0 blocking defects"）把 `BRANCH_THRESHOLD_PCT = 80` 改 78，**藏在与阈值无关的大杂烩提交里、提交信息零字提及**；`5b3e0ef`（"chore: lower coverage threshold from 89% to 85%"）有清晰提交信息但未同步更新 pyproject 注释
- **根因**: 两次降阈值（89→85、80→78）只改值不改自述文档；dd1fc62 一次连提交信息都未留痕。
- **验证**: 三处文件并读 + `git log -S`/`git show dd1fc62 -- tests/unit/test_coverage_thresholds.py`（diff 明确 `-BRANCH_THRESHOLD_PCT = 80` `+BRANCH_THRESHOLD_PCT = 78`）。
- **影响面**: CI 质量门在 85/78 执行而所有自述契约写 89–90/80；78–80 branch、85–89 line 区间的回归相对文档承诺静默放行；后续维护者按文档口径调阈值会被历史注释误导。
- **建议方向**: 值与自述二选一对齐；branch 门若有意 78（如 Windows 容差），在常量旁注明；fail_under 注释更新为 85 的真实理由（保留 5b3e0ef 提交信息链接）。

### F1038 | pre-push CI 模拟 hook 已在 .pre-commit-config.yaml 定义，但全部文档给出的安装命令不激活它 | 漏报 | P2

- **证据**（源码 + 文档并读）:
  - .pre-commit-config.yaml:103-108：`pre-push-ci-check`（entry `tools/pre-push-check.sh`，`stages: [pre-push]`）——最完整的本地门（含 pip-audit、mkdocs 链接检查、覆盖率阈值、幂等检查）的唯一接线
  - 安装版 pre-commit 源码 commands/install_uninstall.py:35-42：`pre-commit install` 无 `--hook-type` 且配置无 `default_install_hook_types` 时**只装 `pre-commit` 一种 hook**
  - docs/getting-started/installation.md:43 与 CONTRIBUTING.md:11 都只写 `uv run pre-commit install`；正确命令 `pre-commit install --hook-type pre-push` 只出现在 tools/pre-push-check.sh:3 的脚本头注释里，无任何用户可达文档面
- **根因**: pre-push stage hook 需要单独的安装 flag，文档化安装路径与 hook 接线面脱节——"hook 配置齐全、激活面缺位"，与 T1303 同族的范围错位形态。
- **验证**: 安装版源码并读 + 三处文档 grep（`--hook-type` 在 *.md 零命中，排除 audit-runs）。
- **影响面**: 照文档安装的贡献者其 pre-push 门**从未运行且无任何提示**；AGENTS.md PR 协议第 1/4 条的执行体（pre-push-check.sh）对这类用户静默失效。
- **建议方向**: `.pre-commit-config.yaml` 顶层加 `default_install_hook_types: [pre-commit, pre-push]`（配置侧根治，文档命令无需改）；或在两处安装文档补 `--hook-type pre-push`。

### F1039 | `just clean` 删除 git 跟踪文件 tests/coverage/.gitkeep，且 gitignore 负模式失效使恢复需 -f | 漏报 | P2

- **证据**（实跑）:
  - justfile:80 `rm -rf tests/coverage/ site/ .cache/`；`git ls-files tests/coverage/` → `tests/coverage/.gitkeep`（跟踪中）；`just --dry-run clean` 确认该 rm 原样执行
  - `git check-ignore -v --no-index tests/coverage/.gitkeep` → 命中 `.gitignore:52:tests/coverage/`——:74 的 `!tests/coverage/.gitkeep` 负模式因**父目录被排除而无效**（git 规则：无法 re-include 父目录已排除的文件）；该文件如今在仓库里只因历史上已被跟踪
- **根因**: clean recipe 的目标目录里放了跟踪锚点文件；gitignore 负模式写法自始无效。
- **验证**: 上列命令实跑（RC 与输出见上）。
- **影响面**: 任何 `just clean` 后工作树出现已删除跟踪文件；`git add -A` 习惯会把删除提交掉，此后恢复必须 `git add -f`（负模式救不回来）。初审 .gitignore 小节判 "`!tests/coverage/.gitkeep` 对已跟踪文件有效，非 bug"——对当时成立，但漏掉了 clean 的删除路径与负模式的失效。
- **建议方向**: clean 改 `rm -rf tests/coverage/*`（保 .gitkeep）或 `find tests/coverage -mindepth 1 -not -name .gitkeep -delete`；顺带修正 :74 无效负模式（删除或改 `!tests/coverage` 目录级配合）。

### F1040 | 全局 addopts --cov + config fail_under=85 使部分 pytest 运行（just test / just test-file）在测试全过时也报 Coverage failure 退出非零 | 漏报 | P2

- **证据**（安装版源码 + 仓库现存产物双重取证）:
  - pyproject.toml:420-431 addopts 全局注入 `--cov=shenbi`（无按运行规模关闭机制）；[tool.coverage.report] `fail_under = 85`
  - 安装版 pytest-cov 7.1.0 源码 plugin.py:270-271：`if self.options.cov_fail_under is None and hasattr(cov_config, 'fail_under'): self.options.cov_fail_under = cov_config.fail_under`——**CLI 未传 --cov-fail-under 时配置值自动生效**；:371-377：`should_fail_under(...)` 为真则 `session.testsfailed += 1`（测试失败退出码）
  - justfile:27-28 `test *args: uv run pytest -n auto -m "unit"` 与 :35-36 `test-file file: uv run pytest {{file}} -v` 均不带 `--no-cov`/`-p no:cov`
  - 仓库现存 tests/coverage/coverage.xml（今日 15:06 产物）：`line-rate="0.2192"`、HTML 报告仅 5 个测试模块（test_exceptions/test_logging/test_gates_integrity/test_pytest_framework/test_coverage_thresholds）——一次部分运行实测 21.92%，按上述机制该运行必然以 "Coverage failure: total of 21.92 is less than fail-under=85" 退出 1
- **根因**: fail_under 阈值只在全量口径下有意义，却通过 pytest-cov 的配置回退机制对**每一次** cov 启用运行生效；justfile 快捷 recipe 未隔离。
- **验证**: 机制链从安装版源码逐行核验；21.9% 产物实读。受审计铁则限制未实跑 pytest 复现退出码（`just test` 的 unit-only 全量口径是否 ≥85 无法确认，但 `test-file` 单文件口径几乎必然 <85）。
- **影响面**: `just test-file` 对绝大多数单文件必然假失败（误导排查方向）；若 unit-only 覆盖 <85，AGENTS.md 文档化的标准命令 `just test`（"Fast unit tests only"）每次调用都会以 Coverage failure 收尾。失败是响亮的（非静默错误），workaround 是手动加 --no-cov。
- **建议方向**: `test`/`test-file` recipe 加 `-p no:cov` 或 `--no-cov`（与 :24 的 last 段先例一致）；或在 addopts 移除全局 --cov、只在 check/test-all/pre-push/CI 显式开启。
- **严重度备注**: 按 r1 对 F1030 的同型裁量（响亮失败 + 即时绕过 → P2）；若后续证实 `just test` unit-only <85（标准命令全量失效），可升 P1 候选。

### F1041 | release/security 的 SBOM 描述 dev 组环境而非发布物运行时依赖（过度包含的范围错位） | 漏报 | M

- **证据**: security.yml:13-15 与 release.yml:16-18 均 `uv sync --frozen --group dev` 后 `cyclonedx-py environment -o sbom.cdx.json`——SBOM 内容 = 项目依赖 + dev 组（含 pytest/mypy/torch/nvidia CUDA 系），而 release 产物 wheel 只含 src/shenbi + 8 个运行时依赖（pyproject [project].dependencies）
- **根因**: cyclonedx environment 命令扫描当前环境；无按产物口径（`cyclonedx-py pyproject` 或 wheel SBOM）生成。
- **验证**: 两 workflow 并读 + pyproject 依赖组对照。
- **影响面**: 发布 SBOM 把 ~170 个非运行时包标为发布组成 → 漏洞扫描器对 dev-only 漏洞误报（噪音方向，非漏报方向）；T1303（docs 组审计缺口）的镜像孪生——一个是欠审计，一个是过度报告。
- **建议方向**: release.yml 改 `cyclonedx-py pyproject`（或对 dist/*.whl 生成），security.yml 可保留 environment 口径但命名/注释注明口径。

### F1042 | pre-push-check.sh:44 mkdocs 条件门的 ref 解析失败被 2>/dev/null 静默吞掉 → docs 链接门静默跳过 | 漏报 | M

- **证据**: tools/pre-push-check.sh:44 `if git diff --name-only main...HEAD 2>/dev/null | grep -qE '^(docs/|mkdocs\.yml)'; then`——无本地 main 引用（仅分支克隆/worktree/浅克隆）时 git diff 报错进 /dev/null、输出为空、grep 无匹配 → 条件假 → mkdocs 链接检查**静默不运行**，脚本继续（后续步骤全绿）
- **根因**: `2>/dev/null` 防的是 grep 噪音，但同时掩盖了 range 本身解析失败这一不同故障类；注释（:42-43）只论证了 main...HEAD 是正确 idiom，未处理 main 缺失分支。
- **验证**: 静态（shell 语义确定）；未在无 main 克隆中实跑复现（构建克隆成本高于收益）。
- **影响面**: 罕见 ref 拓扑下条件门自禁用且零提示；属本地 hook 的 docs-only 门，影响面小。
- **建议方向**: 先 `git rev-parse --verify main >/dev/null 2>&1 || { echo "WARN: no main ref, skipping mkdocs check"; }` 显式降级留痕。

---

## 二、误报 / 事实修正

### r1 的 7 条（F1030–F1036）逐条重验

| 编号 | 重验结果 | 本轮独立证据 |
|---|---|---|
| F1030 | **成立（实跑重现）** | `just --dry-run pipeline-init outline-example.md ./my-novel --auto` → `error: justfile does not contain recipe '--auto'` RC=1；README.md:46 原文确认 |
| F1031 | **成立（实跑重现）** | /tmp/z10r2 同构 replica（just 1.52.0）：`;`/`$( )` 两注入文件 + 单参数注入文件共 3 个全部创建；真实 recipe `--dry-run` 展开确认 prompt 拆散为多 argv |
| F1032 | **成立（实跑重现）** | `just --dry-run pipeline-review ./my-novel approve "some feedback here"` → `--feedback some feedback here`（6 词）；argparse 定义（2 positional + --feedback 单值）并读 |
| F1033 | **成立，一处事实修正** | 四处计数（59/67/69/69）与磁盘 74 全部复核。**修正**：r1 称 "deps.json 侧是新鲜的"——实际 deps.json 仅枚举 69/74 技能（缺 shenbi-foreshadowing-lifecycle 与 review-group-{character,craft,factual,plan} 共 5 个，= 跨区已知 F1212）；docs/skills/index.md 的 69 与其声明来源 deps.json 一致，真正的纯漂移是 command-to-give.md:85 的 59 与 README.md:16/22 的 67（README :88 的 69 反而与 deps.json 一致、与自身 :16 矛盾） |
| F1034 | **成立（实跑重现）** | `ls tests/dispatch-subagent.sh` → 不存在；command-to-give.md:48 活引用；其余命中全为 archive/ADR/spec 历史文档 |
| F1035 | **成立（双 replica 实跑重现）** | :26 无守卫命令替换在无 status 输出时 RC=1 且零输出；:70-79 python 块在 PROJECT_DIR 含单引号时 RC=1、最后日志停在 "STUCK… Advancing past it."、stderr 被 2>/dev/null 吞 |
| F1036 | **成立（实跑重现）** | 零命中目录 → RC=1 零输出整脚本终止；真实 src/shenbi 计数 = 13（WARNING 分支，当前绿） |

**结论：r1 的 7 条零误报。**

### 初审 29 条抽验（10 条实跑）

F1001（graph/fields 在 .github//pre-commit 零接线 grep RC=1）、F1003（`git ls-files .codex-plugin/` 0 个、check-ignore 命中 :20）、F1004（master 59 / 磁盘 74 / missing 15 名单逐字一致 / extra 0）、F1005（0.2.0 vs 0.1.0）、F1006（codeql push 无 branches 过滤）、F1008（锁内 yamllint 1.38.0 vs hook v1.33.0）、F1009（锁内 pytest-ordering 0.6 + pytest-randomly 4.1.0 并存）、F1011（audit-skill-descriptions 零接线）、F1012（check_fixture_mirror 仅 pre-commit）、F1019（`git ls-files novel-output/` 1260 个跟踪文件）——**全部成立，零误报**。其余 19 条在本轮会话的文件并读中一致性核验，未发现矛盾。

**事实扩展（不构成误报）**：
1. F1002 的 "just check = 全部 CI 检查" 过度承诺不止 AGENTS.md——installation.md:78（"运行所有 CI 检查 / Run all CI checks"）与 CONTRIBUTING.md:19 同句式；修复时三处一起改。
2. F1033 的 deps.json 新鲜度表述修正（见上表）。
3. 初审 .gitignore 小节对 `!tests/coverage/.gitkeep` 的"非 bug"判定需补充 clean 删除路径与负模式失效两面（已立案 F1039）。

---

## 三、覆盖空洞

1. **CI 运行态证据（gh 只读查询）本轮首次引入**：job 级结论（macOS/3.13 job 全 success，PR 上 dependency-review success 且 Dependency Changes 组为空=该 PR 无依赖变更）、依赖图 SBOM API（193 包，含 mkdocs/mkdocs-material → **uv.lock 被完整解析，dependency-review 非空转门**，并在 PR-diff 层部分补偿 T1303）、cancelled run 归因（concurrency 取消，正常）。前两轮均未做过——建议后续轮次保留此面。
2. **pytest 运行态不可测**：审计铁则禁 pytest，F1040 的 `just test` unit-only 口径是否 <85 无法实证（机制链与单文件口径已足立案）；留给修复者本地一键验证。
3. **actions 运行时版本货币性**：日志可见 `actions/checkout@v4`、`dependency-review-action@v4` 被强制跑在 Node 24（Node 20 弃用警告）——功能无碍，M 级货币性观察，未立案。
4. **docs/ 深层页面命令引用**：getting-started 三页（installation/concepts/first-novel）本轮已查（first-novel 的 `uv run shenbi-dispatch …` 形状正确）；更深层 docs/ 页面归 Z9，未在本区展开。
5. **mkdocs gh-deploy / release 上传运行态**：无 push 无法验证，静态形状（site/、dist/*.whl、dist/*.tar.gz、sbom.cdx.json 与生成器输出路径）已对账一致。

### 残余点核查结论（r1 §三.5 逐项）

| 残余点 | 本轮判定 |
|---|---|
| run_pipeline.sh:14 `exec > >(tee -a …)` 截断/交错 | **负结果**：5/5 次迭代日志行数完整（/tmp/z10r2/race.log 累计 10/10 行），macOS bash 不复现，不立案（与 r1 的 SIGPIPE 负结果同登记防重追） |
| blocked 分支 `review … \| tail -1` 死前无日志 | **轻于预期**：replica 显示失败 review 的错误 JSON 最后一行会随 tail -1 打印（有死亡证据，非零输出）——并入 F1035 修复建议（死前补显式 FATAL 框架），不单独立案 |
| ci.yml:29-30 macOS/3.13 continue-on-error | **维持不立案**：src/shenbi 无 darwin 专属路径（仅 safe_write.py:54、filelock_utils.py:92/136 的 win32 守卫，Windows 有独立 nightly smoke）；行内注释文档化（uv sync 超时/3.13 rollout）；GitHub UI 对 continue-on-error job 有标注，非完全不可见；ubuntu 门承担 Python 面执法 |
| executor_config 静默 `{}` | **维持 M 观察**：dispatch_helper.py:135-145 确认缺失时无 WARN 直落 `{}` → 温度 0.7/max_tokens 16384 默认（:212-234）；文件在仓库内被跟踪、全框架假设 repo checkout（:65 parents[3] 模式），pip 安装态才可达，单点立案意义有限 |

### 跨区并查登记（供汇总 agent）

- **deps.json 缺 5 技能**（69/74：shenbi-foreshadowing-lifecycle、review-group-*×4）——佐证跨区 F1212 未修复；F1033 的事实修正依赖此点。
- command-to-give.md:48 死引用 = F461/F0-05/F125（台账已注"阶段 4 合并"）。
- F1001/F1013/F1014 与 2026-08-14 specs 中的 F1200/F1201/F1204-F1206 为同域跨号，已由台账关联，无新增冲突。
- T1303（security.yml 漏 docs 组）补充：dependency-review job 因依赖图解析全量 uv.lock，在 **PR 依赖变更 diff** 层覆盖 docs 组（许可/漏洞）；缺口收缩为"非 PR 触发的周期性全量审计仍只扫 dev 组"。

---

## 四、严重度异议表

| 对象 | 原判定 | 异议 | 理由 |
|---|---|---|---|
| F1040（新） | — | 定 P2（P1 候选注明） | 与 r1 裁 F1030 同型（响亮失败 + 即时 --no-cov 绕过）；但若证实 unit-only <85 则 AGENTS.md 标准命令全量失效，升 P1 候选留汇总裁量 |
| F1038（新） | — | 定 P2 | 门本身逻辑正确、非 false green；是"激活面缺位"导致静默不运行，介于 P1"配置错位"与 P2"文档漂移"之间，按影响（有 AGENTS.md 手动协议兜底）取 P2 |
| F1039（新） | — | 定 P2 | 正常路径必然产生脏树 + 意外提交后需 -f 恢复；响亮可见（git status）故非 P1 |
| F1035 | P2 | 无异议（维持） | 实测复核成立；死亡是日志静默但退出码响亮，不到 P1 "静默错误结果" |
| F1004 | P1 | 无异议（维持） | 59/74 独立复算一致，missing 15 名单逐字相符 |
| F1002 | P1 | 无异议 + 描述扩展 | 三文档同句式过度承诺（AGENTS.md/installation.md/CONTRIBUTING.md），修复面扩大但严重度不变 |
| F1033 | P2 | 无异议 + 事实修正 | 漂移成立；"deps.json 新鲜"表述按 F1212 修正为"deps.json 亦缺 5" |
| 其余（F1001/F1003/F1005-F1036 未逐条重列者） | 各级 | 无异议 | 本轮抽验与并读全部成立 |

---

## 五、收敛判定

- **判定：未收敛（按计数标准），但收敛在望。**
- 依据：
  1. r1 的 7 条零误报、初审 29 条抽验零误报——**事实层连续两轮零误报，已收敛**；
  2. 本轮新 6 条（P2×4、M×2），**零新 P0/P1**——严重度层未恶化；
  3. 但 6 > 3，未达"≤3 条且零新 P0/P1"的软序列第 1 轮字面标准；
  4. 全部 6 条来自本轮**首次启用**的方法面（gh 运行态取证、安装版插件源码取证、产物-消费者对账、clean/gitignore 交互），初审与 r1 的方法结构上均不覆盖——属新角度首轮产出而非同方法二次扫描的持续渗出；
  5. 4 个残余点全部关闭（1 负结果、1 并入 F1035、2 维持不立案），r1 的开放面已清零。
- 预期：第 3 轮若无新角度，产出应降至 ≤3 且以 M 为主。建议第 3 轮（如举行）只做两件事：F1040 的 unit-only 口径实证（修复者侧一键验证）与本报告 6 条的修复方案安全性核验，不再全量扫面。
