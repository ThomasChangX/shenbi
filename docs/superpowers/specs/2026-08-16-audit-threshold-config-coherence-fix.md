> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-08-31 — 剔除 F202/F436/F603：已分别由 spec #8 PR #63 与 spec #13 PR #74 修复，SDD #35 阶段 1 驳斥子 agent 复核 + 协调者 file:line 核实) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C9，原 18 条，修订后 15 条 LIVE）| **代表 finding:** F134 | **严重度上限:** P1（F202/F232/F603/F818）| **涉及文件面:** src/shenbi/scoring.py（classify）、contracts/skills/genre_config.py、pacing_design.py、config/config_coherence.py、gates/（g3、g0、g4）、thresholds.py、genre-config.json、约 10 个技能 SKILL.md 阈值表

# 数值阈值/配置契约一致性（audit-threshold-config-coherence）

## 背景

候选元根因 D 分簇二：同一阈值/键集在 code 常量、docstring、SKILL.md 正文、genre-config 多处平行定义且互相矛盾；契约承诺的校验规则未全部编码。四类证据：

1. **阈值多源矛盾**：F134（classify 硬编码 75/60 违背阈值单源）、F411（g3.py 回退评分阈值硬编码 90，低于配置阈值 94）、F760（68 份 rubric 分档线 "75-89: PASS" 与 AGENTS.md "≥90 individual pass" 冲突）、F213（CONSTELLATION 校验区间 [15,35] 宽于 SKILL.md 权威规则 [20,30]，31-35% 漏检）、F846（pacing-design 多套 CONSTELLATION 阈值互相矛盾：15-25%/15-30%/<20%/不合格<10%>40%）、F818（foreshadowing-resolve Chase Power 参数三套体系矛盾：auto-check constants vs 正文区间表 vs chase-power.md，P1）。
2. **键集多源**：F214（_GENRE_KEYS 声称 9 键含 tropeInventory，实际 genre-config.json 8 键，键集三处平行定义）、F822（备份文件名 .bak vs .bak.YYYYMMDD 两处不一致）。（F603 resonance_global_floor float 绕过 Rule2 下限校验——已由 spec #13 PR #74 修复，剔除。）
3. **承诺规则未编码**：F232（genre-config 契约"9 条可自动检查规则"只实现 7 条——approval 必填与顶层字段数=8 完全未编码，G4 放行无审批配置，P1）。（F202 禁用维度 + 空 customRules 绕过——已由 spec #8 PR #63 修复；F436 G0.cc E11 死线——已由 spec #13 PR #74 修复，均剔除。）
4. **SKILL 正文自相矛盾的阈值/数量契约**：F806（chapter-pattern 熵评级阈值两处矛盾 + 13 模式词表与 chapterTypes 不匹配）、F808（chapter-revision 修订模式词表 3 vs 6 模式——词表面归 C8，阈值面在此）、F820（lifecycle-states.md 状态机缺 DORMANT/ACTIVE 态）、F843（review-highpoint 内部严重度矛盾：铁律 3 vs 检查执行 2）、F875（volume-outlining 跨卷钩子数量铁律≥1 vs EXACT≥3 + 张力曲线铺垫段范围 10-20% vs 15-25%）。
5. **污染散点**：F443（_load_protagonist_names 硬编码项目专属主角名"林烽"为框架默认值）。

## 修复目标

1. 每个数值阈值恰一个权威源（thresholds.py 或 genre-config），code/docstring/SKILL.md 全部引用或由 lint 对账。
2. 契约承诺的校验规则 100% 编码（genre-config 9/9）。
3. SKILL.md 阈值表与 code 校验区间一致（矛盾面二选一裁决并同步全部副本）。
4. 框架常量零项目专属值。

## 任务分解

- **T1 · 阈值单源改造（F134/F411/F760）**：classify 分档、g3 回退线、rubric 分档线全部改读 thresholds.py（或 rubric 元数据）；AGENTS.md 阈值条款与 68 份 rubric 分档线以 ≥90/≥94 现行契约为准批量对齐。
- **T2 · genre-config 契约补全（F232/F214/F822）**：补编码 approval 必填 + 顶层字段数校验；_GENRE_KEYS 以真实 genre-config.json 键集生成（或加 lint 对账）；备份文件名单源。
- **T3 · ~~死线校验接线（F436）~~**：已由 spec #13 PR #74 修复（gate_G0 现传 resonance_global_floor），本 task 修订时删除，仅保留复核确认项。
- **T4 · SKILL 阈值矛盾裁决（F213/F818/F846/F806/F808/F820/F843/F875）**：逐技能以"权威规则节"（SKILL.md 铁律节或 genre-config）裁决一组值，其余副本同步；涉及 G4 checker 区间的（F213）先改 checker 对齐权威规则。词表类矛盾（F808 模式族）与 C8 T4 联动，本 spec 只收阈值/数量面。
- **T5 · 阈值对账 lint**：扫描 SKILL.md 中数值区间模式（`\d+-\d+%`、`≥\d+`）与对应 checker 常量比对，不一致 WARN——接入 just check（与 C24 文档卫生 spec 的文档对账工具共用基础设施）。
- **T6 · 常量去污染（F443）**：删除"林烽"硬编码，主角名仅从项目数据读取。

## 批量清理（纯 M 成员）

- F134（classify 75/60）虽列 M，作为 T1 首个修复项处理；F443（"林烽"硬编码）随 T6 一行删除。

## 验收标准

1. `python3 -c "..."` 复算 F232 口径：genre-config 9 条规则全编码（无审批配置的 fixture → G4 FAIL）。
2. `uv run shenbi-validate G0 <seed>` 复核 config coherence 检查已覆盖 resonance_global_floor（F436 已修面的回归确认，不新增修复）。
3. 阈值对账 lint（T5）对 68 份 rubric + 相关 SKILL.md 实跑 exit 0（F760/F846 断言）。
4. `git grep -rn "林烽" src/` 零命中（F443 断言）。
5. `just check` 全绿。

## 风险与回滚

- 风险：F760 若裁决"75-89 PASS 合法"则要改 AGENTS.md 契约而非 68 份 rubric——裁决方向需与人类伙伴确认（本 spec 默认以 AGENTS.md ≥90 为准）。收紧 G4 校验（F202/F232）会使存量无审批配置的 round 显性 FAIL，先盘点存量。
- 回滚：T1/T2 各自独立 PR；lint 先 WARN 周期。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C9（原 18 条，2026-08-31 修订后 15 条 LIVE；F202/F436/F603 已由 spec #8 PR #63 与 spec #13 PR #74 提前修复，剔除）：

F134 F213 F214 F232 F411 F443 F760 F806 F808 F818 F820
F822 F843 F846 F875
