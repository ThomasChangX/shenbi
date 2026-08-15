> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟡 P2（簇内全 P2，但含改写全仓的 sync_contracts 等"变更器零测"高危面）
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C15）| **代表 finding:** F717 | **簇规模:** 12 条 | **严重度上限:** P2
> **范围:** tests/ 新增测试 + pyproject.toml 覆盖率门槛 | **证据等级:** 实验佐证（Z1/Z4/Z7-a 初审，d1-06-coverage-gaps.log 数据）

# C15 · 关键模块/分支零覆盖修复（zero-coverage）

## 背景（根因 + 证据）

**根因**：覆盖率只有全局 85% 单一门槛，无 per-module/per-branch 底线——改写全仓的核心路径（sync_contracts、G2 恢复分支、memory_distill、parallel_dispatch 重试、dispatcher CLI）长期 0–56% 覆盖而无门禁报警（phase4 §1 候选元根因 F 的第三拆分）。

代表证据（F717 汇总，d1-06-coverage-gaps.log）：memory_distill 12%、score_* 检查器 not_found/SKIP 分支、sync_contracts 56%、audit_context_cache 54%、drift baseline 19%、safe_write 锁竞争 66%。

成员明细：
- **F112**（P2）：sync_contracts 的 main()/render_body_into/_write_json/render_body_view 全部零测试（56%）——它是**改写 deps.json + 全部 SKILL.md 的仓内变更器**，出错即批量破坏契约文件
- **F216**（P2）：dispatcher/cli.py 覆盖 0%；executor 异常路径与 SHENBI_G1_SKIP_READS 块完全未测
- **F332**（P2）：genesis auto-mode G4-continue 路径完全未测试
- **F417**（P2）：g4/memory_distill.py 覆盖 12%，checker 主体从未被测试执行
- **F418**（P2）：g2.py G2.dec 多 JSON raw_decode 恢复路径（116-144 行）零覆盖
- **F613**（P2）：某 CLI main() 15 行整体 0% 覆盖（drift_detection 域）
- **F736**（P2）："Chinese week label"测试经英文分支通过；中文周标签正则分支（周[一二三四五六日]）零覆盖
- **F737**（P2）：audit_context_cache 模块覆盖仅 54%：world_rules/characters/style/hooks/volume 分支 + 截断函数全部未测
- **F738**（P2）：parallel_dispatch 重试/退避/异常循环（77-128、165-188 行）零覆盖；唯一测试只断言常量不等式
- **F765**（P2）：book_spine_init G4 检查器零测试引用，77% 覆盖率为 import 虚高
- **F766**（P2）：contracts/skills 三个语义校验器验证分支零覆盖（34%/38%/40%）

## 目标

1. 簇内 12 个零覆盖面全部建立**行为级**测试（非 import 型/常量型，吸取 C14 教训）
2. 覆盖率门槛从单一全局值升级为"全局 + per-module 底线表"，使本簇清单内的模块不能再无声跌破
3. 与 C14 分工：C14 改既有测试的断言质量，本 spec 补缺失的覆盖面

## 任务分解

### T1 · 变更器与门禁核心（优先，出错即大面积破坏）
1. **F112** sync_contracts：main() 端到端（tmp 仓库副本上跑 sync → 断言 deps.json/SKILL.md 的预期 diff）、render_body_into/_write_json/render_body_view 单元级；测试一律在 tmp_path 复制件上操作（吸取 F705 教训）
2. **F418** G2.dec raw_decode 恢复路径：构造多 JSON 粘连/截断/垃圾尾部的 decisions.json 样本，断言恢复语义与失败分类
3. **F417/F765** g4 检查器主体：memory_distill、book_spine_init 各补 PASS/FAIL/SKIP 三态用例（输入用 tests/fixtures 真实产物，遵守 G0.9——与 C16 协同）

### T2 · 管线控制流分支
4. **F216** dispatcher/cli.py：参数解析矩阵 + executor 异常路径 + SHENBI_G1_SKIP_READS 分支
5. **F332** genesis auto-mode G4-continue：用 genesis fixture 走 continue 分支断言 step 推进
6. **F738** parallel_dispatch 重试/退避：mock 时间推进断言退避序列与异常分类（与 C33 重试统一工作衔接，测试写 against 目标语义）
7. **F737/F736** audit_context_cache：五个 truth 域分支 + 截断函数边界；中文周标签正则分支用真实中文日期样本

### T3 · per-module 覆盖率底线
8. pyproject.toml `[tool.coverage.report]` 或 CI 步骤加底线表（本簇 12 面的当前值 + 5–10pp 余量设 floor），跌破即 FAIL；全局 85 维持不变
9. 底线表数据源：`pytest --cov` 产出的 per-module JSON，脚本比对（放 tools/ 或 CI step，避免第三份手写登记表——C22 教训）

### 批量清理（M 级成员）
本簇无 M 级成员（12 条全 P2）。

## 验收标准（真实数据可复验）

1. `uv run pytest -n auto --cov=src/shenbi --cov-report=term` 输出中：sync_contracts ≥85%、dispatcher/cli.py ≥80%、g4/memory_distill ≥80%、g4/book_spine_init checker 行覆盖 >0 且三态用例存在、g2.py 116-144 行区间覆盖 >0、parallel_dispatch 77-128/165-188 行区间覆盖 >0、audit_context_cache ≥85%、中文周标签分支覆盖 >0（与修复前 d1-06-coverage-gaps.log 逐项对照）
2. per-module 底线表生效：临时把任一底线调高至当前值+1 会令 CI FAIL（红灯验证一次并记录）
3. 所有新增测试遵守 C14 的红灯验证法（破坏一处被测逻辑 → 红 → 还原）
4. `just check` 全绿；无对仓库真实文件的写操作（tmp_path 隔离）

## 风险与回滚

- **风险**：补测暴露生产 bug（尤其 G2 恢复路径与 parallel_dispatch 重试）——按新 finding 立案，不得为绿而弱化断言（C14 铁律同样适用）
- **风险**：per-module 底线表可能 flaky（覆盖率随分支合并波动）——底线留 5–10pp 余量，只对簇内 12 面设线，不做全模块
- **回滚**：新增测试独立成文件，底线表是 CI 配置单点，均可独立 revert；不动生产代码

## 簇成员清单（12 条，自查用）

F112, F216, F332, F417-F418, F613, F717, F736-F738, F765-F766（代表 F717）
