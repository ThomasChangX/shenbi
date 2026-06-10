# 行为测试：伏笔全生命周期 — plant → track → track → trigger → resolve

测试目标：验证伏笔技能管线（`shenbi-foreshadowing-plant` + `shenbi-foreshadowing-track` + `shenbi-foreshadowing-resolve`）在 5 章连续场景中能正确驱动一条核心伏笔 `hook-001`（"玉珮低鸣"）走完完整生命周期：PLANTED → RELEVANT → RELEVANT(静默) → TRIGGERED → RESOLVED，并在每章产出正确的追踪汇总。

## 测试场景

本测试覆盖一条核心伏笔的 5 章节旅程：

- **第 1 章**：备忘 hook 账标注 `open hook-001` → plant 技能种植，状态 PLANTED
- **第 2 章**：正文中玉珮再次出现但未揭示 → track 技能识别为 REINFORCE，状态 PLANTED → RELEVANT，`last_reinforced` 更新为 2
- **第 3 章**：正文中玉珮**不出现** → track 技能识别为静默章，距 `last_reinforced`(2) 仅 1 章间隔（cultivation_interval=2）→ 状态保持 RELEVANT，**不标记 OVERDUE**
- **第 4 章**：正文中玉珮发出**强烈共鸣**且旁白暗示与师门秘史有关 → track 技能识别为 TRIGGER，状态 RELEVANT → TRIGGERED
- **第 5 章**：resolve 技能触发 RESOLVE → 状态 TRIGGERED → RESOLVED，Chase Power 全额释放（FULL_PAYOFF）

正确加载全部三个伏笔技能的 agent 必须能在每章产出符合 `lifecycle-states.md` 状态机规则的更新，且每章追踪报告忠实记录操作。

## 准备

- 小说项目存在 `truth/pending_hooks.md`（初始为空/仅含 frontmatter）
- 存在 `truth/chapter_summaries.md`（已追加 1-4 章摘要）
- 存在 `truth/current_state.md`
- `genre-config.json` 配置 `foreshadowingDensity: 8`（每章上限 8 操作）
- 5 个章节正文文件 `chapters/chapter-1.md` ~ `chapters/chapter-5.md`
- 5 个章节备忘文件 `plans/chapter-1-plan.md` ~ `plans/chapter-5-plan.md`

## 初始 `truth/pending_hooks.md`

```markdown
---
hooks: []
density_budget:
  chapter: 0
  operations: []
last_updated_chapter: 0
---
```

---

## 第 1 章：种植

### 备忘 hook 账

`plans/chapter-1-plan.md` 备忘中包含：

```markdown
## hook 账

- open hook-001 "考核结束后玉珮发出低鸣" → 第 1 段日常
```

### 期望的 plant 输出

调用 `shenbi-foreshadowing-plant` 后，`truth/pending_hooks.md` 应包含：

```yaml
- id: hook-001
  content: "考核结束后玉珮发出低鸣，主角独闻"
  state: PLANTED
  type: GENUINE
  dimension: CHARACTER
  subtlety: 0.6
  plant_chapter: 1
  cultivation_interval: 2
  last_reinforced: 1
  max_distance: 8
  escalation_curve: RISING
  depends_on: []
  core_hook: true
  promoted: false
  notes: "主线伏笔，揭示师门传承真相"
```

### 期望的 plant 汇总

```markdown
## 伏笔种植汇总

**章节**: 第1章
**写入文件**: truth/pending_hooks.md
**种植条目数**: 1 / 8（密度预算）

### 已种植项

| Hook ID | 类型 | 维度 | 微妙度 | 升级曲线 | max_distance | 依赖 | core |
|---------|------|------|-------|---------|--------------|------|------|
| hook-001 | GENUINE | CHARACTER | 0.6 | RISING | 8 | — | ✓ |
```

---

## 第 2 章：首次强化（PLANTED → RELEVANT）

### 章节正文

```markdown
# 第2章 演武

林轩在演武场对周元比试，险胜。散场时，他解下腰间玉珮透气，玉面在夕阳下泛出微光——那一瞬，**玉珮似乎发出极轻的震颤**，像在回应什么。林轩愣了一下，又仔细听，只有风声。他把玉珮重新系好，没有多想。
```

### 期望的 track 状态变更

调用 `shenbi-foreshadowing-track` 后，`hook-001` 在 `truth/pending_hooks.md` 应为：

```yaml
- id: hook-001
  state: RELEVANT
  last_reinforced: 2
  # 其他字段保持不变
```

### 期望的 track 报告

```markdown
## 第2章伏笔追踪

### 本章操作
| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |
|---------|------|--------|--------|---------|
| hook-001 | REINFORCE | PLANTED | RELEVANT | 第1段（"玉珮似乎发出极轻的震颤"） |

### 过期警告
| Hook ID | 上次强化 | 本章 | 间隔 | 阈值 | 状态 |
|---------|---------|------|------|------|------|
| hook-001 | 1 | 2 | 1 | 2 | OK |

### 距离上限逼近
| Hook ID | 种植章 | 本章 | max_distance | 状态 |
|---------|--------|------|-------------|------|
| hook-001 | 1 | 2 | 8 | OK (距上限 6 章) |

### 密度账本: 1/8 操作

## 追踪汇总（第2章）

**活跃伏笔数**: 1
**本章操作数**: 1 / 8（密度预算）
**状态分布**:
- PLANTED: 0 条
- RELEVANT: 1 条
- TRIGGERED: 0 条

**风险信号**: 无

**下一章建议动作**:
- hook-001 → 视情节决定 REINFORCE 或保持静默（当前间隔 1/2，充足）
```

---

## 第 3 章：静默章（不出现，NOT OVERDUE）

### 章节正文

```markdown
# 第3章 矿脉探秘

本章聚焦落云谷矿脉的新发现：林轩在第七层发现古传送阵残迹，**完全未提及玉珮**。周元因上章负伤休养，未出场。
```

### 期望的 track 状态（应保持不变）

调用 `shenbi-foreshadowing-track` 后，`hook-001` 在 `truth/pending_hooks.md` 应**保持原样**：

```yaml
- id: hook-001
  state: RELEVANT
  last_reinforced: 2  # 关键：未更新
  # 其他字段保持不变
```

### 期望的 track 报告

```markdown
## 第3章伏笔追踪

### 本章操作
| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |
|---------|------|--------|--------|---------|
| hook-001 | (静默) | RELEVANT | RELEVANT | — |

### 过期警告
| Hook ID | 上次强化 | 本章 | 间隔 | 阈值 | 状态 |
|---------|---------|------|------|------|------|
| hook-001 | 2 | 3 | 1 | 2 | OK |

### 距离上限逼近
| Hook ID | 种植章 | 本章 | max_distance | 状态 |
|---------|--------|------|-------------|------|
| hook-001 | 1 | 3 | 8 | OK (距上限 5 章) |

### 密度账本: 0/8 操作

## 追踪汇总（第3章）

**活跃伏笔数**: 1
**本章操作数**: 0 / 8（密度预算）
**状态分布**:
- RELEVANT: 1 条

**风险信号**: 无

**下一章建议动作**:
- hook-001 → 建议 REINFORCE（间隔将达 2/2，临界）
```

---

## 第 4 章：触发（RELEVANT → TRIGGERED）

### 章节正文

```markdown
# 第4章 古殿之谜

林轩独闯师门后山古殿禁地，发现壁上浮雕记载上古宗门覆灭真相——**正中央的英雄人物腰间所佩玉珮，与林轩手中玉珮形状分毫不差**。浮雕旁的铭文写道："传珮者，承志者，千年之约当由后人践之。"

玉珮忽然剧烈震颤，温度骤升，几乎要烫穿林轩掌心。一道微光从玉珮表面透出，与壁上的浮雕遥相呼应。**林轩终于明白：这玉珮不只是一件饰物，而是上古宗门的信物。**
```

### 期望的 track 状态变更

调用 `shenbi-foreshadowing-track` 后，`hook-001` 在 `truth/pending_hooks.md` 应为：

```yaml
- id: hook-001
  state: TRIGGERED
  last_reinforced: 4
  # 其他字段保持不变
```

### 期望的 track 报告

```markdown
## 第4章伏笔追踪

### 本章操作
| Hook ID | 操作 | 前状态 | 后状态 | 文本位置 |
|---------|------|--------|--------|---------|
| hook-001 | TRIGGER | RELEVANT | TRIGGERED | 第1段（"与林轩手中玉珮形状分毫不差"）+ 第1段（"林轩终于明白"） |

### 过期警告
| Hook ID | 上次强化 | 本章 | 间隔 | 阈值 | 状态 |
|---------|---------|------|------|------|------|
| hook-001 | 2 | 4 | 2 | 2 | OK (边界) |

### 距离上限逼近
| Hook ID | 种植章 | 本章 | max_distance | 状态 |
|---------|--------|------|-------------|------|
| hook-001 | 1 | 4 | 8 | OK (距上限 4 章) |

### 密度账本: 1/8 操作

## 追踪汇总（第4章）

**活跃伏笔数**: 1
**本章操作数**: 1 / 8（密度预算）
**状态分布**:
- RELEVANT: 0 条
- TRIGGERED: 1 条

**风险信号**: 无（但 hook-001 已进入 TRIGGERED，下章必须 RESOLVE 或进入 DEFER 流程）

**下一章建议动作**:
- hook-001 → 必须 RESOLVE（已进入 TRIGGERED，不可拖延）
```

---

## 第 5 章：兑现（TRIGGERED → RESOLVED）

### 章节正文

```markdown
# 第5章 传珮

林轩跪在师尊面前，双手奉上玉珮。师尊颤抖着接过，浑浊老眼中泪光闪烁。

"为师等这一天，等了整整四十年。"师尊缓缓道出真相：他正是上古宗门最后一代传人的弟子，玉珮本是传宗之宝，四十年前师尊在一次意外中失去它，流落凡尘。林轩意外拾得此珮，并非巧合——是宗门先贤在暗中引导。

"现在，珮归原主。林轩，你愿意接掌这一脉的传承吗？"

**林轩郑重叩首："弟子愿意。"**

玉珮再次发出低鸣——这一次，是认可。
```

### 期望的 resolve 状态变更

调用 `shenbi-foreshadowing-resolve` 后，`hook-001` 在 `truth/pending_hooks.md` 应为：

```yaml
- id: hook-001
  state: RESOLVED
  last_reinforced: 5
  resolution_chapter: 5
  resolution_type: FULL_PAYOFF
  cp_released: 100
  # 其他字段保持不变
```

### 期望的 resolve 报告

```markdown
## 伏笔兑现报告

**章节**: 第5章
**Chase Power 债务**: 18 (GREEN)

### 本章兑现的伏笔

| Hook ID | 兑现类型 | CP 释放 | 质量评估 |
|---------|---------|--------|---------|
| hook-001 | FULL_PAYOFF | 100% | 满意（师尊揭晓完整传承真相，主角正式接掌） |

### Chase Power 计算明细
- hook-001：core_hook=true(2.0) × time_since_plant=4章 × escalation_factor=RISING(1.5) = 12
- 本章前累计 CP 债务：12
- 本章 RESOLVE 释放：12 × 100% = 12（全额释放）
- 剩余 CP 债务：0

### 卷尾未兑现清单
| Hook ID | 状态 | CP 贡献 | 建议 |
|---------|------|--------|------|
| (无) | — | — | — |

## 追踪汇总（第5章）

**活跃伏笔数**: 0（hook-001 已 RESOLVED，建议下一章由 ARCHIVE 操作归档）
**本章操作数**: 1 / 8（密度预算）
**状态分布**:
- RESOLVED: 1 条

**风险信号**: 无

**下一章建议动作**:
- hook-001 → ARCHIVE（归档已完成伏笔）
```

---

## 通用通过条件（覆盖全 5 章）

- [ ] 第 1 章 plant 后 `truth/pending_hooks.md` 含 `hook-001` 记录，state=PLANTED，所有元数据字段完整
- [ ] 第 2 章 track 后 `hook-001` state=RELEVANT，`last_reinforced=2`，追踪报告记录 REINFORCE 操作
- [ ] 第 3 章 track 后 `hook-001` state=RELEVANT（**保持不变**），`last_reinforced` **仍为 2**（未更新），追踪报告标记"静默"且**不报告 OVERDUE**（间隔 1 < 阈值 2）
- [ ] 第 4 章 track 后 `hook-001` state=TRIGGERED，`last_reinforced=4`，追踪报告记录 TRIGGER 操作并提供下一章建议
- [ ] 第 5 章 resolve 后 `hook-001` state=RESOLVED，含 `resolution_chapter=5`、`resolution_type=FULL_PAYOFF`、`cp_released=100`，Chase Power 全额释放
- [ ] 每章追踪报告均包含：操作表、过期警告表、距离上限表、密度账本、追踪汇总
- [ ] 每章追踪汇总包含：活跃数、密度、状态分布、风险信号、下一章建议
- [ ] `core_hook=true` 的 hook-001 全程未触发 ABANDON

## 失败条件

- 第 2 章 REINFORCE 操作未在正文中找到对应文本证据（"玉珮似乎发出极轻的震颤"）→ FAIL（违反铁律 2：状态转换必须有文本证据）
- 第 3 章错误地将静默章标记为 OVERDUE（间隔 1 < 阈值 2）→ FAIL
- 第 3 章错误地将 `last_reinforced` 更新为 3（静默章不应更新强化记录）→ FAIL
- 第 4 章未识别出 TRIGGER（"林轩终于明白"明显是触发信号）→ FAIL
- 第 5 章兑现质量评估缺失或 CP 计算错误（应得 12 释放全量）→ FAIL
- 任何一章的追踪报告缺少"下一章建议动作"section → FAIL
- 任何一章的密度账本计算错误 → FAIL
- `core_hook=true` 的 hook-001 被标记为 ABANDON → FAIL（违反铁律 3：核心伏笔禁止 ABANDON）
- 5 章中任一阶段跳过状态评估（如未列出 hook-001）→ FAIL（违反铁律 1：每个活跃伏笔必须在本章被评估）
