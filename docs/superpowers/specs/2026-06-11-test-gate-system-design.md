# Shenbi 测试门禁系统设计

> 基于 Round 001/002 执行中暴露的系统性问题，重新设计测试执行架构和强制验证体系。

## 1. 执行架构

### 1.1 三角色分离

```
调度者（Agent）              决策 subagent 派发/重试/人工介入
    │                       不可越级操作（工具硬件拒绝）
    ├── 生成器 Subagent      读 SKILL.md + 输入文件 → 产出文件 → 写盘
    ├── 评分器 Subagent      读 rubric.md + 产出文件 → 独立打分
    └── 门禁工具              依赖检查 / 写盘验证 / 字数检查 / 一致性校验
```

**三条硬规则：**

1. **生成和评分永不共享 context** — 生成 subagent 和评分 subagent 是独立调用。评分者不看到生成者的 prompt。
2. **工具内嵌依赖检查** — `scoring.py --tier T2 --phase planning` 在计算分数前先检查所有 T1 评分报告是否存在。缺一个就拒绝并返回缺失列表。
3. **进度文件由工具写入，由工具校验** — 不存在"我感觉跑完了"。Agent 不直接编辑 summary.json。

### 1.2 数据流

```
种子文件                     novel.json                  genre-config.json
目标字数：N     ──提取──→     target_words: N
                                                        chapter_word.default: 3000
                                                        chapter_word.ceiling: 10000

expected_chapters = ceil(novel.target_words / genre_config.chapter_word.default)
                 → 此值不存储，每次动态计算
```

所有硬编码值已从 novel.json 移除。`target_words` 从种子提取，`chapter_word.*` 是平台常量定义在 genre-config.json 中。修改种子目标字数 → 全世界自动重算。

## 2. Gate 体系总览

| Gate | 触发时机 | 失败行为 |
|------|---------|---------|
| G0 | Round 创建 | 拒绝创建 round |
| G1 | Subagent 派发前 | 拒绝派发 |
| G2 | Subagent 返回后 | 标记失败，重试队列 |
| G3 | 每次评分前 | 拒绝评分 |
| G4 | T1 技能评分 | 专项检查失败 → 扣分/Kill switch |
| G5 | T2 Phase 评分 | 依赖检查 + handoff 验证 |
| G6 | T3 Pipeline 评分 | 全量一致性 + 多章验证 |
| G7 | Round 关闭 | 完整性验证 |

失败输出格式：

```json
{
  "gate": "G4-chapter-drafting",
  "round": "NNN",
  "skill": "shenbi-chapter-drafting",
  "chapter": 1,
  "timestamp": "2026-06-11T...",
  "status": "FAIL",
  "checks": [
    {"id": "G2.6", "check": "word_count >= floor", "expected": ">= 3000", "actual": 2628, "resolution": "运行 length-normalizing --mode expand --target 3500"},
    {"id": "G4.meta", "check": "no_meta_narrative", "expected": "0 matches", "actual": "0 matches", "status": "PASS"}
  ],
  "blocked_action": "scoring",
  "must_fix": ["G2.6"]
}
```

## 3. Gate 详细清单

### G0 — 环境就绪

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G0.1 | 种子文件存在、可读、UTF-8 编码有效 | 拒绝创建 round |
| G0.2 | `target_words` 从种子成功提取、为 > 0 整数 | 拒绝创建 round |
| G0.3 | `expected_chapters = ceil(target_words / chapter_word.default)` 已计算 | 拒绝创建 round |
| G0.4 | 被测技能目录存在、SKILL.md 存在且 frontmatter 可解析 | 标记该技能 SKIP，不阻塞其他 |
| G0.5 | 被测技能的 rubric.md 存在且维度权重总和 = 100% | 标记该技能 SKIP |
| G0.6 | novel-output/ 目录可写 | 拒绝创建 round |
| G0.7 | scoring.py 自检通过（加载已知 rubric 和分数，输出匹配预期） | 拒绝创建 round |

### G1 — Subagent 派发前

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G1.1 | 技能声明的所有输入文件路径存在且非空 | 拒绝派发，列出缺失文件 |
| G1.2 | 输入 JSON 文件语法合法 | 拒绝派发 |
| G1.3 | 输入 YAML 文件语法合法 | 拒绝派发 |
| G1.4 | 原地修改技能：原文件已备份（.bak 存在且内容一致） | 自动备份后继续 |
| G1.5 | 同一文件不被两个并行 subagent 同时修改 | 排队等待 |

### G2 — Subagent 返回后（写盘验证）

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G2.1 | 声明产出的每个文件路径存在 | 标记失败，重试或人工介入 |
| G2.2 | 每个文件 > 0 bytes | 同上 |
| G2.3 | 每个文件 UTF-8 编码有效 | 同上 |
| G2.4 | JSON 文件语法合法 | 同上 |
| G2.5 | YAML frontmatter 语法合法、必填字段齐全 | 同上 |
| G2.6 | 章节文件：字数 ≥ chapter_word.default (floor=3000) | 自动触发 length-normalizing 重跑 |
| G2.7 | 章节文件：字数 ≤ ceiling (10000)，非重要章 ≤ 1.5×default | 标记需压缩 |
| G2.8 | 章节文件：PRE_WRITE_CHECK 块存在 | 标记失败 |
| G2.9 | 章节文件：POST_WRITE_SELF_CHECK 块存在 | 标记失败 |
| G2.10 | 文件不是模板占位符（不含"待填充"字符串作为主要内容） | 标记失败 |
| G2.11 | Truth 文件：增量操作，旧条目未被删除或修改 | 标记失败，恢复备份 |
| G2.12 | 文件内容完整无截断 | 标记失败 |

### G3 — 每次评分前（依赖检查 + 隔离验证）

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G3.1 | 所有前置技能的评分报告存在 | 拒绝评分，返回缺失列表 |
| G3.2 | 前置技能分数 ≥ 接受阈值 | 拒绝评分，返回不达标列表 |
| G3.3 | 被评文件已通过 G2 全套检查 | 拒绝评分，返回 G2 失败项 |
| G3.4 | 评分 subagent 与生成 subagent 的 agent_id 不同 | 拒绝评分 |
| G3.5 | 评分 subagent 未被用于该文件的历史评分（防记忆偏差） | 警告，不阻塞 |

### G4 — T1 技能专项 Gate

#### 生成类技能专项检查

**worldbuilding:**
- novel.json 含 title/genre/language/target_words
- genre-config.json 可解析
- story_bible.md 含 4 段标题（天地法则/社会格局/历史纵深/暗流涌动）且为散文非条目
- rules.md 含 1-10 条规则且每条含可测试标准
- locations.md 含 3-5 个地点
- truth/ 下 4 个模板文件存在且 frontmatter 完整

**character-design:**
- protagonist.md frontmatter 含 name/role/personality_tags/core_value/goal_surface/goal_deep/fear/arc_type/arc_starting/arc_turning/arc_ending/voice_profile
- voice_profile 含 speech_patterns/catchphrases/avoid_patterns 且均为非空数组
- relationships.md 存在且含关系矩阵表

**story-architecture:**
- story_frame.md frontmatter 含 surface_conflict/personal_conflict/deep_conflict 三个字段且非空
- volume_map.md 含 ≥1 卷的 Objective 和 KR

**power-system:**
- power_system.md 含等级表/进阶规则/能力边界/代价机制/力量天花板/跨级战斗参考

**faction-builder:**
- factions.md 含 ≥2 势力且每个含层级结构/内部矛盾/跨势力关系/利益驱动行为

**location-builder:**
- locations.md 每个地点含布局描述/氛围锚点/功能事件

**relationship-map:**
- relationships.md 含详细关系对且每个含利益根基/信息边界/演化轨迹

**pacing-design:**
- rhythm_principles.md 含四拍循环/三线比例/场景类型目录(≥6种)/单调性检测规则

**plot-thread-weaver:**
- thread_map.md 含 A/B/C 三级线索、章节线索推进表、空白检测

**volume-outlining:**
- volume_map.md 含该卷 Objective/Key Results/卷内张力曲线/跨卷桥接

**chapter-planning:**
- chapter-N-plan.md 含全部 8 段备忘
- 第 1-3 章额外含黄金三章约束

**chapter-drafting:**
- PRE_WRITE_CHECK 块存在
- POST_WRITE_SELF_CHECK 块存在且转折词密度已计算
- 转折词(然/不过/此时/突然/终于/于是)密度 ≤ 1/3000
- 疲劳词命中 ≤ 3
- 未出现"让人感悟/引人深思/由此可见/综上所述/值得注意的是"等元叙事句式
- 字数 ≥ floor(3000)

**foreshadowing-plant:**
- pending_hooks.md 每条新 hook 含 full metadata: type/dimension/subtlety/cultivation_interval/max_distance/escalation_curve/depends_on
- depends_on 不为 null（空填 []）
- 本章操作数 ≤ 8
- SMOKESCREEN 类 hook 的 notes 字段含退出策略

**context-composing:**
- context/chapter-N-context.md 含 P1-P7 全部优先级段
- P1(计划)和 P2(近章摘要)非空

**state-settling:**
- current_state.md 含本章位置/资源变化
- character_matrix.md 含本章新出场角色
- emotional_arcs.md 含本章情绪轨迹
- chapter_summaries.md 末尾含本章摘要

**style-polishing:**
- 润色说明块存在
- 字数变化 ≤ ±15%
- 润色说明中每条修改标注了位置和原文→改文

**anti-detect:**
- 改写报告块存在
- 应用手法和位置已列出

**length-normalizing:**
- 归一化后字数 ≥ floor 且 ≤ ceiling，或 25% 底线 REJECT 已触发且记录

#### Bug-hunt 类专项检查

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G4.b1 | 产出报告命中场景声明的 planted defect | Kill switch → 总分 0 |
| G4.b2 | 未报告场景中没有的缺陷（零误报） | 每次误报 -20 分 |
| G4.b3 | 每个 finding 标注 severity 和 evidence location | 缺失 → 0 分 |

#### Clean 类专项检查

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G4.c1 | 报告 issues 数量 = 0 | 任何 finding → Kill switch，总分 0 |
| G4.c2 | 报告包含"已检查 X 维度，全部通过"摘要 | 缺失 → 不完整扣分 |

### G5 — T2 Phase 专项 Gate

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G5.1 | Phase 链上每个技能的 T1 分数 ≥ 阈值 | 拒绝 Phase 评分 |
| G5.2 | 链上技能 N 的输出文件 = 技能 N+1 的输入文件要求（handoff） | 列出缺失 → handoff 断裂 |
| G5.3 | Cross-skill 一致性：技能 B 引用的角色名存在于技能 A 的 character 输出 | 每个孤儿引用 → 扣分 |
| G5.4 | Cross-skill 一致性：规则/地点引用可在上游输出中找到原始定义 | 每个孤儿引用 → 扣分 |
| G5.5 | Phase 预期输出文件完整存在 | 缺失文件 → 扣分 |
| G5.6 | Phase 内无回归：每个技能在 T2 中产出通过对应 T1 Gate | 回归 → Kill switch |

### G6 — T3 Pipeline 专项 Gate

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G6.1 | 实际生成章节数 ≥ ceil(expected_chapters × 50%) | 拒绝 Pipeline 评分 |
| G6.2 | 章节文件序列无断号（ch1→ch2→ch3 连续） | 缺失章 → 标记 gap |
| G6.3 | 每一章通过 G2 全套 + G4 chapter-drafting Gate | 失败章列表返回 |
| G6.4 | PLANTED 状态 hook 的 last_reinforced ≥ 最近 3 章中至少 1 章（P0 类） | 沉默 hook → 扣分 |
| G6.5 | 当前章 - plant_chapter > max_distance 的 hook 数 = 0 | 每个过期 hook → 扣分 |
| G6.6 | character_matrix 中标记"死亡"的角色不出现在后续章节 | 幽灵角色 → Kill switch |
| G6.7 | 章节引用的每个角色名可在 character_matrix 中找到 | 孤儿引用 → 扣分 |
| G6.8 | 章节引用的每个地点名可在 locations.md 中找到 | 孤儿引用 → 扣分 |
| G6.9 | chapter_summaries.md 含全部已完成章节摘要 | 缺失 → 扣分 |
| G6.10 | current_state.md 包含最新完成章节的位置和资源快照 | 状态滞后 → 扣分 |
| G6.11 | emotional_arcs.md 含全部已完成章节的情绪轨迹 | 缺失 → 扣分 |
| G6.12 | 无平台违规内容（敏感词列表命中检查） | Kill switch → 总分 0 |

### G7 — 轮次关闭

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G7.1 | summary.json 中每个 t1_scores key ∈ skills/ 目录名 | 标记 round 无效 |
| G7.2 | summary.json 中每个技能有对应 skill-traces/ 文件 | 标记缺失 |
| G7.3 | summary.json 中每个技能有对应 t1-reports/ 文件 | 标记缺失 |
| G7.4 | novel-output/ 非空（≥ 1 生成文件） | 标记 round 无效 |
| G7.5 | 无文件仍是模板占位符（不含"待填充"） | 标记未完成 |
| G7.6 | 所有 truth 文件 frontmatter status ≠ "pending" | 标记未完成 |
| G7.7 | CHANGELOG.md 已追加本轮条目 | 自动追加 |
| G7.8 | 本轮无 FAIL 状态 Gate 悬而未决 | 标记 round 未完成 |

## 4. 工具改造

### 4.1 scoring.py

改造为内嵌依赖检查：

```python
# 新增 --tier 和 --phase 参数
# scoring.py --tier T2 --phase planning <rubric> <scores>
#   → 第一步：检查所有 T1 评分报告存在
#   → 缺失则返回 {"error": "T1 incomplete: 47/59 skills scored", "missing": [...]}
#   → 存在则继续评分

# scoring.py --tier T3 --pipeline long-form <rubric> <scores>
#   → 第一步：运行 G6.1-G6.5 脚本检查
#   → 失败则返回具体失败项
#   → 通过则继续评分

# 新增 --gate-only 模式：只跑门禁检查，不评分
```

### 4.2 validate-gate.py（新工具）

```python
# 独立的 Gate 执行器，可单独调用
# validate-gate.py G4 chapter-drafting chapter-1.md
#   → 运行 G2 + G4 chapter-drafting 全套检查
#   → 输出 JSON 结果
# validate-gate.py G7 round-002
#   → 运行 G7 全套检查
#   → 输出 JSON 结果

# 使用方式：Agent 在任何操作前可以调用此工具验证前提条件
# 关键操作（scoring.py/round-exec.sh）内部自动调用，Agent 不需要记住
```

### 4.3 round-exec.sh

```bash
# 创建 round 前运行 G0 全套检查
# round-exec.sh <model> <tier>
#   → G0.1-G0.7 全部通过才创建目录
#   → 失败则打印具体失败项并退出

# 新增 --validate 模式（已有）增强：
#   → 运行 G7.1-G7.8
#   → 输出逐项 PASS/FAIL
```

### 4.4 progress.json（新进度追踪文件）

```json
{
  "round": "003",
  "tier": "T1",
  "skills": {
    "shenbi-worldbuilding": {
      "generative": {"status": "DONE", "score": 97.0, "gate": "PASS"},
      "bug-hunt": {"status": "PENDING"},
      "clean": {"status": "PENDING"}
    },
    "shenbi-chapter-drafting": {
      "generative": {"status": "DONE", "score": 95.75, "gate": "PASS"},
      "bug-hunt": {"status": "PENDING"},
      "clean": {"status": "PENDING"}
    }
  },
  "remaining_generative": ["shenbi-review-character", "shenbi-review-continuity", "..."],
  "remaining_bug_hunt": ["shenbi-worldbuilding", "shenbi-character-design", "..."],
  "current_phase": "generative",
  "gate_blockers": []
}
```

**规则**：此文件由工具写入、由工具读取。Agent 只能读取它来了解进度，不能直接编辑。

## 5. 紧急绕过条款

在以下极端情况下允许绕过 Gate：

1. **人工显式授权**：用户在 prompt 中写 `OVERRIDE G6.1 allow T3 scoring with 3/34 chapters for preview`
2. **绕过记录**：每次绕过写入 `tests/rounds/round-NNN/overrides.json`，含时间戳、被绕过的 Gate、原因
3. **绕过不影响状态**：绕过的结果标记为 `PASS (override)`，不计入正式通过

## 6. 已消除的硬编码

| 位置 | 原值 | 修复方式 |
|------|------|---------|
| novel.json | `expected_chapters: 33` | 删除，改为动态计算 |
| novel.json | `default_chapter_words: 3000` | 移至 genre-config.json |
| novel.json | `chapter_word_floor: 3000` | 删除，= default |
| novel.json | `chapter_word_ceiling: 10000` | 移至 genre-config.json |
| 测试计划 T3 描述 | `drafting 5+ chapters` | 改为动态公式 |
| 测试计划 T3 描述 | `drafting 3 chapters` | 改为动态公式 |
| T3 Long-Form rubric D9 | `After 5 chapters` | 改为 `After ≥50% of expected_chapters` |
| T3 Long-Form rubric L3 | `drafting (5+ chapters)` | 改为动态公式 |
