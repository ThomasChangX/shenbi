# 阶段 1 · 整体层审查报告（2026-08-15）

读过的材料：AGENTS.md、docs/architecture/overview.md、docs/framework/gates.md、docs/framework/truth-files.yaml（kind 全表）、justfile、pyproject.toml、specs/INDEX.md（活跃队列头 8 份）、.github/workflows/ 全部 8 个、executor_config.toml、run_pipeline.sh。

## 维度结论

### 1. 架构一致性 — 通过（含 2 处数字漂移，见 F006/F007）
AGENTS.md 声明的目录结构与实际一致；全部命令入口（just check/test、shenbi-validate/score/phase/dispatch/sync-contracts、pipeline 11 scripts）与 justfile + pyproject [project.scripts] 一致。漂移：AGENTS.md "67+2=69 skills" vs 磁盘 74 个 SKILL.md（F007）；overview.md "15 种 kind" vs truth-files.yaml 16 种（F006）。

### 2. 契约单一信源体系 — 通过（机制层）
frontmatter（contract.kind/reads/writes）→ shenbi-sync-contracts → deps.json/docs/skills 生成链在；三 lint + 幂等 diff 全绿（D1②）。truth-files.yaml 为手维护文档源，与 frontmatter 的双向闭合由 lint_contract_fields 守。深查归 T2/T3。

### 3. pipeline 状态机设计 — 设计一致，但存在绕过面（F002）
genesis→chapter_loop→closure + checkpoint review + retry 预算 + escalation 的设计与 overview/AGENTS.md 一致。**run_pipeline.sh 构成平行操作路径**：stuck≥3 时直接手改 pipeline-state.json 的 step_index+1 并清 retry_counts，error|failed 时 grep 到 escalation/gate/dispatch 关键词即自动 approve——绕过 checkpoint 人工决策与状态机正式迁移路径（F002，P1）。

### 4. G0-G7 门体系 — 通过
gates.md/overview 门表一致；G4 目录参数化已由 PR #42 交付。有效性深查归活跃 spec #8（gate-effectiveness）与阶段 3 线程，阶段 1 无新发现。

### 5. CI 设计 — 3 处覆盖面 findings（F001/F004/F005）
- 8 workflow 与 just check 核心链同构（ruff/format/mypy/basedpyright/lints/两段 pytest）；dependency-review、SBOM、CodeQL、yamllint workflow 校验均在。
- **nightly.yml 整体 DISABLED**（schedule 注释，仅手动 dispatch）：doc-links 371 项测试（test_doc_links.py）在任何自动环境从不运行——本地 skip（工具未装）+ nightly 禁用 = 零执行环境（F001）。
- ci.yml 契约 lint 只跑 lint_contracts + lint_repo_consistency，**缺 lint_contract_graph.py 与 scripts/lint_contract_fields.py**（just lint-contracts 三件之二）——CI 门窄于本地权威门（F004）。
- 反向：CI codegen-idempotency 的 diff 范围含 `.codex-plugin/` + autocheck docs + plugin manifests，**just check 的幂等 diff 只有 deps.json/docs/framework/skills/**——本地门窄于 CI（F005）。
- embeddings-smoke 每日自动 ✓（防 torch 升级破坏推理）。

### 6. 文档体系 — 通过（数字漂移归 F006/F007）
INDEX 活跃 23 与归档目录流程自洽（SDD #6 归档后 24→23 一致）；INDEX 不追踪归档数的约定与 v3 SDD prompt 一致。

### 7. 依赖与供应链顶层 — 通过（1 处设计权衡交 T13）
core 运行时依赖 8 个（轻）；sentence-transformers 已隔离至 optional-dependencies.embeddings，**但 dev 组直接拉回**（每 PR CI 装 torch 级依赖——测试需要 vs 供应链面扩大，权衡评估归 T13）；pip-audit + dependency-review-action + cyclonedx SBOM 防线齐；GitHub Actions 全部 major-tag 引用（@v4 等，非 SHA pin）——供应链候选归 T13。

### 8. 安全顶层设计 — 顶层无洞，脚本面 2 findings（F002/F003）
凭证零命中（D1⑧ 双面）；executor_config.toml 无敏感数据。run_pipeline.sh：`python3 -c` 字符串拼接 `$PROJECT_DIR`（含单引号路径即语法破坏，注入面）+ grep -o 解析 JSON 状态（格式微变即静默失效）（F003，与 F002 同文件不同根因——F002 是契约绕过、F003 是实现脆弱性）。深查归 T12。

### 9. 性能与资源效率顶层设计 — 机制存在，规模行为待 T16
架构上存在检索/索引层（truth-index.json、truth-embeddings.db、context_assemble 多路由 + rerank 去重）；每章循环的增长曲线（truth 体积 × 章数）无法从顶层文档判定，归 T16 标注 + 实测。

## 阶段 1 findings（F0xx 段，已录 findings-ledger.md）
| ID | 严重度 | 标题 |
|---|---|---|
| F001 | P2 | nightly.yml DISABLED → doc-links 371 项测试零自动执行环境 |
| F002 | P1 | run_pipeline.sh 自动 approve 全部 checkpoint（含 ESCALATION）+ 手改 state.json 绕状态机 |
| F003 | P2 | run_pipeline.sh python3 -c 拼接 $PROJECT_DIR 注入面 + grep 解析 JSON 脆弱 |
| F004 | P2 | ci.yml 契约 lint 面缺 graph/fields 两件（CI 窄于本地权威门） |
| F005 | P2 | just check 幂等 diff 范围缺 .codex-plugin/autocheck/plugin manifests（本地窄于 CI） |
| F006 | M | overview.md "15 种 kind" vs truth-files.yaml 实际 16 种 |
| F007 | M | AGENTS.md "69 skills" vs 磁盘 74 个 SKILL.md |
