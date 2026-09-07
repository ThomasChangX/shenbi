> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08 · SDD #52 阶段 1/2 事实核对：F730 剔除——C37 PR #179 已删孤儿模块及其测试；F739 目标 snapshot_diff.py 已被 spec #26 路径 3 删除，重定向至 audit/snapshot.py；F728 生产注入块已由 #43 覆盖，残留面仅测试体重实现；F704 仅 test_cli.py 站点存活；F743 文件已迁移 tests/unit/pipeline/test_state_heal.py；成员存活计数 26→25) | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C14）| **代表 finding:** F704 | **簇规模:** 26 条（2026-09-08 复核后存活 25）| **严重度上限:** P1
> **范围:** tests/（test_cli.py、test_scoring.py、test_safe_write.py、test_audit_context_cache.py、test_dispatch_helper_keys.py 等约 20 个文件）| **证据等级:** 实验佐证（Z7-a/Z7-b 初审，5 条 verified）

# C14 · 弱断言/自证测试修复（weak-assertions）

## 背景（根因 + 证据）

**根因**：测试不构成生产行为验证——测试体内联重实现被测逻辑（"自证"）、恒真/空断言、Mock 虚构属性、测试 pin 生产 bug 不修。绿灯与生产正确性脱钩：测试通过既不证明生产代码对，改坏生产代码也不红（phase4 §1 候选元根因 F 的第一拆分）。

代表证据（P1，均 verified）：
- **F704**：tests/unit/pipeline/test_cli.py:817-862、test_final_review_fixes.py:56-75——测试体内重实现 modify 反馈 / step 回滚 / C1 守卫逻辑，被测函数本身零执行
- **F701**：tests/unit/test_safe_write.py:62-100——lockfile 权限测试同义反复，不调用被测代码
- **F702**：tests/unit/test_scoring.py:435-441——`or True` 恒真断言掩盖 weight_mismatch 警告验证缺失
- **F728**：tests/pipeline/test_audit_context_cache.py——SharedAuditContext 注入测试在测试体内"重实现"生产注入块；生产块（dispatch_helper.py:615-634）零覆盖
- **F729**：tests/pipeline/test_dispatch_helper_keys.py——C1 回归守卫把同一 helper 调两次再断言相等（恒真），无法检测注入块 key 漂移

P2 成员（症状族）：F703（`assert len(result) >= 0` 空断言）、F705（单测改写仓库真实文件 tests/tiers/deps.json，xdist 竞态）、F712（2 处 `pytest.skip("not yet created")` 守卫过期）、F713（D16 哨兵断言被 `if g610 is not None` 包裹 → 检查消失时空洞通过）、F719（test_field_filtering 声称测 dispatch_helper 集成实际只测 contracts.fields 本体）、F730（已随 C37 删除，见头部注记）、F731（test_docs_accuracy 3 处死分支 skip 残留——目标文档现已存在）、F733（test_gate_manifest 错标 `@pytest.mark.last` 被排除且历史 list 分支零覆盖）、F734（`assertIn(state, ["scored","finalized"])`——finalize 全坏也过）、F735（TestEmergencyCleanup 零断言 + 对生产从不调用的 state.save 设 side_effect）、F739/F740（压力提示词语义与 audit/snapshot.py 记录级差分 / CASCADABLE_AUDITS 级联实现相矛盾）、F743（文件已迁移 tests/unit/pipeline/test_state_heal.py；一致性校验不查 current_step ↔ CHAPTER_STEPS[step_index]）、F744（`"chapter" in str(dict)` 近恒真残留；_INPUT_MAX_CHARS_PER_FILE 截断已被 #43 补测，本条只处理恒真断言）。

## 目标

1. 簇内 25 条存活成员全部改写或删除：每条测试断言的都是**生产代码的真实行为**（真实输入 → 真实调用 → 对真实输出的断言），消灭"测试重实现逻辑"模式
2. 建立"mutation/变异自检"导向的最低防线：对本簇修复的每个测试文件，至少注入 1 处故意破坏生产逻辑的临时变更确认会红（红灯验证法），防回潮
3. 与 C15（零覆盖）分工：本 spec 只改既有测试的断言质量，不新增覆盖面（C15 负责）

## 任务分解

### T1 · P1 五连修复（自证壳重写）
1. **F704**：删除 test_cli.py:817-862 内联重实现（存活站点两处：step 回滚 `test_modify_rolls_back_step_index`（"Simulate MODIFY: step_index should roll back to 1" 测试体内自映射 step_index）与 prompt 注入 `test_modify_injects_feedback_into_dispatch_prompt`（"Simulate dispatch prompt construction"）），改为调用生产函数（modify 反馈注入、step 回滚、C1 守卫）并对返回结构断言——test_final_review_fixes.py 站点已走生产代码（run_triggered_skills/clear_checkpoint），不再处理
2. **F701**：lockfile 权限测试改为真实触发 lockfile 竞态路径（借 tmp_path + 真实 WriteLock），断言互斥行为
3. **F702**：删除 `or True`，构造真实 weight_mismatch 输入断言警告出现；再构造匹配输入断言无警告
4. **F728**：test_audit_context_cache.py 测试体内"重实现注入逻辑"（:45-79 "Simulate the injection logic from _build_skill_prompt"）改为直接调用生产 `_build_skill_prompt` 注入块并对注入结果断言——生产块覆盖已由 #43 的 test_dispatch_helper_read_suppression.py 补齐，本条只清自证壳
5. **F729**：C1 回归守卫改为 pin 真实期望键集（硬编码期望列表 vs 生产 helper 输出比对），key 漂移即红

### T2 · P2 恒真/空断言批量改写
按文件逐条处理 F703/F705/F712/F713/F719/F731/F733-F735/F739/F740/F743/F744（F730 已由 C37 PR #179 随孤儿模块同删，剔除）：
- 空断言（F703/F734/F735 类）→ 换成具体值断言
- 过期 skip（F712/F731）→ 删守卫直接执行（文件已存在）
- 条件包裹哨兵（F713）→ 哨兵改为"检查缺失即 FAIL"方向
- 集成名不符实（F719）→ 处置定为：改 docstring/测试名为如实描述"filter_to_fields 本体单测"，迁至 tests/unit/contracts/ 或就地改名——不重写为 dispatch_helper 集成测试（该集成面已由 #43 test_dispatch_helper_read_suppression.py 覆盖，重写即重复）
- 改写真实仓库文件（F705）→ 全部换 tmp_path 隔离
- 语义矛盾提示词（F739/F740）→ 与 src/shenbi/audit/snapshot.py（记录级差分，非全量副本）/ chapter_loop.py CASCADABLE_AUDITS 实现对齐改写场景文本

### T3 · 红灯验证与防回潮
- 对本簇触及的每个测试文件执行一次"临时破坏生产代码 → 确认红 → 还原"记录（写入 PR 描述，不落库）
- 考虑在 tests/ 加一条 meta 测试：grep 检查测试文件中禁用模式（`or True` 恒真形态、`>= 0` 空断言）——模式清单以本簇症状为初始集，须带 allowlist（tests/unit/test_revision_count.py:77 的 `append(...) or True` lambda 惯用法为合法非恒真用法）

### 批量清理（M 级成员）
- **F715**：MASTER_PATH 手工保存/恢复改 pytest fixture（异常安全）+ 测试名/docstring 与行为对齐
- **F716**：弱断言/条件断言集合逐一收紧——2026-09-08 复核存活 8 站点（以符号定位为准，行号有漂移）：tests/unit/gates/test_g5.py:221、tests/unit/cost/test_report.py:34、tests/unit/pipeline/test_parallel_dispatch.py:82、tests/unit/pipeline/test_context_curation.py:30、tests/unit/test_scoring_anti_collapse.py:98-99、tests/unit/test_phase_runner.py:869-870（`if captured_outputs:` 条件包裹 `assert "stray.md" not in captured_outputs[0]`）、tests/unit/gates/test_g0.py:215-216（test_g2.py 原站点已消失）。每处改为断言单一确定状态，或注明"gate must complete, not raise"意图的显式理由。**边界**：F767 的 6 处 PASS/FAIL 双收站点归 spec #49 处置（若未修，移交回 #49 立案，不在本簇）
- **F718**：`seed` 形参未使用的 property 壳——补真实 draw 或删形参
- **F745**：executed_concurrently 测试**必须**补 barrier 交错断言（无 escape hatch）；single-writer 守卫优先行为验证，仅当目标断言是"无文件写"类否定性主张时允许保留文本级 grep，且须注明该论证（说明为何无法行为化）
- **F746**：测试名与断言对齐（returns_empty vs raises）；short title 补过 gate 断言
- **F747**：st.data() 不 draw 的伪属性——改为真实 draw
- **F748**：删行内遗留困惑注释；补 unknown-skill 分支测试

## 验收标准（真实数据可复验）

1. `grep -rn "or True" tests/ --include="*.py"` 除 allowlist（tests/unit/pipeline/test_revision_count.py:77 `escalations.append(ch) or True` lambda 惯用法）外零命中；`grep -rn "assert len(.*) >= 0" tests/` 零命中
2. F704/F728 两个测试文件中不再存在"重实现生产逻辑"的代码块（人工复查 + 机械检查：`grep -n "from shenbi\|import shenbi" <测试文件>` 非空——测试文件必须 import 被测模块）
3. 红灯验证记录：每个触及文件至少 1 处"破坏→红→还原"证据（PR 描述）
4. `just test` + `pytest -n auto -m "not last"` 全绿且无新增 skip（skip 数不增）
5. F705 修复后 `git status` 在测试运行前后保持干净（不再改写 tests/tiers/deps.json）
6. 对 dispatch_helper.py 注入块，`pytest --cov=src/shenbi/pipeline/dispatch_helper` 显示注入块行区间覆盖 >0（已由 #43 test_dispatch_helper_read_suppression.py 达成——本 spec 保持不回退即可，改写 test_audit_context_cache.py 时不得降低该覆盖）
7. 直测对象全部为生产可达路径（C37 R4 移交，2026-09-07）：C37 删除死面时已随删其直测（volume_align/_should_run_drift/compact/check_fields_exist/genre-cache/skip_write/foreshadowing_recall/_audit_context_coverage 等）；本 spec 执行时新增/改写的测试不得直接测试生产不可达函数——basedpyright reportUnusedFunction 门（C37 R3）+ 冻结白名单 lint 是机械防线

## 风险与回滚

- **风险**：改写断言可能暴露被 pin 的真实生产 bug（测试原为迁就 bug 而弱化）——发现即按 finding 新增立案，不得回退断言强度
- **风险**：部分测试改写涉及并发/竞态语义（F701/F745），可能引入 flaky——用确定性同步原语（barrier/event）而非 sleep
- **回滚**：全部改动限于 tests/，单 PR 可整体 revert；生产代码零改动（孤儿模块删除归 C37，不在本 spec 动 src/）

## 簇成员清单（26 条，自查用；2026-09-08 复核：F730 已随 C37 消亡，实际处理 25 条）

F701-F705, F712-F713, F715-F716, F718-F719, F728-F731, F733-F735, F739-F740, F743-F748（代表 F704）
