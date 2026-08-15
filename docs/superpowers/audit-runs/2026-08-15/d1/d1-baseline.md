# D1 确定性机械层基线 — 2026-08-15

执行环境：`uv run`（与 CI 同构）。全部命令真实运行，原始输出见本目录各 `d1-*.log`。

## ① just check 全套
- EXIT=0 全绿：ruff/format/mypy/basedpyright/契约 lints/状态字面量/两段 pytest（2887 passed + 373 skipped；last 段 4 passed）
- 覆盖率 85.34% ≥ 85% 门。COVERAGE_FILE 已隔离至 `d1/.coverage`（原则 7）
- 输出：`d1-01-just-check.log`

## ② tools/ 检查类脚本逐个（9 个）
- lint_status_strings / lint_repo_consistency / scripts:lint_contract_fields / lint_contracts / audit-skill-descriptions / check_fixture_mirror / lint_no_forbid_with_computed_field / lint_no_fs_mutation / **lint_contract_graph**（首跑遗漏后补跑）— 全部 exit=0
- lint_contract_graph 输出既有 DANGLING_WRITE warnings（如 shenbi-score-stratum writes=audits/stratum-*-score.md no consumer）——语义确认归 T2 线程
- 输出：`d1-02-tools-scripts.log`

## ③ SKILL.md frontmatter 全量解析（74 skill）
- yaml 解析 74/74；name==目录名 74/74；description ≤500 全过
- **2 个 meta skill 无 `contract.kind`**（using-shenbi、shenbi-writing-skills）→ finding D104（Z8 语义裁决：设计豁免 or 契约缺失）
- 输出：`d1-03-frontmatter.log`（脚本 `/tmp/d1_03_frontmatter.py`，kind 取 `contract.kind` 路径）

## ④ shenbi-validate G2/G4 冒烟
- G2 真实 fixture（tests/fixtures/chapter-2-draft.md，markdown）：PASS（G2.1/2/3/5/10/12 全过）
- G4 CLI（worldbuilding + fixture）：ValueError("round_dir or project_dir required") — 符合设计契约（与 2026-08-14 轮记录一致）
- 输出：`d1-04-07-cli-smoke.log`

## ⑤ 禁用模式 git grep（src/）
- bare except：**0**；pickle：**0**；硬编码绝对路径（/Users|/home）：**0**
- `print(`：6 处真命中（2 处 `_text_fingerprint(` 子串误报已剔除）→ finding D102
- TODO/FIXME/HACK：1 处（chapter_loop.py:20 docstring）→ finding D103
- 输出：`d1-05-forbidden-patterns.log`

## ⑥ pytest --cov 覆盖率缺口报告
- 每文件未覆盖行清单：`d1-06-coverage-gaps.log`（200 文件条目，源自 ① 的隔离 COVERAGE_FILE）
- 逐行处置归各 per-file 报告（§5 通用维度 8）；低覆盖显著项：audit/snapshot.py（38 未覆盖）、config/config_coherence.py（20）、contracts/fields.py（26）等

## ⑦ CLI 入口冒烟
- shenbi-validate G0 20260814 → FAIL(seed not found)（预期：G0 需已登记 seed，与上轮一致）
- shenbi-score --help / shenbi-dispatch --help / shenbi-phase（缺 --round-dir 报错）— 全部可用
- 输出：`d1-04-07-cli-smoke.log`

## ⑧ 凭证扫描
- `git log -p --all` 全历史（sk-/ghp_/github_pat_/AKIA/PRIVATE KEY/xox-）：**0 命中**
- 工作树 grep（同模式 + password=）：**0 命中**
- 输出：`d1-08-credscan-history.log`、`d1-08-credscan-worktree.log`

## ⑨ 依赖漏洞审计
- `uv audit` 不受当前 uv 版本支持 → 等价 `uvx pip-audit`：**No known vulnerabilities found**
- 输出：`d1-09-pip-audit.log`
- **勘误（2026-08-16，T13 线程）**: uvx pip-audit 审计的是临时环境 29 包而非项目依赖——本条结论无效（false assurance，T1301）。权威结果以 thread-reports/T13.md 四口径重审为准：prod+dev 131/实装 132 = 0 漏洞；docs 组 157 含 1 项 CVE（T1302，配置不可达）

## ⑩ 依赖健康初判
- deptry 不可用（未安装）→ 等价 `uv tree`（180 包解析）+ pyproject 声明对照，深查归 T13
- 输出：`d1-10-uv-tree.log`

## ⑪ skip/xfail 清点
- 运行时：2887 passed + **373 skipped**（just check 第一段）+ 4 deselected（last 段前）
- 来源分解（实测）：**371 = tests/integration/test_doc_links.py 全文件**（markdown-link-check 未装；`.github/workflows/nightly.yml:68` 安装该工具 → 本地跳过/nightly 启用设计，keep 候选，nightly 实际绿否归 Z10/T10）；2 = sentence_transformers 已装降级路径不可测（unit/pipeline）；其余零星
- 静态 skip/xfail 标记仅 2 处（test_safe_write.py、test_phase_runner_property.py）
- DOCS_TO_CHECK 声明 8 条全部在盘（声明面↔磁盘面零断链）
- 输出：`d1-11-skip-reasons.log`、`d1-11-skipxfail-static.log`、`d1-11-docs-to-check-stats.txt`、`d1-11-collect-only.log`

## ⑫ 锁定与环境一致性
- `uv lock --check`：exit=0（锁一致）
- 输出：`d1-12-lock-check.log`

## Pre-existing 失败
- **无**（just check 全绿；G0 seed-not-found 与 G4 契约错误均为设计内行为）

## D1 段 findings（已录 findings-ledger.md）
- D101（P2）：pytest-cov 在 `--collect-only` 阶段仍写 coverage 工件并以 16.08% FAIL（tests/coverage/coverage.xml 被非覆盖目的调用覆写——上轮 2 次污染先例的机制面）
- D102（P1）：src/shenbi 内 6 处 `print(`（AGENTS.md 显式禁令；CLI 入口豁免边界待 Z3/Z5/Z6 深读裁决）
- D103（M）：chapter_loop.py:20 docstring 遗留 TODO 措辞
- D104（P2）：using-shenbi、shenbi-writing-skills 无 contract.kind（Z8 裁决设计豁免 or 契约缺失）
