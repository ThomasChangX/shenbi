# Spec 执行索引

> **最后更新**：2026-08-02
> **活跃 spec 数**：1 | **已归档**：95（见 `archive/`）

仅列待执行 spec；已完成/合并的 spec 已移至 `archive/`，不在此重复。
按推荐执行顺序排列；执行序列号见各 spec 文件名日期前缀。

---

## 执行队列

### #3 · PR #20 Follow-up：Dependabot 配置治理 + embeddings 可选组 CI 覆盖

- **文件**：`2026-08-02-pr20-followup-dependabot-and-embeddings-ci-design.md`
- **系列**：依赖治理（承接 #1 PR20 处置 spec 的两项 follow-up；#1 已归档）
- **状态**：Design
- **优先级**：🟡 Medium（根因未修→僵尸 PR 再生；可选组零 CI 覆盖→兼容性回归无防线）
- **方法**：新建 `.github/dependabot.yml`（当前不存在，Dependabot 以默认配置开 transitive PR）+ CI 加 embeddings 可选组覆盖
- **依赖**：PR #20（已 CLOSED）；前序 spec `archive/2026-08-02-pr20-torch-bump-disposition-design.md`；`pyproject.toml` `[project.optional-dependencies].embeddings`；`.github/workflows/`（ci/nightly/security）
- **内容**：两项 follow-up——(a) 新建 `.github/dependabot.yml` 配 `allow.dependency-type: ["direct"]` 过滤 transitive PR（根因修复，防 PR #20 式僵尸态再生）；(b) embeddings 可选组 CI 覆盖（当前 CI 全用 `--group dev` 不装 embeddings，torch/sentence-transformers 兼容性零防线）。倾向方案：nightly smoke job（B1）+ security.yml 加 `--extra embeddings`（B3）。3 阶段实施，验证：Dependabot 配置被 GitHub 加载 + embeddings import 在 CI 成功 + 前 spec 归档。
- **对应 plan**：❌ 未写（待 spec 批准后另起 plan，含 §5 四项决策：ecosystem 名、CI 方案组合、模型下载策略、PR 拆分）

---

v1 基线（Foundation / Contracts / Pipeline / Quality Gates / Context Handoff / CI / 07-19 一致性与韧性集群）已全部交付，对应 PR #1–#19 均已合并。PR #21/#22（Dependabot）+ PR #25（消除既有 warning）也已合并。

新增 spec 时在此登记（`### #NN · <title>` + 文件/系列/状态/优先级/依赖/内容/对应 plan 字段），完成后移动至 `archive/` 并从本页删除。

## 依赖关系图

```
─── v1 基线（已全部合并，PR #1–#19）───
P-1 卫生 (#3) ─┬─► P-1.E 地基补完 (#4)
               └─► Contract 单一信源 (#6/#8) ─► 一致性基础设施 (#17)
Documentation 重设计 (#10)
Novel Pipeline (#11/#13/#14) ─► 性能重设计 ─► Clean-Context Handoff (#16/#17)
Quality Gates (#7)     CI 优化 (#18)
P0 阻塞修复 (#19) ◄── 07-19 一致性与韧性集群（19 spec，全部落地）
```

> 完整合并历史见 `git log --oneline` 及各 PR。下方仅列分类导航。

## 快速参考

| 想做什么 | 先看哪个 |
|----------|----------|
| 了解 v1 整体架构 | ✅ 已合并 — `docs/architecture/overview.md` |
| 了解 Gate 体系（G0–G7） | ✅ 已合并 — `docs/framework/gates.md` |
| 查某 P-1.E 子项交付 | `archive/2026-06-15-p-1.e-foundation-completion/README.md` |
| 查 07-19 某 spec 实现细节 | `archive/2026-07-19-NN-*-design.md` |
| 查契约 / 契约一致性 | `archive/2026-07-08-contract-consistency-infrastructure-design.md`（PR #17） |
| 查 Pipeline 可靠性 / 崩溃恢复 | `archive/2026-07-19-17-pipeline-infrastructure-and-resilience-design.md` |
| 新增 spec 的写法 | 参照 `archive/` 内近期 spec 的 `> **Date/Series/Depends on/Status**` 块 |

## 归档说明

92 个已完成 spec 在 `archive/` 中，按日期排序（2026-06 ~ 07）。按系列：

- **P-1 基础卫生与地基**（`2026-06-14` ~ `2026-06-16`，含 `2026-06-15-p-1.e-foundation-completion/` 主 spec 簇）— pyproject/uv/ruff/mypy、structlog、ADR、src 布局、测试地基、CI 供应链、企业文件、文档配置；交付于 PR #3/#4
- **契约单一信源**（`2026-06-21`、`2026-06-29`、`2026-06-30`）— frontmatter 契约 + 生成物 + lint、契约执行与生产接线；交付于 PR #6/#8
- **质量门与评分**（`2026-06-22`、`2026-06-28`）— 正向质量门、分层记忆评分系统（Wave 1–4）；交付于 PR #7 及 Wave 提交
- **文档重设计**（`2026-07-01`）— 双语文档、69 技能目录；交付于 PR #10
- **Novel Pipeline**（`2026-07-01`、`2026-07-02`、`2026-07-06`）— 运行器、5 波实现、根因修复、Phase1 缺陷修复；交付于 PR #11/#13/#14
- **性能与上下文交接**（`2026-07-07` ×2）— 性能重设计、Clean-Context Handoff（decisions-sidecar + 字段级 reads）；交付于 PR #16/#17
- **一致性基础设施**（`2026-07-08`）— RoundPaths / match_field / DecisionsDoc / Producer Registry；交付于 PR #17
- **CI 优化**（`2026-07-09`）— 矩阵收缩、codegen 合并、nightly 仅 dispatch；交付于 PR #18
- **07-19 一致性与韧性集群**（`2026-07-19-01` ~ `-19`，19 个 spec）— truth-file 累积、输出校验、成本核算、配置治理、语义索引、上下文工程、并发安全、内容规划、存储优化、状态计数、生命周期、技能契约、内容质量门、结构完整性、基础设施韧性、架构优化、端到端验证；全部落地于 PR #19
- **被取代的早期文档**（`2026-06-11` 测试门、`2026-06-13` 测试完整性、`2026-06-14` P-1 卫生 v1、`2026-06-29` pipeline-runner 设计笔记）— 主题被后续 spec 重做，或随 round-test 移除（PR #12）而吸收
- **遗留（superpowers 前）**（`2026-06-08` ×2）— shenbi 设计 v1、test-plan 设计

> 技术细节查各 archive spec 正文，不在此复述。
