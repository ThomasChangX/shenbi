---
type: truth
category: state
status: initialized
---

# 伏笔种植池

## hooks
- id: hook_001
  type: FORESHADOW
  dimension: social
  subtlety: medium
  cultivation_interval: 3
  max_distance: 15
  escalation_curve: stepwise
  depends_on: "none"
  description: 催收员提及高等种姓特权豁免权，为后续阶层冲突埋伏笔
  category: 线索
  status: 已种植
  notes: 第1章种植，第3章可触发
- id: hook_002
  type: MYSTERY
  dimension: power_system
  subtlety: low
  cultivation_interval: 5
  max_distance: 25
  escalation_curve: exponential
  depends_on: "hook_001"
  description: 林烽的穿越者灵能印记的第一暗示
  category: 暗线
  status: 已种植
  notes: 第1章种植，第8章开始逐步揭示
- id: hook_003
  type: SMOKESCREEN
  dimension: political
  subtlety: high
  cultivation_interval: 10
  max_distance: 40
  escalation_curve: reversal
  depends_on: "none"
  description: 催收员暗示存在还款捷径——如果读者认为林烽会走捷径，则烟幕成功
  category: 悬念
  status: 已种植
  notes: 如果林烽选择走捷径还款，则会被卷入新富族的政治游戏，如果读者认为林烽会走捷径，如果林烽走捷径则革命路线就落空，则烟幕成功；实则林烽最终走的是革命路线

## 伏笔追踪索引
| hook_id | 类型 | 种植章 | 触发章 | 状态 |
|---------|------|--------|--------|------|
| hook_001 | FORESHADOW | 1 | 3 | 已种植 |
| hook_002 | MYSTERY | 1 | 8 | 已种植 |
| hook_003 | SMOKESCREEN | 1 | 15 | 已种植 |
