> **Date:** 2026-08-16 | **Status:** Done (PR #132, 2026-08-31; spec v3 basis) | **原状态:** Design (Revised 2026-08-31 — 剔除 F202/F436/F603：已分别由 spec #8 PR #63 与 spec #13 PR #74 修复，SDD #35 阶段 1 驳斥子 agent 复核 + 协调者 file:line 核实) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C9，原 18 条，修订后 15 条 LIVE）| **代表 finding:** F134 | **严重度上限:** P1（F232/F818）| **涉及文件面:** src/shenbi/scoring.py（classify）、contracts/skills/genre_config.py、pacing_design.py、config/config_coherence.py、gates/（g3、g4）、thresholds.py、genre-config.json、约 10 个技能 SKILL.md 阈值表

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

- **T1 · 阈值单源改造（F134/F411/F760）**：定稿分档词表与完整映射 PASS_EXCELLENT→PASS / PASS_ACCEPTABLE→CONDITIONAL / CONDITIONAL→MARGINAL / <60 FAIL（枚举 status.py:76-82；新值经 STATUS_STRING_LITERALS 自动派生，lint_status_strings/spec #34 单源规则随动）；消费方已盘点为有界集：src 仅 scoring.py:228-235，tests 为 test_status.py:62-63 与 68 份 rubric 模板字符串；classify 分档与 g3 回退线改读 thresholds.py 常量（g3 两处 `90` 字面量按语义替换为 TEST_PASS=90，保留"个体通过线 ≠ 晋级线 94"的分层语义，不盲目抬到 94）；68 份 rubric 分档线用一次性 codemod 脚本批量对齐（验收断言 `git grep -c "75-89: PASS" tests/tiers` → 0）；AGENTS.md 阈值条款不动（≥90/≥94 即现行契约）。
- **T2 · genre-config 契约补全（F232/F214/F822）**：补编码 approval 必填（现有 `_approval_decision_valid` 收紧为 required 语义）+ 顶层键集校验——**裁决（F214）**：8 必填键 + 1 可选 `tropeInventory`（校验规则 = 键集 ⊆ `_GENRE_KEYS` 且 8 必填全在），`_GENRE_KEYS`（ownership.py:38，9 键）保留为权威；SKILL.md:296/302「恰好 8 个」改「8 必填 + 1 可选 tropeInventory」；与 `lint_key_reconciliation`（just check 在跑）对账。备份文件名单源：SKILL.md 文档侧 `.bak.YYYYMMDD` 指示改与代码侧 `.bak` 一致，且 config_coherence.py 回滚 glob 补裸 `.bak` 形态（现 glob `genre-config.json.bak.*` 不匹配无后缀的 `.bak`，两种形态都能被 rollback 收敛）。
- **T4 · SKILL 阈值矛盾裁决（F213/F818/F846/F806/F808/F820/F843/F875）**：逐技能以"权威规则节"（SKILL.md 铁律节或 genre-config）裁决一组值，其余副本同步。**F213/F846 裁决**：CONSTELLATION 为按卷型多波段设计（标准 15-25 / 开卷 30-40 / 情感 15-25 / 大战 15-25），G4 checker 硬失败带放宽为 **[15,40]**（覆盖开卷上限 40，不再复现"SKILL 合规但 G4 误拒"的 F213 形态），SKILL.md 内部把 l.91 的 15-25% 修正为与 l.192-194 按卷型表一致的口径，contract docstring 的 [20,30] 同步改 [15,40]；顺带修 pacing_design.py docstring "Exactly 8 scene types" vs 校验 6-12 的漂移，SKILL.md:~199「恰好 8 种场景类型」同步改「6-12 种」。**C8 边界**：集合成员/词表内容 → C8；集合基数与数值区间 → 本 spec（F808 的 3 vs 6 计数面归本 spec，词表内容归 C8；F820 状态数缺口归本 spec，状态机语义归 C8）。其余（F818/F806/F843/F875）按铁律节裁决同步。
- **T5 · 阈值对账 lint**：显式 allowlist 映射文件（skill → checker → 常量）驱动的对账，扫描 SKILL.md 数值区间模式（`\d+-\d+%`、`≥\d+`）仅对映射表内条目比对，不一致 WARN（首个周期 WARN-only，不 FAIL）；接入 just check（与 C24 文档卫生 spec 的文档对账工具共用基础设施）。**依赖**：T1+T4 裁决值落定后才实跑比对，避免 lint 追赶 churn。
- **T6 · 常量去污染（F443）**：删除"林烽"硬编码（chapter_drafting.py:141/162/332 三处），主角名仅从项目数据读取；无数据时的回退语义 = 空名单 + 该检查 SKIP 记录（不设默认名，保持 gate 纯度）。

## 批量清理（纯 M 成员）

- F134（classify 75/60）虽列 M，作为 T1 首个修复项处理；F443（"林烽"硬编码，三处站点）随 T6 清除。

## 验收标准

1. F232 口径：genre-config 契约规则全编码——单测中以真实 fixture 的内存 dict 去掉 approval 键后 `GenreConfig.model_validate` 抛校验错（G0.9：不手造 fixture 文件，改内存变体）；顶层键集校验对多余键 FAIL。
2. F411/F134 口径：`git grep -n "= 90" src/shenbi/gates/g3.py` 零命中（改读 TEST_PASS）；`git grep -c "75-89: PASS" tests/tiers` → 0；classify 消费方测试全绿。
3. 阈值对账 lint（T5）对 allowlist 映射内 SKILL.md 实跑 exit 0（F846 断言；rubric 对齐属 T1 codemod，断言在验收 2）。
4. `git grep -rn "林烽" src/` 零命中（F443 断言）。
5. T4 各裁决面同步断言：`grep -c "15-25%" skills/shenbi-pacing-design/SKILL.md` 只出现在按卷型表语境（l.91 已改）；foreshadowing-resolve SKILL 内 CP 分档仅剩单一体系（`grep -c "GREEN_MAX\|CP > 200" skills/shenbi-foreshadowing-resolve/SKILL.md` 单源化）；lifecycle-states.md 含 DORMANT/ACTIVE；review-highpoint 缺段严重度单一口径；volume-outlining 钩子数量单一口径；chapter-pattern 熵分档单一口径；chapter-revision 模式计数单一口径。
6. `just check` 全绿。

## 风险与回滚

- 风险：F760 裁决方向（75-89 归 CONDITIONAL 而非 PASS）沿用 spec 既定默认——AGENTS.md ≥90 为现行契约，rubric 批量改写可由 git 反向恢复；若人类伙伴事后裁决相反，改 AGENTS.md + thresholds.py 单点即可。收紧 G4 校验（F232）会使存量无审批配置的 round 显性 FAIL——两份生产 genre-config.json 均带 approval（阶段 3 审查核实），存量面为零。
- 回滚：T1/T2 各自独立 commit；lint 先 WARN 周期。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C9（原 18 条，2026-08-31 修订后 15 条 LIVE；F202/F436/F603 已由 spec #8 PR #63 与 spec #13 PR #74 提前修复，剔除）：

F134 F213 F214 F232 F411 F443 F760 F806 F808 F818 F820
F822 F843 F846 F875
