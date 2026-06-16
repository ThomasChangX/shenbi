---
project: 星火燃穹：位面解放战争史
last_updated: 2026-06-12
version: 0.1.0
---

# 伏笔池

**活跃伏笔数**: 3
**已解决伏笔数**: 0

## 活跃伏笔

| Hook ID | 类型 | 维度 | 微妙度 | 升级曲线 | 种植章 | 操作 | 状态 |
|---------|------|------|--------|---------|--------|------|------|
| hook-ch1-001 | GENUINE | THEMATIC | 0.45 | RISING | 1 | plant | PLANTED |
| hook-ch1-002 | GENUINE | CHARACTER | 0.75 | RISING | 1 | plant | PLANTED |
| hook-ch1-003 | GENUINE | STRUCTURAL | 0.80 | FLAT | 1 | plant | PLANTED |

## hooks

- id: hook-ch1-001
  content: "催收员告知林烽灵能修炼贷款已逾期，墙上告示列出逾期处罚条款——强制劳役或灵能剥离。林烽第一次意识到这个世界'欠债'的含义远比现代严重。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: THEMATIC
  subtlety: 0.45
  plant_chapter: 1
  cultivation_interval: 3
  last_reinforced: 1
  max_distance: 150
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false
  notes: "种植位置：对话段落（催收员互动）+ 环境细节（墙上告示）。全书'个人债务→系统债务→文明债务'主题的起点。催收员处理为'按规矩做事的另一个庶民'，暗示压迫来自系统而非个人——这一处理本身是伏笔的一部分。"

- id: hook-ch1-002
  content: "林烽穿越后感知到空气中存在他人似乎不察的灵能嗡鸣——低频震颤像电流穿过骨骼。章末在破屋独处时，安静环境中这种感知变得更清晰。他将其归因为'穿越后遗症'。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.75
  plant_chapter: 1
  cultivation_interval: 5
  last_reinforced: 1
  max_distance: 80
  escalation_curve: RISING
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：环境探索段落（穿越后感知锈泥巷的五感描写中嵌入）+ 章末独处段落。通过日常五感描写自然嵌入，不设单独'金手指展示'段落。不展示分解/塑形/融合的具体操作。第4章首次科学揭示能力原理。"

- id: hook-ch1-003
  content: "锈泥巷灵能炉底部磨损铭文残存非庶民文字（列塔尼亚制造标记）；催收员提及'上面定的规矩，我只管执行'；邻居随口说'矿场那边又要人了，涅普的订单赶不完'——三处碎片分散嵌入不同场景，不给读者整合信息的机会。"
  state: PLANTED
  operation: plant
  type: GENUINE
  dimension: STRUCTURAL
  subtlety: 0.80
  plant_chapter: 1
  cultivation_interval: 4
  last_reinforced: 1
  max_distance: 60
  escalation_curve: FLAT
  depends_on: []
  core_hook: false
  promoted: false
  notes: "种植位置：三处碎片分别嵌入——(1)环境探索段落（灵能炉铭文）、(2)对话段落（催收员台词）、(3)邻里对话段落（邻居随口提及）。分散在不同场景中阻止读者首次阅读时整合。FLAT曲线保持碎片化暗示节奏，第3章起逐步具象化后转为RISING。"

---

## 第1章伏笔追踪

### 本章操作

| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |
|---------|------|--------|--------|---------|
| hook-ch1-001 | PLANT（新建） | — | PLANTED | 催收员对话段 + 墙上告示 |
| hook-ch1-002 | PLANT（新建） | — | PLANTED | 穿越后环境感知 + 章末独处 |
| hook-ch1-003 | PLANT（新建） | — | PLANTED | 灵能炉铭文 + 催收员台词 + 邻居台词 |

### 过期警告

| Hook ID | 上次强化 | 本章 | 间隔 |
|---------|---------|------|------|
| — | — | — | — |

无过期警告——所有伏笔均为本章新种植，培育间隔尚未开始计数。

### 距离上限逼近

| Hook ID | 种植章 | 本章 | max_distance | 状态 |
|---------|--------|------|-------------|------|
| hook-ch1-001 | 1 | 1 | 150 | OK (距上限 149 章) |
| hook-ch1-002 | 1 | 1 | 80 | OK (距上限 79 章) |
| hook-ch1-003 | 1 | 1 | 60 | OK (距上限 59 章) |

### 密度账本: 3/8 操作

---

## 追踪汇总（第1章）

**活跃伏笔数**: 3
**本章操作数**: 3 / 8（密度预算）
**状态分布**:
- PLANTED: 3 条
- RELEVANT: 0 条
- TRIGGERED: 0 条

**风险信号**:
- 无——所有伏笔均为第一章新种植

**下一章建议动作**:
- hook-ch1-001：建议 REINFORCE——作为核心伏笔（core_hook=true），应在第2-3章中通过林烽应对债务的实际行动自然强化（cultivation_interval=3，最晚第4章前需强化）
- hook-ch1-002：可在第2章日常生活场景中自然强化灵能感知描写（cultivation_interval=5，第6章前均可）
- hook-ch1-003：在第2章继续碎片化暗示，不整合信息（FLAT曲线，cultivation_interval=4）

**Phase 1 限制声明**：伏笔系统（foreshadowing-plant/track/resolve）尚未完全实现，`pending_hooks.md` 为初始化伏笔池。本追踪操作仅更新 `last_reinforced` 和 `subtlety` 字段，不推进 hook 生命周期状态（PLANTED→RELEVANT 等）。生命周期转换需要完整的验证逻辑，留给 foreshadowing-track 未来阶段实现。
