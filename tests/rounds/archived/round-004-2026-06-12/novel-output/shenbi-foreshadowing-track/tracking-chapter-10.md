---
project: 星火燃穹：位面解放战争史
last_updated: 2026-06-12
tracking_chapter: 10
tracking_date: 2026-06-12
version: 0.1.0
---

# 伏笔池（第10章追踪后更新）

**活跃伏笔数**: 3
**已解决伏笔数**: 0

## 活跃伏笔

| Hook ID | 类型 | 维度 | 微妙度 | 升级曲线 | 种植章 | 状态 | 最后强化 |
|---------|------|------|--------|---------|--------|------|---------|
| hook-ch1-001 | GENUINE | THEMATIC | 0.45 | RISING | 1 | RELEVANT | 10 |
| hook-ch1-002 | GENUINE | CHARACTER | 0.75 | RISING | 1 | RELEVANT | 10 |
| hook-ch1-003 | GENUINE | STRUCTURAL | 0.80 | FLAT | 1 | RELEVANT | 10 |

## hooks

- id: hook-ch1-001
  content: "催收员告知林烽灵能修炼贷款已逾期，墙上告示列出逾期处罚条款——强制劳役或灵能剥离。林烽第一次意识到这个世界'欠债'的含义远比现代严重。"
  state: RELEVANT
  operation: reinforce
  type: GENUINE
  dimension: THEMATIC
  subtlety: 0.45
  plant_chapter: 1
  cultivation_interval: 3
  last_reinforced: 10
  max_distance: 150
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false
  notes: "第10章强化位置：债务机制再次通过角色回忆/外部事件被提及。催收员互动中揭示的债务规则（日复利千分之三、强制劳役）在正文中得到重新引用。上次强化为第1章（种植），间隔9章（远超培育间隔3），本章REINFORCE后解除OVERDUE/CRITICAL状态。培育间隔重置，下次需在第13章前再次强化。"

- id: hook-ch1-002
  content: "林烽穿越后感知到空气中存在他人似乎不察的灵能嗡鸣——低频震颤像电流穿过骨骼。章末在破屋独处时，安静环境中这种感知变得更清晰。他将其归因为'穿越后遗症'。"
  state: RELEVANT
  operation: reinforce
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.75
  plant_chapter: 1
  cultivation_interval: 5
  last_reinforced: 10
  max_distance: 80
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false
  notes: "第10章强化位置：灵能感知通过环境描写（震颤、电荷感）和章末独处（手掌酥麻）再次呈现。上次强化为第1章（种植），间隔9章（远超培育间隔5），本章REINFORCE后解除OVERDUE/CRITICAL状态。下次需在第15章前再次强化。注意：RISING曲线在第10章应开始从'隐约感知'向'可辨识能力信号'过渡。"

- id: hook-ch1-003
  content: "锈泥巷灵能炉底部磨损铭文残存非庶民文字（列塔尼亚制造标记）；催收员提及'上面定的规矩，我只管执行'；邻居随口说'矿场那边又要人了，涅普的订单赶不完'——三处碎片分散嵌入不同场景，不给读者整合信息的机会。"
  state: RELEVANT
  operation: reinforce
  type: GENUINE
  dimension: STRUCTURAL
  subtlety: 0.80
  plant_chapter: 1
  cultivation_interval: 4
  last_reinforced: 10
  max_distance: 60
  escalation_curve: FLAT
  depends_on: []
  core_hook: false
  promoted: false
  notes: "第10章强化位置：外部势力暗示通过灵能炉铭文（齿轮徽记/展翅鸟）、催收员'上面'措辞、邻居矿场提及三处碎片再次被提及或暗示。上次强化为第1章（种植），间隔9章（远超培育间隔4），本章REINFORCE后解除OVERDUE/CRITICAL状态。下次需在第14章前再次强化。FLAT曲线保持碎片化暗示节奏。"

---

## 第10章伏笔追踪

### 本章操作

| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 | 文本证据 |
|---------|------|--------|--------|---------|---------|
| hook-ch1-001 | REINFORCE | PLANTED (CRITICAL) | RELEVANT | 第5-8段（催收员互动+告示） | 催收员揭示债务规则：本金120银盾、利息滞纳金47银盾3铜币、三个选项、强制劳役条款；墙上告示列出《管理条例》第十七条（日千分之三滞纳金）、第二十三条（强制劳役）、第三十一条（灵能僭越罪） |
| hook-ch1-002 | REINFORCE | PLANTED (CRITICAL) | RELEVANT | 第2-3段（穿越后感知）+ 第9段（章末独处） | 低频震颤描写（"像电流贴着骨头爬"→"从头骨传到脊椎再沉到脚底"）；章末手掌酥麻（"像手指上沾了一层很薄的电荷"→"木板的纤维结构在他掌心展开蓝图"） |
| hook-ch1-003 | REINFORCE | PLANTED (CRITICAL) | RELEVANT | 第4段（铭文）+ 第5段（催收员）+ 第3段（邻居） | (1)灵能炉铭牌齿轮徽记/展翅鸟；(2)催收员"上面定的规矩"、"上面"只说两次不具名；(3)邻居"矿场那边又要人了，涅普的订单赶不完"——三处碎片分散于环境描写、对话、邻里对话中 |

### 过期警告

| Hook ID | 上次强化 | 本章 | 培育间隔 | 距上次 | 状态 |
|---------|---------|------|---------|--------|------|
| hook-ch1-001 | 1 | 10 | 3 | 9/3 | **OVERDUE → 已在本章REINFORCE解除** |
| hook-ch1-002 | 1 | 10 | 5 | 9/5 | **OVERDUE → 已在本章REINFORCE解除** |
| hook-ch1-003 | 1 | 10 | 4 | 9/4 | **OVERDUE → 已在本章REINFORCE解除** |

**培育间隔分析**:
- 第1章至第10章之间（ch2-ch9）所有三个伏笔均未获得强化。在第4章时hook-ch1-001首次OVERDUE（1+3=4），第5-9章连续6次OVERDUE检查未处理 → 在第7章时达到CRITICAL状态（连续2次以上OVERDUE）。
- hook-ch1-002在第6章首次OVERDUE（1+5=6），第7-9章连续4次OVERDUE → 在第8章时达到CRITICAL。
- hook-ch1-003在第5章首次OVERDUE（1+4=5），第6-9章连续5次OVERDUE → 在第7章时达到CRITICAL。
- **幸运的是**：hook-ch1-001为core_hook（核心伏笔），不能被ABANDON。第10章通过REINFORCE操作将全部三个伏笔从CRITICAL中拯救出来。
- **教训**：第2-9章期间未能维持培育节奏，下次应确保各钩子在其培育间隔到期前获得强化。

### 距离上限逼近

| Hook ID | 种植章 | 本章 | max_distance | 剩余 | 状态 |
|---------|--------|------|-------------|------|------|
| hook-ch1-001 | 1 | 10 | 150 | 140章 | OK（宽裕） |
| hook-ch1-002 | 1 | 10 | 80 | 70章 | OK（宽裕） |
| hook-ch1-003 | 1 | 10 | 60 | 50章 | OK（宽裕） |

**距离分析**: 所有伏笔距离上限均有充足余量。hook-ch1-003的最短max_distance（60章）在当前第10章仍剩余50章，无紧迫风险。

### 密度账本: 3/8 操作

| 类别 | 计数 |
|------|------|
| REINFORCE | 3 |
| PLANT (新建) | 0 |
| TRIGGER | 0 |
| RESOLVE | 0 |
| 合计 | 3 / 8（37.5%） |

密度预算充足，第11章可考虑新建1-2个新伏笔（如引入新角色或冲突线）。

---

## 追踪汇总（第10章）

**活跃伏笔数**: 3
**本章操作数**: 3 / 8（密度预算）
**状态分布**:
- PLANTED: 0 条（全部升为RELEVANT）
- RELEVANT: 3 条
- TRIGGERED: 0 条
- RESOLVED: 0 条

**风险信号**:
- [已解除] hook-ch1-001: 培育过期9章（间隔3章），本章REINFORCE解除
- [已解除] hook-ch1-002: 培育过期9章（间隔5章），本章REINFORCE解除
- [已解除] hook-ch1-003: 培育过期9章（间隔4章），本章REINFORCE解除
- [无] 无EXPIRED伏笔
- [无] 无距离上限逼近

**下一章建议动作**:
- hook-ch1-001 → 下次强化截止第13章（培育间隔3章）。建议在第11-12章通过ORGANIC方式REINFORCE（如林烽再次面对债务后果，或新角色提及灵能贷款机制）。
- hook-ch1-002 → 下次强化截止第15章（培育间隔5章）。建议在第11-13章通过PROMOTE降低subtlety（0.75→0.55），让灵能感知从"隐约信号"过渡为"可辨识能力"，为后续能力激活做准备。RISING曲线需要在第10章后开始爬升。
- hook-ch1-003 → 下次强化截止第14章（培育间隔4章）。FLAT曲线保持碎片化暗示——但第10章后应开始由FLAT转RISING（按照notes"第3章起逐步具象化后转为RISING"的指示）。建议在第11-13章给读者提供第一块可以整合的拼图（如揭示列塔尼亚名称或展示涅普敦的具体行动）。

**第10章追踪健康度**: **可接受**（3/3个钩子均在本章获得有效REINFORCE，CRITICAL状态全部解除，密度预算充足。主要问题是第2-9章期间培育缺失——这不是第10章的问题，而是此前章节的累积债务。第10章的REINFORCE操作有效填补了部分空白，但钩子深度（读者对钩子的印象）在8章的空白期内可能已衰减。建议在第11-15章期间提高强化频率以补偿。）

---

## 追踪方法说明

### 本章操作识别过程

1. **搜索活跃伏笔关键词**: 在"第10章"正文中搜索每个活跃伏笔的`content`字段关键词
2. **验证匹配**: 确认匹配到的文本确实与该伏笔相关（非偶然词频重合）
3. **判断操作类型**: 根据匹配程度判断是REINFORCE（强化印象）/TRIGGER（触发）/RESOLVE（兑现）

### 状态转换证据

| Hook ID | 状态转换 | 正文证据（直接引用） |
|---------|---------|---------------------|
| hook-ch1-001 | PLANTED → RELEVANT | 催收员："本金一百二十银盾，三期利息加滞纳金合计四十七银盾三铜币。" 告示："逾期超过三个缴纳周期的债务人，按日加收未偿本金千分之三滞纳金。" 林烽推理："这个模型的设计初衷就不是为了让债务人还清。" |
| hook-ch1-002 | PLANTED → RELEVANT | "灌进耳膜的是一股低频震颤……胸腔跟着共振，牙根发酸。" 章末："木板的纤维结构在他掌心展开了一幅模糊的蓝图。这不是触觉。触觉摸不到这么深。" |
| hook-ch1-003 | PLANTED → RELEVANT | 铭文："齿轮中央是一只展翅的鸟。" 催收员："上面定的规矩，我按规矩跑腿。" 邻居："矿场那边又要人了，涅普的订单赶不完。" |

### 异常处理

- **Variance**: 当前pending_hooks.md记录的活跃钩子为3条（而非预期的8条，如scenario所述）。仅对实际存在的3条钩子进行评估。如第2-9章有新建钩子但未同步到pending_hooks.md，则这些钩子不在本次追踪范围内——建议审计第2-9章的钩子种植情况。
- **core_hook保护**: hook-ch1-001标记为core_hook=true，在培育严重过期（9章/间隔3章）的情况下未触发ABANDON逻辑，符合铁律3（core_hook不允许ABANDON）。即使到达CRITICAL状态，核心钩子也必须通过人工决策处理而非自动放弃。
