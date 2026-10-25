# Spec #73 · 大纲引擎置换与市场参数（engine-swap）

> **Date:** 2026-10-25 | **Status:** Active (Revised 2026-10-25 R1 驳斥复核：schema 落点四站补正 + pacing 换算同步 + rule-007 边界 + 锚点所有权声明) | **Severity:** 🟥 P0（内容地基） | **方法:** 引擎置换——保留账单/记名/人民史观内核，激活人物卡休眠资产为机制 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** 无（与 #72/#75 并行） | **范围:** outline/story_frame.md 四引擎规则 / genre-config.json 市场参数 / outline/rhythm_principles.md 收紧

> 源自总设计 §1（决策路径见总设计头部）。用户决策：引擎置换（非全面市场化、非只调密度）。原则：**不推翻设定，激活休眠资产**——四引擎零件已存在于人物卡（种子识衰减/怕忘记灯的脸/「攒东西的人」/贫嘴是铠甲），从修辞变机制。

## 1. 定位与边界

- 问题：volume_map Objective 明写「让读者确认本书不是重生爽文」，四个代入引擎（死亡筹码/信息优势/欲望/成长）被主题主动拆除——代入感不足的一半是设计结果。本 spec 以「引擎置换」恢复代入引擎，同时保住核心命题（预知救不了眼前人、账单不许销账、人民史观）。
- 本 spec 只改**规则层三文件**；卷一具体落位与角色卡修复归 #74。

## 2. 施工面

### 2.1 story_frame.md：四引擎规则

1. **死亡筹码→轮回代价**：每渡丢一部分记忆，先丢最不重要的（无关之人的名字→技能细节→逼近「灯的脸」）；死亡保命免费、记忆是赌注；ch1「想不起原身的名字」retroactively 为机制首演扣费；渡鸦局卡片追踪启用为慢燃威胁；他人之死永久不可逆。
2. **信息优势→预知有限变现+账房降维**：规则成文「大节点准、细节错位」（城破日/粮价走势/汛期可预知；个体位置/人心/执行路径不可知）；允许节点变现（几十文级起步）且变现引来注意（灰烬/官府盯上会算的人）；现代账房技能（复式记账/统计/审计）显性化为金手指，接信用滚动。红线：预知救不了眼前人，变现限于自保与积累。
3. **欲望→章级欲望阶梯**：卷一四级（活下来→还清债立足→护住名录上的人→名录交出去立约），每级具体 want + 可度量进度 + deadline（附籍册/征粮令天然时钟）；前台故事补「每章主角想要什么」契约。
4. **成长→账本四轴结算**：资产（钱袋余额）/信用（谁找他算账）/名录（《鉴录》名字数）/组织（持灯人关系）四轴可见进度；每卷卷末结算清单 = 遗物匣 + 四轴快照 + 渡鸦局档案卡彩蛋（既有）。

### 2.2 genre-config.json：市场参数（R1：顶层新键 market_params 四站同步）

- **schema 落点决策（R1-E）**：顶层新键 `market_params`（真 schema——嵌 pacing 子键将令「lint 可校验」验收空转）。**闭键集四站同步**（#72 primary_platform 同模式）：`contracts/ownership.py` GENRE_KEYS 11→12 + `contracts/skills/genre_config.py`（optional 字段 + 结构校验：五参数键型/值域）+ `skills/shenbi-genre-config/SKILL.md` 模板与闭键集行（「顶层仅十一键」→十二键）+ `tests/unit/contracts/test_genre_config_platform.py` 键数断言
- 参数（项目面值 + schema 值域）：
  - `payoff_density`：每 3 章 ≥1 智识小胜或变现落地（schema: `{"window": 3, "min": 1}`）
  - `emotion_band`：每章 ≥1 暖点或燃点（`{"min_per_chapter": 1}`）
  - `hook_grading`：微钩/章钩/大钩；连续 2 微钩后必须章钩（`{"max_consecutive_micro": 2}`）
  - `voice_density_min`：贫嘴声口密度下限（接线归 #76；占位值域）
  - `meme_quota`：梗位卷级配额（接线归 #76；占位值域）
- **红线自查第 4 条（R1-G 盲区）**：`payoff_density` 与既有 rule-007「现代知识碾压每卷 ≤2 次」/tropeInventory「单卷高光 ≤2 次」的边界——**智识小胜 = 本书世界内的观察/算学/组织成果，不计入「现代知识碾压」**；现代降维（复式记账等）归引擎二金手指轴另计。lint 校验不含此语义判别（内容层自查）
- **approval 块整体重写**（现 note 双 stale：7600/十键 → 3200/12 键 + 本次变更说明——SKILL.md:418 变更说明纪律）

### 2.4 交付边界（R1-D）

- 框架面（进 PR）：market_params 四站 + G4 genre_config 结构校验 + SKILL 模板 + 测试
- 项目面（工作树交付，/novel-*/ gitignored——#72 双轨惯例）：story_frame 四引擎节 + genre-config market_params 值 + rhythm_principles 收紧 + pacing 换算 + approval 重写；验收走本地 lint + 自查清单

### 2.3 rhythm_principles.md：收紧（R1：pacing 双源同步）

- 铺垫段占比 20-40% 收紧为 15-25%（驳斥复核：volume_map 卷一曲线已是 15-25%——本条是**收敛两文件**而非新造）；四拍循环增「每拍重量下限」条款（铺垫拍也须有可感知欲望推进，纯氛围章不计入有效铺垫）
- **单循环章节数换算（R1-风险1 双源）**：8-15 章（7600 字口径 = 6.1-11.4 万字/循环）→ 3200 字口径换算为 **19-36 章**（同字数带宽），三处联动：`rhythm_principles.md` :10/:17/:166 + `genre-config.json` pacing 块 `minChaptersPerCycle:8/maxChaptersPerCycle:15` → 19/36（两源同批，缺一即分叉）

### 2.5 锚点与回溯所有权声明（R1-风险 3/5/6）

- 全书 1316 锚（volume_map 头部/rhythm_principles 卷表）整体重锚至 3125/3300 口径——**归 #79 重生成**（#73 只动规则条目不重排锚表；#74 只重排卷一）；两 spec 落地后 rhythm_principles 内新旧锚并存属已知过渡态
- ch1-10 已写章的四引擎回溯核验（「每章想要什么」契约/四轴快照）——**归 #79 验收**（#73 只立规则，回溯不回改已写正文）
- G0.3 expected=3125 vs volume_map 1316 当前不一致为 **#72 遗留的预存裂缝**（#74 重排后 --apply 收敛）——#73 验收跑 lint 时不得误判为本次回归

## 3. 验收

- 三文件重写落地，四引擎规则均有**可测试表述**（时间锚可查、金额可数、名字数可数、进度轴可查）
- 引擎规则与核心命题红线无冲突（预知红线/他人之死不可逆/账单不销账三条逐条自查）
- 市场参数进入 genre-config schema，lint 可校验（R1：G4 genre_config 对 market_params 结构校验有测试——缺键/越域值 FAIL 用例）
