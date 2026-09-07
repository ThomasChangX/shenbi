> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08) | **Severity:** 🟡 P2（簇内全 P2，但含改写全仓的 sync_contracts 等"变更器零测"高危面）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C15）| **代表 finding:** F717 | **簇规模:** 12 条（修订后 10 条） | **严重度上限:** P2
> **范围:** tests/ 新增测试 + 覆盖率门槛 | **证据等级:** 实验佐证（Z1/Z4/Z7-a 初审，d1-06-coverage-gaps.log 数据；2026-09-08 驳斥复核后修订）
> **修订注记（2026-09-08）:** F418/F766 经驳斥复核确认已由既有测试覆盖，剔除（记 closed）；F216/F737/F738 收窄至残余面；audit_context_cache 实际路径为 `src/shenbi/pipeline/`

# C15 · 关键模块/分支零覆盖修复（zero-coverage）

## 背景（根因 + 证据）

**根因**：覆盖率只有全局 85% 单一门槛，无 per-module/per-branch 底线——改写全仓的核心路径（sync_contracts、memory_distill、dispatcher CLI 等）长期 0–56% 覆盖而无门禁报警（phase4 §1 候选元根因 F 的第三拆分）。

代表证据（F717 汇总，d1-06-coverage-gaps.log）：memory_distill 12%、score_* 检查器 not_found/SKIP 分支、sync_contracts 56%、audit_context_cache 54%、drift baseline 19%、safe_write 锁竞争 66%。

成员明细（2026-09-08 驳斥复核后）：
- **F112**（P2，存活）：sync_contracts 的 main()/render_body_into/_write_json/render_body_view 全部零测试（56%）——它是**改写 deps.json + 全部 SKILL.md 的仓内变更器**，出错即批量破坏契约文件
- **F216**（P2，收窄）：dispatcher/cli.py main() 仍 0% 覆盖；executor 的 SHENBI_G1_SKIP_READS 块（executor.py:187-205）在 executor 路径未测（既有 env 测试只打到 G1 gate 与 dispatch_helper 副本）；executor G1-fail/G2-fail/dispatch-failure 返回路径未测（ContractError 路径已有 test_dispatcher_executor.py:348/370）
- **F332**（P2，存活）：genesis auto-mode G4-continue 路径（genesis.py:362-376 `genesis_g4_continue_auto`）零测试引用
- **F417**（P2，存活）：g4/memory_distill.py 覆盖 12%，checker 主体从未被测试执行
- ~~**F418**（已剔，2026-09-08）：G2.dec 多 JSON raw_decode 恢复路径已由 tests/unit/gates/test_g2.py:519-545 与 tests/test_g4_decisions_recovery.py 覆盖~~
- **F613**（P2，存活）：revision_routing/__main__.py main() 15 行整体 0% 覆盖
- **F736**（P2，存活）："Chinese week label"测试经英文分支通过（test_title_check.py:21 用「第四周Saturday」）；中文周标签正则分支（周[一二三四五六日]，chapter_drafting.py:100-105）零覆盖
- **F737**（P2，收窄）：audit_context_cache（`src/shenbi/pipeline/audit_context_cache.py`）world_rules/style/hooks/截断大部已测（test_audit_context_cache.py，PR #183 增强）；残余：characters/volume 域分支
- **F738**（P2，收窄）：parallel_dispatch 串行重试/退避已测（test_parallel_dispatch_safety.py:227-297）；残余：并发波异常循环（dispatch_reviews_parallel 波内异常路径）
- **F765**（P2，存活）：book_spine_init G4 检查器零测试引用，77% 覆盖率为 import 虚高
- ~~**F766**（已剔，2026-09-08）：contracts 三个语义校验器分支已由 test_pacing_design_contract.py / test_genre_config_contract.py / test_foreshadowing_resolve_contract.py 覆盖~~

## 目标

1. 修订后 10 个零/低覆盖面全部建立**行为级**测试（非 import 型/常量型，吸取 C14 教训）
2. 覆盖率门槛从单一全局值升级为"全局 + per-module 底线表"，使本簇清单内的模块不能再无声跌破
3. 与 C14 分工：C14 改既有测试的断言质量，本 spec 补缺失的覆盖面

## 任务分解

### T1 · 变更器与门禁核心（优先，出错即大面积破坏）
1. **F112** sync_contracts：main() 端到端（tmp 仓库副本上跑 sync → 断言 deps.json/SKILL.md 的预期 diff）、render_body_into/_write_json/render_body_view 单元级；测试一律在 tmp_path 复制件上操作（吸取 F705 教训）
2. **F417/F765** g4 检查器主体：memory_distill、book_spine_init 各补 PASS/FAIL/SKIP 三态用例。fixture 策略（G0.9 禁手造）：book_spine_init 用真实产物 `tests/fixtures/book-spine-example.md`（conftest.py:79 的 book_spine.md 为手写脚手架，禁止作为 checker 输入）；memory_distill 用真实产物 `tests/fixtures/arc-example.md`（`generated_by: shenbi-memory-distill`）；两者若被证不可用则该子项记 deviation 并回阶段 1 重裁，禁止手造 fixture

### T2 · 管线控制流分支
3. **F216** dispatcher/cli.py：参数解析矩阵（usage/rc=1/prompt-join 分支）+ executor 的 SHENBI_G1_SKIP_READS 块与 G1-fail/G2-fail/dispatch-failure 返回路径
4. **F332** genesis auto-mode G4-continue：用 genesis fixture 走 continue 分支断言 step 推进
5. **F738** parallel_dispatch 并发波异常路径：wave 内单任务异常不串扰、结果聚合正确（串行重试已测，不重复）
6. **F737/F736** audit_context_cache characters/volume 域分支；中文周标签正则分支用真实中文日期样本
7. **F613** revision_routing/__main__.py main()：argv 矩阵（合法诊断 JSON → 路由模式 stdout 输出；非法 JSON → 错误路径）

### T3 · per-module 覆盖率底线（在 T1/T2 合入、最终 per-module 数值确定后执行）
8. 覆盖率底线表（本簇 10 面的当前值 + 5–10pp 余量设 floor），跌破即 FAIL；全局 85 维持不变
9. 底线表数据源：`pytest --cov` 产出的 per-module JSON，脚本比对（放 tools/ 或 CI step，避免第三份手写登记表——C22 教训）

### 批量清理（M 级成员）
本簇无 M 级成员。

## 验收标准（真实数据可复验）

1. `uv run pytest -n auto --cov=src/shenbi --cov-report=term` 输出中：sync_contracts ≥85%、dispatcher/cli.py ≥80%、g4/memory_distill ≥80%、g4/book_spine_init checker PASS/FAIL/SKIP 三分支覆盖均 >0、genesis auto-mode G4-continue 分支（genesis.py:362-376）覆盖 >0、revision_routing/__main__.py main() ≥80%、parallel_dispatch 并发波异常分支覆盖 >0、audit_context_cache characters/volume 分支覆盖 >0、中文周标签分支覆盖 >0（与修复前对照）
2. per-module 底线表生效：临时把任一底线调高至当前值+1 会令校验 FAIL（红灯验证一次并记录）
3. 所有新增测试遵守 C14 的红灯验证法（破坏一处被测逻辑 → 红 → 还原）
4. `just check` 全绿；无对仓库真实文件的写操作（tmp_path 隔离）

## 风险与回滚

- **风险**：补测暴露生产 bug（尤其 parallel_dispatch 并发路径）——按新 finding 立案，不得为绿而弱化断言（C14 铁律同样适用）
- **风险**：per-module 底线表可能 flaky（覆盖率随分支合并波动）——底线留 5–10pp 余量，只对簇内 10 面设线，不做全模块
- **回滚**：新增测试独立成文件，底线表是 CI 配置单点，均可独立 revert；不动生产代码

## 簇成员清单（12 条，自查用；修订后活跃 10 条）

F112, F216, F332, F417, F613, F717, F736-F738, F765（活跃）；F418, F766（2026-09-08 驳斥复核剔除——已覆盖）（代表 F717；F717 为汇总型代表条目，由成员任务并集覆盖，无独立任务）
