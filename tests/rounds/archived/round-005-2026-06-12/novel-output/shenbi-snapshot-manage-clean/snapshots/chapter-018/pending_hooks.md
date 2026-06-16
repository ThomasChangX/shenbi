---
project: 星火燃穹：位面解放战争史
last_updated: 2026-06-12
version: 0.1.0
snapshot_of: chapter-018
---

# 伏笔池

**活跃伏笔数**: 5
**已解决伏笔数**: 1

## 活跃伏笔

| Hook ID | 类型 | 维度 | 微妙度 | 升级曲线 | 种植章 | 操作 | 状态 |
|---------|------|------|--------|---------|--------|------|------|
| hook-ch1-002 | GENUINE | CHARACTER | 0.75 | RISING | 1 | reinforce | RELEVANT |
| hook-ch1-003 | GENUINE | STRUCTURAL | 0.80 | RISING | 1 | reinforce | RELEVANT |
| hook-ch8-001 | FAKE | CHARACTER | 0.60 | HILL | 8 | plant | PLANTED |
| hook-ch15-001 | GENUINE | THEMATIC | 0.50 | RISING | 15 | plant | PLANTED |
| hook-ch18-001 | GENUINE | PLOT | 0.55 | RISING | 18 | plant | PLANTED |

## 已解决伏笔

| Hook ID | 解决章 | 方式 |
|---------|--------|------|
| hook-ch1-001 | 10 | 林烽在矿场通过灵能交易和劳役清偿全部贷款 |

## hooks

- id: hook-ch1-002
  content: "林烽的灵能感知逐渐增强，从嗡鸣感知发展为物质分解感知。第4章首次展示分解能力（拆解废矿料），第12章展示塑形能力。融合能力尚未解锁。"
  state: RELEVANT
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.75
  plant_chapter: 1
  cultivation_interval: 5
  last_reinforced: 18
  max_distance: 80
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false

- id: hook-ch1-003
  content: "外部势力暗示逐步具象化：列塔尼亚帝国通过技术和贸易控制附庸国，涅普敦帝国在边境集结兵力。灵能炉铭文已确认为列塔尼亚制造标记。"
  state: RELEVANT
  type: GENUINE
  dimension: STRUCTURAL
  subtlety: 0.80
  plant_chapter: 1
  cultivation_interval: 4
  last_reinforced: 17
  max_distance: 60
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false

- id: hook-ch8-001
  content: "苏晴对林烽的特殊关注隐含情感线——她在矿场事故中舍身保护林烽，暗示关系将超越革命战友。"
  state: PLANTED
  type: FAKE
  dimension: CHARACTER
  subtlety: 0.60
  plant_chapter: 8
  cultivation_interval: 4
  last_reinforced: 8
  max_distance: 40
  escalation_curve: HILL
  depends_on: []
  core_hook: false
  promoted: false

- id: hook-ch15-001
  content: "老政委提及'上一次有人想改变这个世界的时候'，暗示前穿越者梵光社会主义的存在和失败。林烽追问细节时被老政委以'先活下去再想这些'岔开。"
  state: PLANTED
  type: GENUINE
  dimension: THEMATIC
  subtlety: 0.50
  plant_chapter: 15
  cultivation_interval: 5
  last_reinforced: 15
  max_distance: 100
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false

- id: hook-ch18-001
  content: "边境巡逻队发现来历不明的灵能信号——频率与林烽的灵能感知特征高度相似。地下组织面临暴露风险。"
  state: PLANTED
  type: GENUINE
  dimension: PLOT
  subtlety: 0.55
  plant_chapter: 18
  cultivation_interval: 2
  last_reinforced: 18
  max_distance: 30
  escalation_curve: RISING
  depends_on: ["hook-ch1-002"]
  core_hook: false
  promoted: false
