> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1（F004/F005/F1001/F1002/F1003 本地绿 CI 红双向失真）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C25）| **代表 finding:** F004 | **簇规模:** 24 条 | **严重度上限:** P1
> **范围:** .github/workflows/ci.yml、justfile、tools/pre-push-check.sh、pyproject.toml（addopts）、.gitignore、.pre-commit、release/docs/codeql workflows | **证据等级:** 实验佐证（Z10 三区 + Z10-review-r1/r2 实跑 diff 命令 + phase1）
> **与既有 spec 关系:** AGENTS.md PR 协议 1（"Validate locally before pushing"）的保证面修复；PR Review Protocol 4 提到的 pre-push hook 覆盖率工件污染问题（D101/F770/F1040）在本 spec T4 收口
> **phase4 严重度校准提案:** F004/F005 各有 →P1 提案（与 F1001/F1002 跨区重复立案同内容）

# C25 · CI/just/工具链双向同步漂移修复（ci-just-sync）

## 背景（根因 + 证据）

**根因**：ci.yml 与 justfile 各自维护检查清单、双向手工同步无单一信源——CI 窄于本地（F004：ci.yml:63-66 仅 lint_contracts + lint_repo_consistency，缺 lint_contract_graph.py 与 scripts/lint_contract_fields.py，`diff <(grep -o 'lint_[a-z_]*\.py' justfile …)` 实跑证实）或本地窄于 CI（F005：just check 幂等 diff 范围缺 .codex-plugin/、autocheck docs、plugin manifests，对照 ci.yml:86-99 codegen job）。"本地绿 ⇒ CI 绿"的契约（AGENTS.md PR 协议 1）双向都有洞。外围还有：hook 配置齐全不激活、coverage 工件被非覆盖运行污染、gitignore 反忽略 22.7MB 生产物。

证据分组（24 条）：
- **双向清单漂移（P1 核心）**：F004/F1001（CI 缺 2 个阻断 lint，grep 零接线实跑 verified）、F005/F1002（just check 缺 CI 强制的 4 步：lock/两 lint/autocheck 幂等；**补充**：AGENTS.md 给的"等价命令"还缺 `-m "last"` 第二段 pytest，等价双向不成立）、F1003（ci.yml + .gitignore：`.codex-plugin/` 幂等 diff 恒空——目录被 gitignore，插件新鲜度门形同虚设）
- **coverage 工件污染链**：D101（pytest-cov 在 --collect-only 阶段仍写 coverage 工件并以 16.08% FAIL 污染正式覆盖率文件，两次复现）、F770（M，同根：addopts 全局 --cov）、F1040（全局 addopts --cov + fail_under=85 使 just test/test-file 类运行测试全过也假失败退出非零——21.92% 现存产物实证，协调者抽验；与 AGENTS.md PR 协议 4 记述的 pre-push 覆盖率覆写事件同族）
- **工具/hook 激活缺口**：F1038（pre-push hook 配置齐全但文档安装命令不激活）、F1011（audit-skill-descriptions.py 未接任何门）、F1012（check_fixture_mirror.py 仅 pre-commit，CI/just 缺席 + 缺 sys.path 锚定）、F1015（lint_status_strings.py CWD 敏感，异目录静默假绿——实跑 verified）、F1036（pre-push-check.sh:74 计数管道零命中即崩整钩——实跑重现）
- **workflow 配置缺陷**：F1006（codeql push 无分支过滤全量扫）、F1007（pre-commit-autoupdate rc==1 语义误判——autofix 与真失败同返 1，从安装源码取证 verified）、F1021（release.yml 裸 git log 绕过 cliff 分组）、F1026（M，docs.yml 无 concurrency 取消组）、F1042（M，mkdocs 条件门失败静默跳过）、F911（plugin-manifest CI 强制描述失效）
- **gitignore/清洁面**：F1019（novel-output 先忽略后取反死行误导）、F1020（缺 run_pipeline.sh 产物条目）、T1504（novel-output 22.7MB/1260 文件反忽略入库 main：52 个 ~320KB 快照 + 119 staging，staging 与顶层忽略规则对冲——协调者抽证 25M/119）
- **杂项**：F957（test_docs_accuracy 盲区：F901/F951 类断链无感穿过——防线面与 C17/C23 协同）、F1039（just clean 删跟踪文件 .gitkeep）

## 目标

1. **单一信源**：ci.yml 与 justfile 的检查清单由同一来源驱动（just check 为权威、CI 调 just，或生成式清单），双向漂移结构性消灭
2. coverage 工件隔离：非覆盖目的的 pytest 运行不再触碰正式 coverage 文件；just test 假失败修复
3. hook/工具激活面闭合：配置存在的检查全部真实运行（或删除配置）
4. 生产产物出库：novel-output 22.7MB 反忽略入库清理 + 忽略规则修复

## 任务分解

### T1 · 清单单源化（P1 核心）
1. 重构为 **CI 调 `just check`**（推荐：ci.yml 各 job 收敛为安装 + `just <target>`，清单只在 justfile 一处）；或次选——单一 `justfile` include 的 check 清单文件被两边引用
2. F004：lint_contract_graph + lint_contract_fields 进统一入口；F005：.codex-plugin/、autocheck docs、plugin manifests 幂等 diff 进 just check；F1003：`.codex-plugin/` 从 gitignore 放开（幂等 diff 需要基线在库）或改哈希对比方案——二选一裁决落文
3. AGENTS.md "等价命令"修正为真实等价（含 `-m "last"` 第二段 + lint 面），或直接改述为"运行 just check"
4. 同步登记后续新 lint 的接入规则（C17/C20/C21/C22 的新检查全部走同一入口——本 spec 是它们的承载前提）

### T2 · coverage 工件隔离
5. addopts 拆分：全局 addopts 移除 `--cov/--fail-under`，仅覆盖专用入口（just check 的 pytest 段、CI coverage job）显式携带；或常态 `COVERAGE_FILE` 隔离 + collect-only 豁免——以最小侵入裁决
6. F1040：just test/test-file 目标改用 `--no-cov`（AGENTS.md PR 协议 4 的教训制度化）；F1036：pre-push 计数管道加零命中守卫

### T3 · 激活面与 workflow 修复
7. F1038：pre-push 安装命令修正为真实激活路径；F1011/F1012：两个检查工具接进 T1 统一入口（F1012 兼修 sys.path 锚定）；F1015：lint_status_strings 显式锚定仓库根（拒绝异目录假绿）
8. F1006（codeql 加 branches 过滤）、F1007（rc==1 判定改为区分 autofix/失败：比对 hook 前后 git diff 或用 pre-commit timeout/retry 语义）、F1021（release notes 走 cliff）、F911（plugin-manifest 强制描述恢复生效）
9. F957：test_docs_accuracy 盲区缩小（与 C17 T2 的 internal-links 防线分工对齐，避免重复建防线）

### T4 · 忽略规则与出库
10. F1019/F1020：gitignore 死行清理 + run_pipeline.sh 产物条目补齐；F1039：just clean 排除跟踪文件
11. T1504：novel-output 反忽略入库处理——按 phase4 C18 分工：生产树清洗（C18）完成后再决定保留样本（脱敏小样入 fixtures，标 provenance）或全部出库；本 spec 只修规则对冲（staging 与顶层忽略规则一致化），出库动作与 C18 协同排期

### 批量清理（M 级成员）
- **F770**（M）：随 T2 addopts 拆分消解
- **F1026**（M）：docs.yml 加 concurrency 取消组
- **F1042**（M）：mkdocs 条件门失败显式报错而非跳过

## 验收标准（真实数据可复验）

1. `diff <(grep -o 'lint_[a-z_]*\.py' justfile | sort -u) <(grep -o 'lint_[a-z_]*\.py' .github/workflows/ci.yml | sort -u)` 为空且 ci.yml 的检查步骤以 `just` 调用呈现（结构对照截图/摘录进 PR）；反向：justfile 中存在而 CI 未跑的步骤数为 0
2. 覆盖隔离复验：`uv run pytest --co -q` 两次运行后 `git status tests/coverage/` 干净（D101 红转绿）；`just test` 在全过的测试上退出码 0（F1040 红灯验证）
3. pre-push：按文档命令安装后真实触发一次（push dry-run 或 hook 手跑记录）；零命中目录场景不再崩钩（F1036 负样本）
4. `git ls-files novel-output | wc -l` 与定稿策略一致（出库后 = 0 或仅显式白名单样本）；`git check-ignore` 对 run_pipeline.sh 产物模式命中（F1020）
5. codeql 只扫默认分支 push（workflow diff 对照）；release notes 由 cliff 生成（dry-run 输出）
6. `just check` 全绿且与 CI 同命令——在一个干净 runner（CI）与本地各跑一次结果一致

## 风险与回滚

- **风险**：CI 收敛为 just 调用改变 CI 可观测性（步骤粒度变粗）——保留关键 lint 的独立 step 或加 just 内部 echo 分隔；CI 时长监控一轮
- **风险**：`.codex-plugin/` 入库（F1003 方案 A）增加仓库体积——先测量体积再裁决，方案 B（哈希对比）无此风险
- **风险**：addopts 拆分影响所有本地 pytest 习惯——justfile 目标全覆盖常见入口 + README 一段迁移说明
- **风险**：novel-output 出库动 main 历史（若走 filter-repo）——默认仅前向删除（新 commit 删文件）+ 忽略修复，不改写历史；历史瘦身另立项
- **回滚**：T1–T4 各自独立 PR；ci.yml/justfile 改动均可整文件 revert；coverage 配置回滚无数据损失

## 簇成员清单（24 条，自查用）

D101, F004-F005, F770, F911, F957, F1001-F1003, F1006-F1007, F1011-F1012, F1015, F1019-F1021, F1026, F1036, F1038-F1040, F1042, T1504（代表 F004）
