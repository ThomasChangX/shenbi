> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-08-31) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C2，13 条）| **代表 finding:** F224 | **严重度上限:** P1（F224/F201）| **涉及文件面:** scripts/lint_contract_fields.py、35 个技能 SKILL.md frontmatter fields 声明、skills/shenbi-state-settling 模板、truth 文件真实结构（生产树 novel-output/xinghuo-ranqiong）

# Layer B 字段级 reads 机制修复（audit-layerb-field-reads）· 修订版 2026-08-31

## 修订记录（价值门 REWRITE 裁决产物）

2026-08-31 价值门复核（驳斥子 agent + 协调者逐条 VERIFY）发现原 spec 大部分主张已被 main 后续合并实现，缩窄至存活面：

**已由 main 实现核销（不再属于本 spec）**：
- T2/F201（escape-hatch）：`contracts/fields.py` `_filter_md`/`_filter_json` 均已实现「任一声明字段缺失 → 全文返回 + WARN」（PR #66 spec #9 R3，测试 `tests/unit/contracts/test_fields.py`）
- T1/F224（管线过滤接线）：`pipeline/dispatch_helper.py:637-659` 已正确处理 dict-form reads 并调用 `filter_to_fields`，管线/API 路由可达且测试覆盖（`tests/unit/pipeline/test_field_filtering.py`）。原 spec「API/codex/IDE 三条派发路由各验证一次」的表述作废——standalone 路由（dispatcher/modes/）架构上不注入文件内容（codex exec 子代理自行读盘），无过滤对象；该残留面若要处理归 #25 的 F225 议题，非本 spec
- T4（双匹配语义统一）：`fields.py` 的 `match_field` 已是单一匹配器，`scripts/lint_contract_fields.py` 直接 import 复用，无 lower/normalize 分叉
- T5（lint 入 `just check`）：`just lint-contracts`（justfile:53-56）已含 `scripts/lint_contract_fields.py`，`just check` 覆盖
- T3 大部：lint 全绿，35 个 dict-form 声明对 fixture 集合 100% 命中（F227/F824/F826/F827/F867 fixture 侧通过）
- T6/T303：AGENTS.md Layer B 示例字段（主角状态/当前世界局势/活跃线索）与 fixture `tests/fixtures/snapshots/chapter-025/truth/current_state.md` 节名一致，lint 校验通过（fixture 侧）

**存活面（本修订版的全部范围，R1-R5）**：
lint 的校验基准是 `PROJECT_DIR = REPO_ROOT` 的 fixture 解析，从未覆盖生产树 `novel-output/xinghuo-ranqiong`——原 T3 的核心裁决「以生产树为准」被实际执行为「以 fixture 为准」，四个声明漂移实例存活且 lint 不可见。

## 修复目标

恢复「声明字段 ∈ 生产树真实节名/键」的对账链，关闭 lint 的 fixture-only 盲区与样本跳过洞，并清理两处引用死亡。

## 任务分解（修订版）

- **R1 · F845 生产树/fixture 分裂对账（核心）**：生产树 `novel-output/xinghuo-ranqiong/truth/current_state.md` 的 H2 为「系统演化阶段/参数当前位置/进行中的情节线/世界状态变化（第56章）」，与声明（chapter-planning、state-settling 等：主角状态/当前世界局势/活跃线索）零交集。以生产树为准：修订声明技能的 fields 至生产树节名 + 修 state-settling 写方模板使节名稳定可声明 + 同步 fixture（fixture 必须为生产树真实产物副本，G0.9/G0.11）。若「世界状态变化（第N章）」类动态节名不可声明，裁决为该节不入 fields（靠 escape-hatch 全文回退）并在声明处注明
- **R2 · F839 volume_map 零命中 + lint 样本洞**：`skills/shenbi-review-arc-payoff/SKILL.md` 声明 `volume_promise`/`arc_beats`，但生产树 `outline/volume_map.md` 的 H2 为动态卷标题（第一卷：…），fields 语义结构性不适用（与 spec #65 的 volume_map 裁决一致：该文件不可 fields 化）。裁决：改为整文件读（去掉 fields 限定）；`scripts/lint_contract_fields.py` 的 `EXAMPLE_FIXTURES["outline/volume_map.md"] = None` no-sample 跳过洞补真实样本（生产树副本）使该路径进入校验
- **R3 · F880 DOT/声明不一致**：`skills/shenbi-style-polishing/SKILL.md:49` DOT 指示读 genre-config 的 `prohibitions`，但 frontmatter fields 只声明 `fatigueWords`，且 genre-config 契约与全部真实样本无 `prohibitions` 键——DOT 指令指向幻影键。裁决：DOT 改为与真实键集一致（fatigueWords），不新增 schema 键（新增键归 genre-config 契约面 spec #35/#2 管）
- **R4 · F844 残留死引用**：`skills/shenbi-review-pacing/SKILL.md:94` 引用 `skills/_shared/REVIEW_EVIDENCE.md`，该文件不存在（全仓唯一引用点）。裁决二选一：删除引用改为内联格式说明，或建立该共享文件；倾向删除（单引用点不值得建共享层）
- **R5 · lint 入 CI**：`scripts/lint_contract_fields.py` 在 `just check` 但不在 `.github/workflows/ci.yml`（ci.yml:53-62 无此步）。虽 CI/just 同步属 #63（C25），但该行改动一行即闭合，随本 spec 顺带完成并在 deviations 注记与 #63 的分工（#63 做 CI↔just 清单一源化时纳入）

## 验收标准（修订版）

1. `uv run python scripts/lint_contract_fields.py` exit 0，且校验基准包含生产树样本（R1/R2 的样本不再是 None 跳过或 fixture-only）——F239 复验以生产树口径零命中
2. 生产树 `current_state.md` 实跑 `filter_to_fields`（或其单测以生产树副本为 fixture）：chapter-planning 声明字段命中非空、无 escape-hatch WARN（F845 断言）
3. `git grep prohibitions skills/shenbi-style-polishing/SKILL.md` 零输出（F880 断言）；`git grep REVIEW_EVIDENCE skills/` 零输出（F844 断言）
4. `.github/workflows/ci.yml` 含 `lint_contract_fields` 步骤且 CI 全绿（R5 断言）
5. `just check` 全绿；改 SKILL.md 契约面的技能 `just generate` 幂等 diff 为空

## 风险与回滚

- R1 改变技能可见内容面（fields 换节名）：逐技能独立提交，可单技能 revert；escape-hatch 兜底保证缺字段时全文回退不失败
- R2 改整文件读会放大该技能输入（volume_map ~26KB）：token 面优化归 spec #65 的 extractor 方案，本 spec 只做正确性（声明诚实）
- fixture 更新必须是生产树真实产物精确副本（G0.9），带哈希一致校验（G0.11）

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C2（13 条，代表 F224）：F201 F224 F227 F239 F824 F826 F827 F839 F844 F845 F867 F880 T303
（修订版状态：F201/F224/F227/F239 大部/F824/F826/F827/F867/T303 已核销；存活 = F839/F844/F845/F880 + F239 的生产树口径复验）
