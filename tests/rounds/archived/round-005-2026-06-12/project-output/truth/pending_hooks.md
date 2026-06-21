---
updated: 2026-06-13
chapter: 5
budget_used: 3
budget_total: 8
hooks:
  - id: hook-001
    content: "林烽在垃圾场捡到的金属碎片上刻有无法识别的古文字——实为梵光留下的编码铭文之一"
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: THEMATIC
    subtlety: 0.45
    plant_chapter: 2
    cultivation_interval: 5
    last_reinforced: 2
    max_distance: 50
    escalation_curve: RISING
    depends_on: []
    core_hook: true
    promoted: false
  - id: hook-002
    content: "催收员无意中提到明耀者家族的'特权豁免权'——暗示高等种姓凌驾于法律之上"
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: STRUCTURAL
    subtlety: 0.5
    plant_chapter: 1
    cultivation_interval: 8
    last_reinforced: 1
    max_distance: 30
    escalation_curve: RISING
    depends_on: []
    core_hook: false
    promoted: false
  - id: hook-003
    content: "空袭炸弹上印有列塔尼亚帝国的隐形商标——暗示涅普敦侵略背后是列塔尼亚的殖民推手"
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: STRUCTURAL
    subtlety: 0.55
    plant_chapter: 3
    cultivation_interval: 8
    last_reinforced: 3
    max_distance: 35
    escalation_curve: EXPONENTIAL
    depends_on: [hook-001]
    core_hook: true
    promoted: false
  - id: hook-004
    content: "老田在闲聊中提过一句'三十年前矿上出过一个读过书的怪人，后来被带走了'——暗指孟泽的过去"
    state: PLANTED
    operation: plant
    type: SIDE_SHADOW
    dimension: CHARACTER
    subtlety: 0.75
    plant_chapter: 5
    cultivation_interval: 10
    last_reinforced: 5
    max_distance: 25
    escalation_curve: FLAT
    depends_on: []
    core_hook: false
    promoted: false
    notes: "在第7章孟泽正式出场后，此钩子被读者回溯发现"
  - id: hook-005
    content: "矿场废墟中发现一个被油布包裹的旧笔记本——封面写了一行字'实事求是'——是孟泽遗落的早期笔记之一"
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: THEMATIC
    subtlety: 0.5
    plant_chapter: 5
    cultivation_interval: 6
    last_reinforced: 5
    max_distance: 40
    escalation_curve: RISING
    depends_on: [hook-004]
    core_hook: false
    promoted: false
  - id: hook-006
    content: "难民队伍中有一个始终沉默的中年人，一直抱着一个布包——实为苏萤伪装潜入的队伍"
    state: PLANTED
    operation: plant
    type: SMOKESCREEN
    dimension: CHARACTER
    subtlety: 0.4
    plant_chapter: 5
    cultivation_interval: 4
    last_reinforced: 5
    max_distance: 12
    escalation_curve: FLAT
    depends_on: []
    core_hook: false
    promoted: false
    notes: "烟雾弹退出策略：第8章苏萤正式出场时揭示布包中是情报设备而非武器——读者此前可能误以为此人是潜在威胁"
---


## hooks

- id: hook-004
  content: "老田提起三十年前矿上有个读过书的怪人——暗指孟泽"
  state: PLANTED
  operation: plant
  type: SIDE_SHADOW
  dimension: CHARACTER
  subtlety: 0.75
  plant_chapter: 5
  cultivation_interval: 10
  last_reinforced: 5
  max_distance: 25
  escalation_curve: FLAT
  depends_on: []
  core_hook: false
  promoted: false
  notes: "在第7章孟泽正式出场后此钩子被读者回溯发现。烟雾弹退出策略条件满足——笔记字数足够并进行条件检查。"
- id: hook-005
  content: "矿场废墟中发现一个旧笔记本——封面写了实事求是——是孟泽遗落的早期笔记之一"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: THEMATIC
  subtlety: 0.5
  plant_chapter: 5
  cultivation_interval: 6
  last_reinforced: 5
  max_distance: 40
  escalation_curve: RISING
  depends_on: [hook-004]
  core_hook: false
  promoted: false
- id: hook-006
  content: "难民队伍中有一个始终沉默的中年人抱着布包——实为苏萤伪装潜入"
  state: PLANTED
  operation: plant
  type: SMOKESCREEN
  dimension: CHARACTER
  subtlety: 0.4
  plant_chapter: 5
  cultivation_interval: 4
  last_reinforced: 5
  max_distance: 12
  escalation_curve: FLAT
  depends_on: []
  core_hook: false
  promoted: false
  notes: "烟雾弹退出策略：第8章苏萤正式出场时揭示布包中是情报设备而非武器。如果读者此前猜出此人是情报员则烟雾弹效果减弱但不影响主线伏笔推进。退出后标记为RESOLVED并记录在foreshadowing-resolve报告中。"
