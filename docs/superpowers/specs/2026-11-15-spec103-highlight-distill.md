# Spec #103 · 高光复盘与成功传染（highlight-distill）：确定性选章规则、三层归因手法卡 playbook、anchors 候选池接读者信号、老化与变奏防僵化

**日期**：2026-11-15｜ **系列**：写作工艺批（authoring-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟡 P2
**动机证据**：`skills/shenbi-style-learning/SKILL.md:267-289` 自锚定范文环已存在（anchors.md 每 12 章/卷界重选 3-5 段，drafting few-shot 消费）但**候选池三源全内部结构指标**（≥35 字句达标记章／POST 摘录行／PRE 母题行）——与读者侧成功信号零关联；`truth/resonance_trend.md:12` 四维数据面完备（情感落地/场景临场感/文笔质感/读者回报/overall/confidence/human_overridden）且实测分布窄（~78-86 高分密集带）——**绝对阈值选章在高分通胀下失真**；`skills/shenbi-chapter-drafting/SKILL.md:23-29` reads 已含 style_profile 字段级+anchors.md——**消费管道现成，dispatch 零改动**；`src/shenbi/pipeline/triggers.py:201-231` 弧组插步点 + `:226-231`/`:264-270` style-learning 双 entry（periodic/volume_boundary）同 skill 双 mode 先例 + `:493-498` 卷界抑制 periodic 项机制；`src/shenbi/pipeline/revision_router.py:76` DEFAULT_RESONANCE_FLOOR=50——全链只有下限门（<floor→revision），无正向放大回路；drift-guidance 只传纠偏信号；`skills/shenbi-review-highpoint/SKILL.md` 为防御性审计（蓄压-爆发/虚化检测）非成功复盘；确定性预计算先例 `compute_stats.py`；滚动归档同构 `src/shenbi/pipeline/ledger_archive.py`；`src/shenbi/scoring.py` flag_score_collapse 分布兜底。

**触及的不变量维度**：情绪节奏、能力活性（均弱关联——消费 resonance/母题信号面与注入面，不新增门检）

---

## 0. 根因

**正向回路存在一半，缺三件**：spec #71 anchors 环已把「自己最好的文字」喂回 drafting，但——
1. **成功探测器错位**：候选池来自结构统计（统计上像范文），不是共鸣分最高（读者侧确认爆了）——放大错的东西；
2. **无机制归因**：style-learning 铁律 2「统计而非评判」——只有「是什么」没有「为什么爆」，高光无法转译为可讲、可复用、可变奏的手法；
3. **无跨卷沉淀**：anchors 每 12 章整文件重写（滚动 3-5 段），爆点配方随窗口滑走——无累积、无使用计数、无老化。

净效果：全链质量面是**纯纠偏系统**（floor 门+audit_drift+drift_guidance 全负向），「不挨骂」有保障、「能追」无机制——商业逻辑上读者被平均章留住、被高潮章转发，后者目前只靠 drafting temperature=0.90 一个参数硬扛。

**备选案已评估并否决**：「复活/扩用 review-highpoint」——它是防御审计（检查蓄压是否达标），归因方向相反；「playbook 并入 style_profile」——style_profile 每次 create_or_overwrite 整文件重算，外部条目会被统计重写抹掉，落点必须独立文件。

## 1. 任务分解

### T1 · 确定性选章 + playbook schema + G4 门
- 选章函数（代码侧，零 LLM 判断，同 compute_stats 先例）：弧窗（ch%12）top-1 ∧ `confidence=high` ∧ 非 `human_overridden` ∧ `overall ≥ 全书 running median + 5`（**相对阈值抗通胀**）；卷界卷 top-1。同输入同选章，可重放；
（**confidence 前置校准——spec #110 T3 接线**：judge-reliability 报告 confidence=high 基率 >50%，或 #115 T3 外部锚 ρ<0.3 回退成立，两闸任一触发 → confidence 从合取判据降为参考列，相对阈值单独承担；#103 plan 前置检查单须含此条）
- `style/highlight_playbook.md`（**append_dedup** key=playbook_id）：手法卡四要素——出处（章号+引文 ≤200 字 **verbatim**）／三层归因（结构：蓄放曲线与拍位；节奏：章型序列位；语言：句式与词汇层）／复用条件（适用章型 ∧ 情绪带 ∧ 前置条件）／使用计数+最近命中+状态列；**活跃卡上限 12**（有界注入）；
- G4 结构校验：四要素齐全 + 引文在出处章逐字存在（quote_verbatim 共基复用）。

**判据**：选章确定性单测（同 resonance_trend 输入→同章号）；G4 红测（缺任一要素→FAIL／引文不在出处章→FAIL）。

### T2 · 新技能 + 双 entry 插步 + 消费接线
- 新技能 `shenbi-highpoint-distill`（kind: artifact；reads：入选章正文／该章 resonance 报告证据行／前 2 章 chapter_summaries 尾窗（蓄势从哪来）／该章 plan／genre-config；writes：playbook append_dedup）；
- TRIGGER_STEPS **双 entry 同 skill 双 mode**（style-learning :226-231/:264-270 先例）：`mode="arc"`（弧组，score-arc 后、style-learning 前——distill 先产出，anchors 候选池才可消费）+ `mode="volume"`（卷界块，score-volume 后）；卷界重合时弧 entry 按 :493-498 抑制机制只跑 volume 位；
- drafting contract reads 加 `style/highlight_playbook.md`（活跃卡注入，同一 style 注入路径）；style-learning SKILL anchors 半操作化规则加**第四源**：本窗 resonance top 章段落优先进候选（把读者信号接进已有范文环）。

**判据**：TRIGGER_STEPS 含双 entry；drafting frontmatter reads 含 playbook；**消费可证**——dispatch prompt manifest（已记录 reads mode/fields）含 playbook 条目。

### T3 · 老化与防僵化
- 使用计数/最近命中列由 distill 每次运行**确定性重算**（近窗 plan 正文 grep PB-id 引用面）；
- 2 卷未命中 → 归档 `style/highlight_playbook_archive.md`（ledger_archive 同构）；活跃超限同规则老化；
- **变奏提示**（anti-rationalization 核心）：卡使用计数 ≥3 且命中间隔 <6 章 → planning prompt 注入变奏提示——**手法卡是变量集不是模板**，同一配方连用三次即对新 tell 透明（与 #96 tell 清单天然联动）；
- drift-guidance 卷界汇总一行：本卷卡命中情况；T3b（可选）：planning reads 活跃卡「复用条件」——把「怎么爆」前置到计划层。

**判据**：老化红测（13 活跃+1 新卡→最老未命中卡入 archive）；变奏提示注入测试；drift-guidance 汇总行接线。

## 2. 验收
1. T1-T3 判据全绿；
2. T1 生成测试 ≥94（手法卡归因质量：三层归因各 ≥1 句可验证陈述+引文锚定）；
3. 消费证据：manifest 含 playbook 条目（接线证明）；
4. 首个适用运行窗 2 卷窗观察：arc_payoff_trend / volume_score_trend 不降；resonance 分布不变窄（flag_score_collapse 兜底观察点）。

## 3. 风险
- **复盘归因表面化**（LLM 复盘最常见失败）：三层归因模板+引文强制锚定+G4 结构门+卷界检查点人审抽检四重约束；
- **公式僵化**：变奏提示+老化归档双闸；
- **自评悖论说明**（预答价值门）：本技能做**提炼**非审计——输入是已成章+独立 resonance 证据（审计已发生），产物过 G4 结构门+人审抽检，不违反 G3.4 独立性；
- playbook 膨胀：活跃上限 12+滚动归档（读侧有界）。
