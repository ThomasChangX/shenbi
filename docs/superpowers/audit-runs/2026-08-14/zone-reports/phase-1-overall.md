# 阶段 1 · 整体层审查报告（协调者亲审）

> 8 维度逐项结论。阅读材料：AGENTS.md / docs/architecture/overview.md / docs/framework/{gates,dispatcher,logging,scoring,decisions-schema,chapter-file-format}.md / docs/superpowers/specs/INDEX.md / justfile / pyproject.toml / .github/workflows/*（8 个）/ command-to-give.md / goal-prompt.md / README.md / CHANGELOG.md / SECURITY.md / run_pipeline.sh / executor_config.toml / mkdocs.yml / cliff.toml / truth-files.yaml + index.json / deps.json

## 1. 架构一致性 — findings: F0-01, F0-02, F0-03, F0-05, F0-06
- AGENTS.md 目录结构声明 vs 实际：基本一致（src 分层、tests、skills、docs 均存在）
- **skills 数量漂移**：AGENTS.md:19 声称 "67 functional + 2 meta = 69"；README.md:10 声称 67 写作技能；docs/skills/index.md:189 声称 69（67+2）。实际 `skills/` 目录 **74 个**（D1③ 确认 74 SKILL.md 全部解析成功）。数差 5。
- **gate 数量漂移**：overview.md:55 "八道门（G0–G7）"、gates.md:3 "8 validation gates"、README "8 道质量门控"。实际 `shenbi-validate` CLI 支持 **11 个 gate**：G0-G7 + G_TRANSITION + G_DISPATCH + G_RECONCILE（cli.py:61,131-133）。3 个额外 gate 在全部活跃文档中 **0 引用**（grep 非 archive 文档无命中）。g_dispatch.py/g_reconcile.py/g_transition.py 存在且有测试（tests/unit/gates/test_g_dispatch.py 等 3 个文件 + phase_runner 引用）。
- **command-to-give.md:48 引用已删除脚本** `tests/dispatch-subagent.sh`（0f68102 "rename novel-output → skill-output + delete dispatch shim" 删除），仍指导执行者使用。
- **python 版本三元不一致**：pyproject:8 requires-python ">=3.11"；mypy python_version="3.12"（:359）；basedpyright pythonVersion="3.11"（:378）。CI 矩阵 3.11/3.12/3.13 三版都跑。类型检查语义基准不一致。

## 2. 契约单一信源体系 — findings: F0-02, F0-04
- frontmatter → 生成物 → 执行链路设计完整（sync-contracts + 5 个 lint 脚本 + 幂等检查），D1② 9/9 通过。
- **但 deps.json 缺 5 个 skill 登记**：`shenbi-foreshadowing-lifecycle` + `shenbi-review-group-{character,craft,factual,plan}` 在 `skills/` 目录存在、在 `docs/framework/truth-files.index.json` 有 producer 登记（:24,34-37,79-81）、`executor_config.toml` 有 `[overrides."shenbi-foreshadowing-lifecycle"]` 引用——却**不在** `tests/tiers/deps.json` 任何 prerequisites/_out_of_pipeline 列表。契约三源（deps.json / truth-files.index.json / executor_config）不同步；且 lint_repo_consistency.py 等 5 个 lint 全部通过 → **lint 存在覆盖洞**（未校验 skill 目录 ↔ deps.json 完整性）。
- INDEX.md:4 声称 "已归档 99"；:80 正文声称 "97 个已完成 spec"；实际 `specs/archive/` 91 项。归档计数漂移。

## 3. pipeline 状态机设计 — 通过（无 finding）
- phase_runner.py 状态机 + T2/T3 分层设计自洽；G_TRANSITION/G_DISPATCH/G_RECONCILE 在 phase_runner 中接线（tests/unit/phase_runner/ 有覆盖）；crash_recovery.py + pipeline resume 提供恢复。细节留给 Z1/Z3 深读。

## 4. G0-G7 门体系 — 通过（无 finding，见 F0-03 文档漂移）
- 门间依赖、不可跳过性（G0 阻断→修复→重检）、幂等性（pure validation）设计符合 AGENTS.md 声明；801 gate 测试全过。G3.4 独立评分约束存在于 scoring.py。细节留给 Z4。

## 5. CI 设计 — findings: F0-07
- 8 个 workflow 与 just check 一致性：ci.yml 各步与 justfile check 一致（ruff/mypy/basedpyright/lints/pytest），codegen-idempotency 覆盖 3 个生成器。docs.yml 用 mkdocs --strict。codeql 每周。nightly 三 job 全部 DISABLED（有注释说明）。
- **SECURITY.md 声称 pip-audit "runs on every PR and weekly"**（:20-21）——security.yml 仅 push main + PR 触发，**无 schedule**；nightly.yml 也无 pip-audit job。weekly 声明无落点（漂移）。
- ci.yml:29-30 continue-on-error 覆盖 3.13 与 macos——push(main) 的 3.13 job 失败不阻断（有意，注释说明）。风险：3.13 回归信号弱（nightly 的 3.13 job 也 disabled）。

## 6. 文档体系 — findings: F0-04, F0-08
- specs/INDEX/archive 流程设计存在，但计数漂移（见上）。docs/skills/index.md 声称数据 "源自 deps.json" 却列 72 行 > deps.json 的 68（包含 5 个未登记 skill？）→ 与 F0-02 同根因。
- **coverage 注释漂移**：pyproject:447-451 注释声称 ">=90% line / >=80% branch"、"89 (not 90)"，实际 fail_under=85（:452）。注释与配置差 5 个百分点。

## 7. 依赖与供应链顶层设计 — findings: D1-01（阶段 0 录入）
- core deps 7 个均有真实引用；sentence-transformers 在 dev group（有意，embeddings-smoke.yml 说明），但 pyproject:17 注释声明 "移至 optional" 与之矛盾（dev 安装拉 torch）。效果：2 个降级路径测试永远 skip（D1-01 已录）。
- uv.lock 有 torch 22 处引用（embeddings 链），core 不直接依赖 ✓。pip-audit 0 漏洞。SBOM 在 release/security workflow 生成 ✓。

## 8. 安全顶层设计 — 通过（无 finding，细节归 T12）
- 凭证扫描 0 命中（D1⑧）；run_pipeline.sh 用 exec >(tee) + 固定 PROJECT_DIR 推导（无用户输入注入面）；executor_config.toml 纯静态配置；subprocess 调用面在 tools/pre-push-check.sh（固定命令）；capability_fs 设计留给 Z1/T12。security.yml + codeql 覆盖 CI 面。SECURITY.md 披露流程完整。
