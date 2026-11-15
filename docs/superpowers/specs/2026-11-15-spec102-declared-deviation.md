# Spec #102 · 声明式计划偏离（declared-deviation）：deviations[] 申报协议、group-plan 三择一豁免裁定、hook defer-only 硬边界、偏离→计划进化反馈回路

**日期**：2026-11-15｜ **系列**：写作工艺批（authoring-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：`docs/framework/decisions-schema.md:30-37`（adjustments 仅 issue_id/severity/handling/rationale——漂移处置语义）与 `:95-107`（Per-Skill 表 drafting=「pacing deviations, opening」——**无计划条目偏离语义**）；`skills/shenbi-review-group-plan/SKILL.md:6-11`（contract reads 四项**不含 decisions sidecar**——审计对申报盲区）、`:75-78`（D1 四铁律：备忘 1/3/6/7/8 段全硬化）、`:195`（反合理化首条「备忘是计划，可以灵活调整→灵活调整 = 推翻承诺」——章内 improvisation 零合法通道）；`skills/shenbi-chapter-drafting/SKILL.md:32-38`（writes 双章 sidecar——通道已存在）；`src/shenbi/pipeline/revision_router.py:127-146`（BLOCKING/CRITICAL 传感）——reject 偏离自然走既有 revision 回路，**路由零改动**；引句逐字校验共基现成（`src/shenbi/gates/g4/quote_verbatim.py` + `post_declarations.py`，spec #82/#83）；P2.5 rationale 规则现成（decisions-schema.md:84-93）；shadow 降级先例（`gates/g4/shadow.py` GATE_TO_SHADOW_KEY + retention_anchor shadow 开关）。

**触及的不变量维度**：承诺与债务（钩）（弱关联——defer 偏离消费 hook_age/承接行校验，不新增门检）；情绪节奏（弱关联——备忘 1/6 段豁免裁定面，三硬闸语义不变）

---

## 0. 根因

**通道断开 + 意识形态闸**：草写者可写 sidecar、审计不读；「灵活调整=推翻承诺」把备忘八段的三种东西**同等硬化**——读者承诺（§3 兑现/§7 hook 账：赖账=信任崩塌，值得死守）、结构承诺（§6 章尾改变：缺席=静止章，值得死守）、工艺护栏（§8 禁止事项：自设边界，不可偏离但性质不同）。结果：正文中「这场戏自己长出了更好走向」的时刻没有合法表达通道，group-plan 一律判 error 强制修回计划——**计划腔散文是 AI 味的结构性根源**（#96 修表层 tell，本 spec 修服从性结构层）。

**备选案已评估并否决**：「放开审计、只查大纲级」——memo 承诺面是读者信任的机器代理（弃书信号防御），放开=丢掉已验证的门资产；「deviation 进 staging 正文注释」——审计器消费结构化数据（sidecar）是既定架构（Layer A），正文注释破坏发布卫生。

## 1. 任务分解

### T1 · schema + G4 门 + 政策开关
- `decisions-schema.md` 加 **optional** `deviations[]`（向后兼容：无偏离不写字段——非 breaking，不触发 contract-upgrade 迁移义务）：`{plan_section: "1|3|6|7", kind: replace|add|drop|redirect, quote: 备忘原文 ≥20 字（逐字）, replacement_summary, rationale（REQUIRED ≤100 字，P2.5 现成）, hook_ids: []}`；
- G4.dec（`decisions_validator.py`）扩展：quote 在对应 plan 文件**逐字存在**（复用 quote_verbatim 共基）；kind 枚举；rationale 存在；每章条数 ≤ max；`hook_ids` 非空时 kind 必须 defer 语义（drop 拒收）；
- genre-config `deviation_policy: {enabled, max_per_chapter: 2, forbid_sections: ["8"], hook_mode: "defer_only"}`；**shadow 期**：未声明偏离时审计行为与现状逐字节一致（旧语义不松动）；
- 注记：drafting 已在 decisions 生产者名册，无新 sidecar 文件——`lint_decisions_sources` 三源不受扰。

**判据**：`git grep -n "deviations" docs/framework/decisions-schema.md` 命中字段表+P2.5 行；红测三条（quote 缺失或不 verbatim→FAIL／rationale 缺→FAIL／超 max→FAIL）。

### T2 · 双 SKILL 协议（申报 + 裁定）
- drafting SKILL 自检表加「偏离申报」节（凡正文与备忘 1/3/6 段不一致处，落章前必须申报）；反合理化首条（:195）**改写非删除**：「**未声明的灵活调整 = 推翻承诺**。声明偏离不是自由度，是一份要过独立审计的自证：替代物必须等价或更强，说不出来就回计划。纯 omission 永远是 error」；
- group-plan contract reads 加 `chapters/chapter-N-decisions.json`（+N+1 双章各一）；D1 升级**三择一裁定**：endorse（替代物等价或更强，有证据）/ neutral（等价）/ reject（弱于承诺或纯 omission→照旧 BLOCKING→既有 revision 回路）；输出格式加「偏离裁定表」（四要素证据格式不变）；
- **硬边界三条**：① hook_ids 非空的偏离只认 defer——replacement_summary 须含滚入章号且 **N+1 plan 承接行存在**（程序可校验，planning N+1 预生成 sidecar 可查），drop 一律 reject（hook_age 追踪滚动的债，账不丢）；② forbid_sections 钉死 §8；③ 超 max → G4 FAIL。

**判据**：group-plan frontmatter reads 含 sidecar；红测（未声明偏离仍 BLOCKING／hook drop→reject）；绿测（endorse→无 BLOCKING／defer→N+1 承接行校验过）。

### T3 · 偏离→计划进化反馈回路
- group-plan 报告（audits/chapter-N-memo-compliance.md）裁定表自带计数（declared/endorsed/rejected）——数据落点零新增；
- drift-guidance 卷界汇总两个信号：**reject 率超阈值 → 纠偏指向 planning**（草写者连续拒绝计划=计划质量问题）；**同类 endorsed 反复出现（≥3 章同 plan_section）→ 制度化提示**（把实弹演化写回备忘模板——计划通过偏离反馈进化）。

**判据**：drift-guidance SKILL reads 含 memo-compliance 偏离计数面；planning 反馈键接线测试。

## 2. 验收
1. T1-T3 判据全绿；
2. bug-hunt：谎报偏离（quote 造不出 verbatim）与漏报偏离（正文不一致但无申报）均检出；
3. T1 生成测试 ≥94；
4. 首个适用运行窗 3 章束：偏离申报零假阳性（shadow 期对照）。

## 3. 风险
- **偷懒通道化**：三重闸（每章上限 2／独立审计裁定／reject 率趋势反馈 planning）；
- **意识形态闸松动**：反合理化表改写路径语义原样（未声明=推翻承诺），红测钉死；
- **与 #96 同文件面**（drafting SKILL + review_checklist 预计算）——**#96 落地后施工**（批次纪律）；
- 双章束 per-chapter sidecar 独立申报（双章批不共享偏离额度）。
