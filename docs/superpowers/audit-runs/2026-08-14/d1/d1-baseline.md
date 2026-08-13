# D1 确定性机械层基线 — 2026-08-14

> 全部命令在 2026-08-14 会话 1 实际运行。本文件为归档索引；详细输出见各 d1-*.log/txt。

## ① just check 全套
- 命令: `just check`（lint_status_strings / lint_repo_consistency / lint-contracts(3) / ruff check / ruff format / mypy / basedpyright / sync-contracts 幂等 / pytest 2814+4）
- 结果: **PASS** — `2814 passed, 216 skipped in 41.81s`；覆盖率 **85.14%** ≥ 85 阈值；EXIT=0
- 输出: `d1-01-just-check.log`

## ② tools/ 检查类脚本（逐个运行）
- 9/9 脚本 EXIT=0: lint_status_strings.py / lint_repo_consistency.py / lint_contract_graph.py / scripts/lint_contract_fields.py / tools/lint_contracts.py / audit-skill-descriptions.py / check_fixture_mirror.py / lint_no_forbid_with_computed_field.py / lint_no_fs_mutation.py
- 迁移类工具（migrate_contract_to_frontmatter.py）按规则排除
- 输出: `d1-02-tools-scripts.log`

## ③ SKILL.md frontmatter 全量解析
- 74/74 skills yaml 解析通过；name == 目录名；description ≤500 字符；0 异常
- 注：初跑用 `yaml.safe_load(全文)` 报错——SKILL.md 正文含 `---` 分隔线，需仅解析 frontmatter 块（修正后 0 BAD）

## ④ shenbi-validate G2/G4
- G2: PASS（真实 fixture 冒烟 `tests/fixtures/chapter-2-draft.md`；Z8.files 清单冒烟 PASS，G2.12 WARN may-be-truncated）
- G4: 20 个 per-skill checker 全部由 `tests/unit/gates/g4/test_all_skills_parametrized.py` 参数化冒烟覆盖；全部 gate 测试 `tests/gates/ tests/unit/gates/` = **801 passed**
- CLI G4 冒烟: `shenbi-validate G4 worldbuilding <md>` → ValueError("round_dir or project_dir required") — **符合设计契约**（test_g4_signatures 断言无 root raise）

## ⑤ 禁用模式 grep
- bare except / pickle / TODO-FIXME-HACK / 硬编码绝对路径: **0 命中**（src/）
- `print(`: 7 处命中 — pipeline/cli.py:877,879、cost/report.py:93,95、skill_utils/foreshadowing_recall/recall.py:61、skill_utils/escalation/check.py:149（CLI/工具入口上下文，Z1/Z5/Z6 深读确认是否违反 AGENTS.md "No print() in framework code"）

## ⑥ 覆盖率缺口报告
- `tests/coverage/coverage.xml`（85.14% 运行生成）解析: **7050 未覆盖行**，top: chapter_loop.py 886 / dispatch_helper.py 603 / pipeline/cli.py 345 / state.py 207 / review_checklist.py 205 / style_learning/compute_stats.py 185 等
- 全清单: `d1-06-coverage-gaps.txt`（每文件未覆盖行 → Z 区逐行处置）

## ⑦ CLI 冒烟
- `shenbi-validate G0 20260814` → FAIL(seed not found) — 预期（G0 需已登记 seed）
- `shenbi-score --help` / `shenbi-dispatch --help` / `shenbi-phase`(缺 round-dir 报错，正常) / `shenbi-sync-contracts`(PASS，输出 phase_synced) / `pipeline --help`（子命令齐全）— 全部可用

## ⑧ 凭证扫描
- 工作树 grep 高熵模式（sk-/ghp_/AKIA/PRIVATE KEY/password=/api_key=）: **0 命中**
- `git log -p --all`（1419879 行 dump）: **0 命中**
- 输出: 凭证扫描摘要 `d1-08-credential-scan-summary.md`（dump 1419879 行不入库）

## ⑨ 依赖漏洞审计
- `uv audit` 不支持（uv 版本旧）→ 回退 `uv run pip-audit`: **No known vulnerabilities found**（shenbi 自身不在 PyPI 跳过属正常）
- 输出: `d1-09-uv-audit.log`

## ⑩ 依赖健康初判
- deptry 不可用（未安装）→ `uv tree --depth 1` + uv.lock 对照
- core deps: jieba/pydantic/pyyaml/structlog/numpy/openai/tenacity — 均有真实引用（jieba→text/cjk.py、numpy→truth_embed.py）
- **矛盾发现（F-D1-01）**: pyproject.toml:17 注释声明 sentence-transformers 移至 optional 避免 torch，但 :47 dev group 显式含 sentence-transformers → dev 安装仍拉 torch/CUDA
- torch 22 处 lock 引用，仅经 embeddings optional 链（sentence-transformers→torch），core 不直接依赖 ✓

## ⑪ skip/xfail 清点
- 源码标记: 15 处（13× pytest.skip( + 2× @pytest.mark.skipif），分布: test_docs_accuracy.py 4 / test_bridge_tracker.py 2 / 其余各 1
- 运行时 216 skipped（just check）→ `pytest -rs` 原因清单在 `d1-11-skip-reasons.log`（后台生成中）
- 清单: `d1-11-skipxfail.txt`（源码标记，Z7 逐条处置）

## ⑫ 锁定与环境一致性
- `uv lock --check`: **PASS**（Resolved 180 packages in 4ms）
- .venv 134 包 vs lock 180 包（差异为 lock 中多平台/未安装分支，T13 细查）
- 输出: `d1-12-lock-check.log`

## pre-existing 失败（单独一节）
- 无 pre-existing 失败；collect-only 触发 cov 插件输出 16.08% 假失败（F-D1-02，见 ledger）
