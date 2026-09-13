> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-13 · SDD #63 阶段 1 REWRITE：剔除 F1007/F1015/F1011 三条已被后续 PR 顺带修复成员，F004 改述结构债，T1504 按 C18 后实况重写) | **Severity:** 🟠 P1（F005/F1002/F1003/D101/F1040 本地绿 CI 红双向失真）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C25）| **代表 finding:** F005 | **簇规模:** 21 条（原 24 条，REWRITE 剔 3） | **严重度上限:** P1
> **范围:** .github/workflows/ci.yml、justfile、tools/pre-push-check.sh、pyproject.toml（addopts）、.gitignore、.pre-commit-config.yaml、release/docs/codeql workflows、AGENTS.md（等价命令表述） | **证据等级:** 实验佐证（Z10 三区 + Z10-review-r1/r2 实跑 + phase1 + 2026-09-13 SDD 驳斥复核亲证）
> **Ledger:** `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（**更正**：本簇成员在 08-15 ledger，非 08-14）
> **与既有 spec 关系:** AGENTS.md PR 协议 1（"Validate locally before pushing"）的保证面修复；PR Review Protocol 4 的 pre-push 覆盖率工件污染问题（D101/F770/F1040）在本 spec T2 收口。原「C17/C20/C21/C22 新 lint 承载前提」依赖已随 #55/#58/#59/#60 归档而消解，但它们新接入的 lint 已实际加剧双清单债（见 F004 改述）

# C25 · CI/just/工具链双向同步漂移修复（ci-just-sync）

## 背景（根因 + 证据 · 2026-09-13 复核后）

**根因**：ci.yml 与 justfile 各自维护检查清单、双向手工同步无单一信源。ci.yml:62 留有仓库自认的债务标注：`# NOTE: dual-list with justfile is C25 debt (spec #63) — systematic single-sourcing deferred`。"本地绿 ⇒ CI 绿"的契约（AGENTS.md PR 协议 1）双向都有洞。

证据分组（21 条，2026-09-13 main HEAD b00f564b 亲证存活）：
- **双向清单漂移（P1 核心）**：
  - **F004/F1001（改述为结构债）**：原「ci.yml 缺 lint_contract_graph + lint_contract_fields」的定向缺口已由 PR #202（C20）补齐，但双清单本体仍在蔓延——ci.yml lint job（L52-72）与 just check（justfile:14-39）各自维护清单，`diff <(grep -o 'lint_[a-z_]*\.py' justfile|sort -u) <(grep -o 'lint_[a-z_]*\.py' .github/workflows/ci.yml|sort -u)` 现非空（justfile 独有 7 个：artifact_contamination/bare_subprocess_json/bare_writes/decisions_sources/helper_usage/routing_faces/threshold_reconciliation；ci.yml 独有 2 个：no_forbid_with_computed_field/no_fs_mutation）。C17-C24 系列每新增一个 lint 就加深一次双向漂移
  - **F005/F1002（存活）**：just check 缺 CI codegen job（ci.yml:95-113）强制的 4 步——`uv lock --check`、`generate_autocheck_docs.py` 再生 diff、`shenbi-generate-plugins` + `.codex-plugin/` diff、（原「第二段 `-m "last"` pytest」半点已修，justfile:39 已含）。**补充存活**：AGENTS.md PR 协议 1 的「等价命令」（`ruff check . && ruff format --check . && mypy … && pytest … --cov-fail-under=85`）零 lint、零第二段、零 lock 检查——等价双向不成立
  - **F1003（存活，与 F911 同根合并裁决）**：`.gitignore:20` 忽略 `.codex-plugin/` → ci.yml:113 的 `git diff --exit-code -- … .codex-plugin/` 恒空转，插件新鲜度门形同虚设
- **coverage 工件污染链（存活）**：D101（pytest-cov 在 `--collect-only` 阶段仍写 coverage 工件并以 16.08% FAIL 污染正式覆盖率文件）、F770（M，同根：addopts 全局 `--cov`）、F1040（全局 addopts `--cov`+`fail_under=85`（pyproject.toml:437-445,467）使 `just test`（justfile:47，`-m "unit"`）/`just test-file`（L55）类运行全过也假失败）——三 fact 2026-09-13 亲证 pyproject/justfile 原样
- **工具/hook 激活缺口（存活）**：F1038（pre-push hook 配置齐全（.pre-commit-config.yaml:108-113 `stages: [pre-push]`）但文档安装命令（CONTRIBUTING.md:11、docs/getting-started/installation.md:43）只写 `uv run pre-commit install` 无 `--hook-type pre-push`，不激活；正确命令只在 tools/pre-push-check.sh:3 头注释）、F1012（收窄为纯接线：`check_fixture_mirror.py` 仅在 pre-commit（.pre-commit-config.yaml:81），just/CI 缺席；原「缺 sys.path 锚定」半点已失效，脚本已锚定仓库根）、F1036（pre-push-check.sh:74 计数管道 `grep|grep -v|wc -l` 在 `set -euo pipefail`（L4）下零命中即崩整钩——同文件 L63-65 cairo grep 已加 `|| true`，此管道漏加）
- **workflow 配置缺陷（存活）**：F1006（codeql.yml:12-13 `on: push:` 裸无 branches 过滤全量扫）、F1021（release.yml changelog 仍裸 `git log --format=…`，cliff 只在 justfile changelog recipe）、F1026（M，docs.yml 无 `concurrency:` 取消组，对照 ci.yml:8-10 有）、F1207（codeql.yml 无 pull_request 触发 vs SECURITY.md:27 "every PR" 声明漂移；push-only 有 300-file-limit 设计理由已文档化，修复向 = SECURITY.md 声明对齐或 PR 触发补全，T3 裁决）、F1042（M，pre-push-check.sh:44 `git diff --name-only main...HEAD 2>/dev/null | grep -qE`——ref 解析失败被吞、mkdocs 门静默跳过）、F911（与 F1003 同根：diff 恒空转使 plugin-manifest 强制描述失效）
- **gitignore/清洁面（存活）**：F1019（.gitignore:93 `novel-output/` 后接 :98-99 `!novel-output/`+`!novel-output/**` 死行——`git check-ignore -v` 亲证 93 行恒被 98 行覆盖）、F1020（无 `novel-*/`、`pipeline.log` 条目，而 run_pipeline.sh:6,13-14 在仓库根产生之）、T1504（**C18（PR #194）清洗后实况**：跟踪 1150 文件 / 12MB / staging 仅剩 8 个——原「22.7MB/1260/119 staging 对冲」论据已被 C18 消解大半；本 spec 只修规则对冲与决定剩余产物归宿，出库动作与 C18 协同）
- **杂项（存活）**：F957（test_docs_accuracy 白名单仅 9 份根级文档（tests/integration/test_docs_accuracy.py:15-25）、CODESPAN_PATTERN 只匹配无空格单 token——防线面与 C17/C23 分工对齐）、F1039（just clean（justfile:110）`rm -rf tests/coverage/` 删跟踪文件 `tests/coverage/.gitkeep`）

**REWRITE 剔除记录（2026-09-13，已被后续 PR 顺带修复）**：F1007（autoupdate rc 语义已修——workflow 现 `rc>1` 才 block）、F1015（lint_status_strings 已锚定 REPO_ROOT，docstring 自记 T905 修复）、F1011（audit-skill-descriptions 已接 just check，PR #204/C21；CI 面兜底缺位并入 F005/F004 的单源化收益，不再单列）。

## 目标

1. **单一信源**：ci.yml 与 justfile 的检查清单由同一来源驱动（CI 调 `just check` 为推荐向），双向漂移结构性消灭
2. coverage 工件隔离：非覆盖目的的 pytest 运行不再触碰正式 coverage 文件；`just test` 假失败修复
3. hook/工具激活面闭合：配置存在的检查全部真实运行（或删除配置）
4. 生产产物出库收尾：novel-output 剩余 1150 文件归宿裁决 + 忽略规则修复

## 任务分解

### T1 · 清单单源化（P1 核心）
1. 重构为 **CI 调 `just check`**（推荐：ci.yml lint/test job 收敛为安装 + `just check`，清单只在 justfile 一处）；或次选——单一被两边引用的 check 清单文件。裁决落文
2. F005：`uv lock --check`、autocheck docs 幂等 diff、plugin manifests 幂等 diff 进 just check（与 CI codegen job 对齐）；F1003/F911：`.codex-plugin/` 从 gitignore 放开（幂等 diff 需基线在库；先测体积）或改哈希对比——二选一裁决落文
3. AGENTS.md「等价命令」改述为「运行 `just check`」或修正为真实等价（含 lint 面 + `-m "last"` 第二段 + lock 检查）
4. 登记新 lint 接入规则（后续新检查只加 justfile 一处，CI 结构性继承）

### T2 · coverage 工件隔离
5. addopts 拆分：全局 addopts 移除 `--cov/--fail-under`，仅覆盖专用入口（just check 的 pytest 段、pre-push）显式携带；或常态 `COVERAGE_FILE` 隔离 + collect-only 豁免——最小侵入裁决落文（F770 随此消解）
6. F1040：`just test`/`test-file` 目标改用 `--no-cov`（AGENTS.md PR 协议 4 教训制度化）；F1036：pre-push 计数管道加 `|| true` 守卫

### T3 · 激活面与 workflow 修复
7. F1038：安装命令修正（文档 + `.pre-commit-config.yaml` 补 `default_install_hook_types: [pre-push, pre-commit]` 双保险）；F1012：check_fixture_mirror 接进 T1 统一入口
8. F1006（codeql 加 branches 过滤）、F1021（release notes 走 cliff）、F1207（与 F1006 同文件裁决：SECURITY.md 声明对齐或 pull_request 补全）
9. F957：test_docs_accuracy 盲区缩小（与 C17 T2 internal-links 防线分工对齐，避免重复建防线）
10. F1042：pre-push mkdocs 门 ref 解析失败显式报错；F1026：docs.yml 加 concurrency 取消组

### T4 · 忽略规则与出库
11. F1019/F1020：gitignore 死行清理 + run_pipeline.sh 产物条目；F1039：just clean 排除跟踪文件（`git clean` 或显式排除 .gitkeep）
12. T1504：novel-output 剩余 1150 文件/12MB（staging 8 个）归宿裁决——按 C18 后实况：脱敏小样入 fixtures（标 provenance）或全部出库（前向删除，不改写历史）

## 验收标准（真实数据可复验 · 2026-09-13 修订）

1. `diff <(grep -o 'lint_[a-z_]*\.py' justfile | sort -u) <(grep -o 'lint_[a-z_]*\.py' .github/workflows/ci.yml | sort -u)` 为空（CI 以 `just` 调用呈现后两侧同源）且反向：justfile 中存在而 CI 未跑的步骤数为 0（结构摘录进 PR）
2. 覆盖隔离复验：`uv run pytest --co -q` 两次运行后 `git status tests/coverage/` 干净（D101 红转绿）；`just test` 在全过测试上退出码 0（F1040 红灯验证）
3. pre-push：按文档命令安装后真实触发一次（hook 手跑记录）；零命中目录场景不再崩钩（F1036 负样本）
4. `git ls-files novel-output | wc -l` 与定稿策略一致（出库后 = 0 或仅显式白名单样本）；`git check-ignore` 对 run_pipeline.sh 产物模式命中（F1020）；`novel-output/` 死行移除后 `git check-ignore novel-output/staging/x` 行为符合定稿策略
5. codeql 只扫默认分支 push（workflow diff 对照）；release notes 由 cliff 生成（dry-run 输出）
6. `just check` 全绿且与 CI 同命令——干净 runner（CI）与本地各跑一次结果一致

## 风险与回滚

- **风险**：CI 收敛为 just 调用改变 CI 可观测性（步骤粒度变粗）——保留关键 lint 独立 step 或 just 内部 echo 分隔；CI 时长监控一轮
- **风险**：`.codex-plugin/` 入库（F1003 方案 A）增加仓库体积——先测量体积再裁决，方案 B（哈希对比）无此风险
- **风险**：addopts 拆分影响所有本地 pytest 习惯——justfile 目标全覆盖常见入口 + 文档一段迁移说明
- **风险**：novel-output 前向删除影响依赖它的 fixtures/测试引用——删除前 grep 引用面并改写为 tests/fixtures 路径
- **回滚**：T1–T4 各自独立 commit/PR 段；ci.yml/justfile 改动可整文件 revert；coverage 配置回滚无数据损失

## 簇成员清单（21 条，REWRITE 后自查用）

D101, F004-F005, F770, F911, F957, F1001-F1003, F1006, F1012, F1015✂(剔), F1019-F1021, F1207, F1026, F1036, F1038-F1040, F1042, T1504（代表 F005）
✂ 已剔除：F1007（autoupdate rc 已修）、F1015（CWD 已锚定）、F1011（已接 just check，CI 兜底并入 F004/F005）
