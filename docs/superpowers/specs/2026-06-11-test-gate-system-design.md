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

1. **生成和评分永不共享 context** — 生成 subagent 和评分 subagent 是独立调用。评分者 prompt 中不含生成者的 prompt 文本。此规则由 G3.4 的 agent_id 校验 + G3.5 的防重用校验强制执行。
2. **工具内嵌依赖检查** — `scoring.py --tier T2 --phase planning` 在计算分数前先检查所有 T1 评分报告是否存在。缺一个就拒绝并返回缺失列表。Agent 不能绕过——工具硬件拒绝，不是策略提醒。
3. **进度文件由工具写入，由工具校验** — 不存在"我感觉跑完了"。progress.json 由 `validate-gate.py` 写入，Agent 只读。summary.json 由 `summarize-round.py` 生成，Agent 不可编辑。

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

### 1.3 依赖图

G3.1 的"前置技能"由机器可读的依赖清单定义。文件位置：`tests/tiers/deps.json`。

```json
{
  "t2-phases": {
    "genesis": {
      "prerequisites": ["shenbi-worldbuilding", "shenbi-power-system", "shenbi-faction-builder", "shenbi-location-builder", "shenbi-character-design", "shenbi-relationship-map"],
      "expected_outputs": ["novel.json", "genre-config.json", "world/story_bible.md", "world/rules.md", "world/locations.md", "world/power_system.md", "world/factions.md", "characters/protagonist.md", "characters/major/*.md", "characters/relationships.md", "truth/current_state.md", "truth/character_matrix.md", "truth/emotional_arcs.md", "truth/chapter_summaries.md"]
    },
    "architecture": {
      "prerequisites": ["shenbi-story-architecture", "shenbi-pacing-design", "shenbi-plot-thread-weaver", "shenbi-genre-config"],
      "expected_outputs": ["outline/story_frame.md", "outline/volume_map.md", "outline/rhythm_principles.md", "outline/thread_map.md", "genre-config.json"]
    },
    "planning": {
      "prerequisites": ["shenbi-volume-outlining", "shenbi-chapter-planning", "shenbi-foreshadowing-plant", "shenbi-context-composing"],
      "expected_outputs": ["plans/chapter-*-plan.md", "truth/pending_hooks.md", "context/chapter-*-context.md"]
    },
    "drafting": {
      "prerequisites": ["shenbi-chapter-drafting", "shenbi-state-settling", "shenbi-foreshadowing-track", "shenbi-style-polishing", "shenbi-anti-detect", "shenbi-length-normalizing"],
      "expected_outputs": ["chapters/chapter-*.md", "truth/current_state.md", "truth/character_matrix.md", "truth/emotional_arcs.md", "truth/chapter_summaries.md", "truth/pending_hooks.md"]
    }
  },
  "t3-pipelines": {
    "long-form": {
      "prerequisites": ["genesis", "architecture", "planning", "drafting"],
      "min_chapter_ratio": 0.5
    }
  }
}
```

脚本读取 `deps.json` 确定依赖关系。添加新技能或调整 Phase 组合时只需修改此文件。

**重要**：`prerequisites` 数组的顺序定义了 handoff 链（技能 0 → 技能 1 → 技能 2 ...）。G5.2 的 handoff 完整性检查依赖此顺序——不可随意重排数组。

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
| **G_TRANSITION** | **Phase 切换（新）** | **拒绝进入下一 phase** |
| **G_DISPATCH** | **Phase 循环结束（新）** | **拒绝 Phase 完成声明** |
| **G_RECONCILE** | **每 5 个 subagent / Phase 边界（新）** | **标记不一致项** |

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
| G0.4 | 被测技能目录不存在 → HARD FAIL，拒绝创建 round；目录存在但 SKILL.md 缺失 → SKIP + 警告；目录存在且 SKILL.md 存在 → PASS | 见左列 |
| G0.5 | 被测技能的 rubric.md 存在且维度权重总和 = 100% | SKIP + 警告（目录存在时） |
| G0.6 | novel-output/ 目录可写 | 拒绝创建 round |
| G0.7 | scoring.py 自检通过（加载已知 rubric 和分数，输出匹配预期） | 拒绝创建 round |

### G1 — Subagent 派发前

适用于**所有 subagent 类型**（生成器、评分器、bug-hunt、clean）。

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G1.1 | 技能声明的所有输入文件路径存在且非空 | 拒绝派发，列出缺失文件 |
| G1.2 | 输入 JSON 文件语法合法（json.loads 通过） | 拒绝派发 |
| G1.3 | 输入 YAML 文件语法合法（yaml.safe_load 通过） | 拒绝派发 |
| G1.4 | 原地修改技能：原文件已备份（.bak 存在且内容一致） | 自动备份后继续 |
| G1.5 | 同一文件不被两个并行 subagent 同时修改 | 排队等待（见 3.1 文件锁规范） |
| G1.6 | 评分 subagent 未用于该文件的历史评分（防记忆偏差） | 拒绝派发，要求换 subagent |

### 文件锁规范（G1.5 实现）

```
锁文件: {target_file}.gate-lock
内容:   {"agent_id": "...", "timestamp": "...", "operation": "write"}
超时:   300 秒（5 分钟）后锁自动过期
死锁检测: 如果锁文件存在超过 300 秒且持有 agent 已不存在 → 自动清理
获取失败: 等待 5 秒后重试，最多 60 次（总共 5 分钟）
全部重试失败: 标记 subagent 失败，人工介入
```

### G2 — Subagent 返回后（写盘验证）

适用于**所有 subagent 类型**。报告类文件（bug-hunt 输出、clean 输出、评分报告）跳过 G2.6-G2.9（章节专项），但必须通过 G2.1-G2.5 和 G2.10-G2.12。

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G2.1 | 声明产出的每个文件路径存在 | 标记失败，进入重试队列 |
| G2.2 | 每个文件 > 0 bytes | 同上 |
| G2.3 | 每个文件 UTF-8 编码有效 | 同上 |
| G2.4 | JSON 文件语法合法 | 同上 |
| G2.5 | YAML frontmatter 语法合法、必填字段齐全 | 同上 |
| G2.6 | 章节文件：字数 ≥ chapter_word.default (floor=3000) | 自动触发 length-normalizing 重跑 |
| G2.7 | 章节文件：字数 ≤ ceiling (10000)，非重要章 ≤ 1.5×default | 标记需压缩 |
| G2.8 | 章节文件：PRE_WRITE_CHECK 块存在（匹配 `## PRE_WRITE_CHECK` 标题） | 标记失败 |
| G2.9 | 章节文件：POST_WRITE_SELF_CHECK 块存在（匹配 `## POST_WRITE_SELF_CHECK` 标题） | 标记失败 |
| G2.10 | 文件并非模板占位符：全文搜索"待填充"字符串。命中行数 / 文件总行数 > 10% → 判定为模板占位符（与 G7.5 使用统一标准） | 标记失败 |
| G2.11 | Truth 文件：旧条目未被删除或修改（逐行对比 .bak 文件） | 标记失败，恢复备份 |
| G2.12 | 文件内容完整：Markdown 文件以合法标题或段落结束（不以未闭合代码块或半个句子结尾）；JSON 文件以 `}` 或 `]` 结尾 | 标记失败 |

### 2.1 Subagent 重试与清理规范

```
最大重试次数: 3
重试策略: 指数退避，间隔 = 30s × (2^attempt)
重试方式: 每次重试使用新的 subagent（不同 agent_id），清空前次 subagent 的上下文
部分产出清理: 重试前删除上次尝试产出的所有文件（基于 subagent 返回的声明产出列表）
耗尽重试: 标记为 DEAD，写入 progress.json 的 gate_blockers，等待人工介入
           后续依赖此技能的所有 Phase/Pipeline 自动阻塞
```

### G3 — 每次评分前（依赖检查 + 隔离验证）

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G3.1 | 根据 deps.json 中定义的前置技能列表，所有前置评分报告存在 | 拒绝评分，返回缺失列表 |
| G3.2 | 前置技能分数 ≥ 接受阈值 | 拒绝评分，返回不达标列表 |
| G3.3 | 被评文件已通过 G2 全套检查 | 拒绝评分，返回 G2 失败项 |
| G3.4 | 评分 subagent 的 agent_id ≠ 生成 subagent 的 agent_id。agent_id 由 round-exec.sh 在 subagent 派发时生成并记录到 progress.json 的 `agent_trace` 字段 | 拒绝评分 |
| G3.5 | 评分 subagent 的 agent_id 不存在于该文件的历史评分记录中（记录位置：progress.json `scoring_history`）。注：此检查在派发时由 G1.6 优先执行，G3.5 为防御性二次检查 | 拒绝评分 |

### G_TRANSITION — Phase 切换 Gate（新）

在以下时间点触发：generative→bug-hunt、bug-hunt→clean、clean→T2、T2→T3。

| # | 检查项 | 失败行为 |
|---|--------|---------|
| GT.1 | 当前 phase 的 progress.json `remaining_*` 队列为空（所有技能已派发） | 拒绝进入下一 phase |
| GT.2 | 当前 phase 所有技能的 status = DONE 或 DEAD | 列出未完成技能 → 拒绝 |
| GT.3 | 无 gate_blockers 条目处于 FAIL 状态且未 bypass | 列出阻塞项 → 拒绝 |
| GT.4 | 当前 phase 所有产出文件通过 G2 检查（批量模式） | 列出失败文件 → 拒绝 |
| GT.5 | 下一 phase 所需的所有输入文件存在（根据 deps.json） | 列出缺失 → 拒绝 |

### G_DISPATCH — 派发完整性 Gate（新）

在当前 phase 的派发循环结束时触发（Agent 声明"本 phase 派发完毕"后）。

| # | 检查项 | 失败行为 |
|---|--------|---------|
| GD.1 | `set(progress.completed_skill_names) == set(framework_skills_for_current_test_cycle_phase)`（framework_skills_for_current_test_cycle_phase = skills/ 目录下所有技能名）。当前 test_cycle_phase 为 "generative" 时检查是否 59 个技能全部派发过 | 列出未派发技能 → 拒绝 test_cycle_phase 完成声明 |
| GD.2 | 每个 completed_skill 的 progress.json status ≠ PENDING | 列出 PENDING 技能 → 拒绝 |
| GD.3 | 每个 DEAD 状态的技能有人工 bypass 记录或仍在 gate_blockers 中 | 无记录的 DEAD → 拒绝 |

### G_RECONCILE — 中间一致性对账（新）

每 5 个 subagent 完成后自动触发，以及每次 Phase 切换前触发。

| # | 检查项 | 失败行为 |
|---|--------|---------|
| GR.1 | progress.json 中 status=DONE 的技能 → 对应的 t1-reports/ 文件存在 | 标记 orphan_report → 需修复 |
| GR.2 | t1-reports/ 中存在但 progress.json 中 status≠DONE 的报告 → 标记 stale_tracker → 需修复 |
| GR.3 | progress.json 中 status=DONE 的技能 → 对应的 skill-traces/ 文件存在 | 标记 missing_trace → 需修复 |
| GR.4 | 文件系统中存在但不在该技能 SKILL.md 数据契约 `Writes`+`Updates` 列表中的文件 → 标记 orphan_file → 警告。检查来源：从每个已 DONE 技能的数据契约段提取预期产出路径列表，与文件系统实际文件做 diff |

### G4 — T1 技能专项 Gate

#### 生成类技能专项检查

每个检查分为两个层级：**脚本代理检查**（validate-gate.py 运行，不需要 LLM）和 **完整检查**（评分 subagent 运行，包含语义判断）。

**worldbuilding:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | novel.json 存在、JSON 合法、含 title/genre/language/target_words 字段且非空 |
| 脚本 | genre-config.json 存在、JSON 合法 |
| 脚本 | story_bible.md 存在、含 4 个 `## ` 二级标题、条目标记密度 < 5%（`- ` 或 `* ` 或数字列表行数 / 总行数） |
| 脚本 | rules.md 存在、规则条目数 1-10（按 `## 规则` 标题计数）、每条规则含"可测试标准"子标题 |
| 脚本 | locations.md 存在、地点条目数 3-5（按 `## 地点` 标题计数） |
| 脚本 | truth/ 下 4 个模板文件存在、frontmatter 含 type/category/status 字段 |
| 完整 | story_bible.md 4 段为叙事散文（非条目） |
| 完整 | rules.md 每条规则的可测试标准实际可操作 |
| 完整 | locations.md 地点描述有氛围和空间感 |

**character-design:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | protagonist.md frontmatter 含全部必填字段且非空 |
| 脚本 | voice_profile.speech_patterns 为数组且 length ≥ 2 |
| 脚本 | voice_profile.catchphrases 为数组且 length ≥ 1 |
| 脚本 | voice_profile.avoid_patterns 为数组且 length ≥ 1 |
| 脚本 | relationships.md 存在、含关系矩阵表（`|` 分隔的表格行 ≥ 3） |
| 完整 | 角色弧线描述连贯 |
| 完整 | voice_profile 使角色对话可区分 |

**story-architecture:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | story_frame.md frontmatter 含 surface_conflict/personal_conflict/deep_conflict 三个字段且非空 |
| 脚本 | volume_map.md 含 ≥1 个 `## 第.X卷` 标题、每个卷含 `**Objective**` 和 `**Key Results**` 标题 |
| 完整 | 三层冲突相互关联 |
| 完整 | OKR 可映射到具体章节 |

**power-system:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | power_system.md 含等级表（`|` 表格行 ≥ 5） |
| 脚本 | 含 `## 进阶规则` 标题 |
| 脚本 | 含 `## 能力边界` 标题 |
| 脚本 | 含 `## 代价机制` 标题 |
| 脚本 | 含 `## 力量天花板` 标题 |
| 完整 | 等级间差距为质变非量变 |
| 完整 | 代价机制具体可衡量 |

**faction-builder:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | factions.md 含 ≥2 个 `## 势力` 标题 |
| 脚本 | 每个势力含 `### 层级结构` 标题 |
| 脚本 | 每个势力含 `### 内部矛盾` 标题 |
| 脚本 | 每个势力含 `### 跨势力关系` 标题 |
| 脚本 | 每个势力含 `### 利益驱动行为` 标题 |
| 完整 | 内部矛盾具体非空泛 |
| 完整 | 跨势力关系有历史事件支撑 |

**location-builder:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | 每个地点含 `### 布局描述` 标题且内容 ≥ 200 字 |
| 脚本 | 每个地点含 `### 氛围锚点` 标题且内容 ≥ 150 字 |
| 脚本 | 每个地点含 `### 功能事件` 标题 |
| 完整 | 布局描述让读者能在脑中"走一遍" |
| 完整 | 氛围锚点有主导感官和时间感 |

**relationship-map:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | 含 ≥3 个 `## 关系对` 标题 |
| 脚本 | 每个关系对含 `**利益根基**` 字段且非空 |
| 脚本 | 每个关系对含 `**信息边界**` 字段且为 SYMMETRIC/ASYMMETRIC/ISOLATED/MUTUAL_SECRET 之一 |
| 脚本 | 每个关系对含 `**演化轨迹**` 字段 |
| 完整 | 利益根基可追溯 |
| 完整 | 信息不对称有戏剧利用价值 |

**pacing-design:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | rhythm_principles.md 含 `## 四拍循环` 标题 |
| 脚本 | 含 `## 三线比例` 标题且表格含 QUEST/FIRE/CONSTELLATION 三行 |
| 脚本 | 含 `## 场景类型序列` 标题且表格行 ≥ 6 |
| 脚本 | 含 `## 单调性检测规则` 标题 |
| 完整 | 四拍占比合理（10-40%） |
| 完整 | 三线比例与题材匹配 |

**plot-thread-weaver:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | thread_map.md 含 `## A 长线` 标题 |
| 脚本 | 含 `## B 中线` 标题 |
| 脚本 | 含 `## 章节线索推进表`（`|` 表格） |
| 脚本 | 含 `## 空白检测` 标题 |
| 完整 | A 线 max_gap 不超限 |
| 完整 | C 线有始有终 |

**volume-outlining:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | volume_map.md 含当前卷的 `**Objective**` 且可二元判断 |
| 脚本 | 含 `### Key Results` 且 3-5 个 KR |
| 脚本 | 含 `### 卷内张力曲线` |
| 脚本 | 含 `### 跨卷桥接` 且 ≥1 个实体钩子 |
| 完整 | 张力曲线有起有伏 |
| 完整 | 跨卷钩子能驱动下卷开场 |

**chapter-planning:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | chapter-N-plan.md 含 8 个 `## N.` 编号标题（1-8） |
| 脚本 | 第 1-3 章（N≤3）：第 1 段含"三面墙"或等价世界观建立描述（ch1）、第 2 段含对手建立（ch2）、第 3 段含小高潮/大主线钩子（ch3）。第 4 章起（N>3）：黄金三章约束不适用，跳过此检查 |
| 脚本 | 所有章节：第 4 段含 `### 关键抉择过三连问` |
| 脚本 | 所有章节：第 5 段含 hook 账（open/advance/resolve/defer 四种操作名至少出现一种） |
| 完整 | 章尾改变具体可验证 |
| 完整 | "不要做"列表可操作 |

**chapter-drafting:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | PRE_WRITE_CHECK 块存在（匹配 `## PRE_WRITE_CHECK` 标题） |
| 脚本 | POST_WRITE_SELF_CHECK 块存在（匹配 `## POST_WRITE_SELF_CHECK` 标题） |
| 脚本 | 转折词(然/不过/此时/突然/终于/于是)总出现次数 / 总字数 ≤ 1/3000 |
| 脚本 | 疲劳词命中次数 ≤ 3（从 genre-config.json 的 fatigue_words 列表逐词匹配） |
| 脚本 | 元叙事句式为 0：grep "让人感悟\|引人深思\|由此可见\|综上所述\|值得注意的是\|不禁感慨\|不由得想到" |
| 脚本 | 字数 ≥ floor(3000) |
| 完整 | Show-don't-tell 比例 > 60%（评分 subagent 估算） |
| 完整 | 角色对话匹配 voice_profile |

**foreshadowing-plant:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | pending_hooks.md YAML frontmatter 的 hooks 数组中每条新 hook 含 type/dimension/subtlety/cultivation_interval/max_distance/escalation_curve/depends_on |
| 脚本 | depends_on 不为 null（空为 []） |
| 脚本 | 本章 plant+reinforce+trigger+resolve 合计 ≤ 8 |
| 脚本 | SMOKESCREEN 类 hook 的 notes 字段 ≥ 50 字符且含条件关键词（如果/若/when/if/则/then） |
| 完整 | 种植位置选择了合适的场景类型 |
| 完整 | 微妙度与 hook 类型匹配 |

**context-composing:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | context/chapter-N-context.md 含 P1-P7 标签 |
| 脚本 | P1(章节任务)非空 |
| 脚本 | P2(近章摘要)非空 |
| 完整 | Hook 债务简报的紧迫度计算正确 |
| 完整 | 结尾方式检查覆盖最近章节 |

**state-settling:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | current_state.md 含 `## 位置` 标题且含本章章节号引用 |
| 脚本 | character_matrix.md 含本章新出场角色条目（逐章 diff） |
| 脚本 | chapter_summaries.md 末尾含本章摘要块（匹配 `## 第N章`） |
| 脚本 | emotional_arcs.md 含 `### 第N章 情绪轨迹` 标题 |
| 完整 | 提取仅基于正文明确描述（非推论） |
| 完整 | 情绪轨迹与实际章节内容一致 |

**style-polishing:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | `## 润色说明` 块存在 |
| 脚本 | 润色后字数 / 润色前字数 ∈ [0.85, 1.15] |
| 脚本 | 润色说明中每条修改含位置标记（段号或行引用） |
| 完整 | 润色未改变情节/角色行为 |
| 完整 | 未引入新 AI 味 |

**anti-detect:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | `## 改写报告` 块存在 |
| 脚本 | 改写报告含应用手法列表 |
| 完整 | 改写为靶向非笼统 |
| 完整 | 未错杀好句 |

**length-normalizing:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | 归一化后字数 ≥ floor(3000) 且 ≤ ceiling(10000)，或 25% 底线 REJECT 已触发且记录在归一化报告中 |
| 脚本 | 归一化报告含原始字数/目标区间/归一化后字数/变化百分比 |
| 完整 | 扩写为深化非灌水 |
| 完整 | 压缩未丢失信息 |

**genre-config:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | genre-config.json 存在、JSON 合法、含 fatigue_words/audit_dimensions/pacing_rules/chapter_word 字段 |
| 脚本 | chapter_word.default ≥ 1000（合理的字数下限） |
| 脚本 | fatigue_words 为数组 |
| 脚本 | audit_dimensions 为数组且 ≥ 5 个维度 |
| 完整 | 疲劳词数量 ≤ 50 且有替换建议 |
| 完整 | 审计维度选择性启用非全开 |

**foreshadowing-track:**

| 层级 | 检查项 |
|------|--------|
| 脚本 | pending_hooks.md 中 ≥1 条 hook 的 state 从 PLANTED 变更为 RELEVANT/PAYING_OFF/RESOLVED（或 last_reinforced 更新） |
| 脚本 | 每条 track 操作有章节号引用 |
| 脚本 | 核心 hook（core_hook=true）的沉默章数未超过 max_gap |
| 完整 | 紧迫 hook 获得了 advance/resolve 操作 |
| 完整 | 状态转换逻辑符合 escalation_curve 定义 |

#### Bug-hunt 类专项检查

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G4.b1 | 产出报告命中场景声明的 planted defect。匹配算法：(a) 文件路径精确匹配，(b) defect 描述提取 3 个关键词（名词和动词），报告 finding 中至少包含其中 2 个（中文子串匹配），(c) severity 标签与场景声明一致 | Kill switch → 总分 0 |
| G4.b2 | 未报告场景中没有的缺陷（零误报：报告中的 finding 数 ≤ 场景声明的 planted defect 数） | 每次误报 -20 分 |
| G4.b3 | 每个 finding 标注 severity（error/warning）和 evidence location（文件:段落引用）。统计通过率：有完整标注的 finding 数 / 总 finding 数，按比例给分 | 通过率 < 100% → 按比例扣分（每个缺失标注的 finding 扣 10 分，直至该维度 0 分） |

#### Clean 类专项检查

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G4.c1 | 报告 issues 数量 = 0 | 任何 finding → Kill switch，总分 0 |
| G4.c2 | 报告包含"已检查 X 维度，全部通过"摘要（匹配该模式） | 缺失 → 不完整扣分 |

#### G4 完整检查校准规范

所有"完整"层级的检查由评分 subagent 执行（LLM 需要语义理解）。为保证不同 subagent 之间评分一致性：

1. **评分尺度**：每个完整检查给 0-100 分。90+ = 符合标准，75-89 = 可接受但有改进空间，60-74 = 勉强通过，0-59 = 未通过。
2. **证据要求**：评分 subagent 必须引用产出文件中的具体段落作为评分依据。不得给"整体感觉"式的评分。
3. **校准锚点**：每个完整检查附带一个 PASS 示例和一个 FAIL 示例，存储在 `tests/tiers/t1-skill/<skill>/rubric.md` 对应维度的 `anchor_pass` 和 `anchor_fail` 字段中。格式：
   ```markdown
   | 3 | Internal consistency | 15% | Zero contradictions within world rules |
   ```
   扩展为：
   ```markdown
   | 3 | Internal consistency | 15% | Zero contradictions within world rules |
   
   **Anchor PASS**: "规则一和规则四互补：灵能守恒保证能量不灭，位面通道流速比描述的是时空属性——两者分别约束能量和时空，互不冲突。"
   
   **Anchor FAIL**: "规则一说灵能不能凭空产生，但规则四描述的角色从通道中'吸收灵能'违反守恒——吸收意味着灵能来自外部，但规则一要求总量不变，这里未说明来源。"
   ```
   评分 subagent 必须阅读锚点并据此校准评分尺度。
4. **分歧处理**：如果同一文件的两次独立评分（不同评分 subagent）分差 > 15 分，触发第三次评分（仲裁评分）。取三个分数中差值最小的两个的平均值。如果三分数间距相等（如 70, 80, 90），取中位数（80）。如果三分数完全相同，直接采用。

#### 报告和追踪文件命名规范

- **t1-reports/**：`<skill-name>-<test_type>.json`。例：`shenbi-worldbuilding-generative.json`
- **skill-traces/**：`<skill-name>-<test_type>.md`。例：`shenbi-worldbuilding-generative.md`
- G3.1、GR.1-GR.3、G7.2、G7.3 使用此命名规范查找对应文件

#### SKILL.md 数据契约解析（G5.2 使用）

G5.2 的 handoff 检查需要解析每个 SKILL.md 的数据契约段。每个技能文件中的 `## 数据契约` 段必须遵循以下格式（脚本可解析）：

```markdown
## 数据契约

- **Reads:** `path/to/file1.md`, `path/to/file2.md`
- **Writes:** `path/to/output1.md`
- **Updates:** `path/to/output2.md`
```

G5.2 实现：解析技能 N+1 的 `Reads` 列表 → 验证每个路径（展开通配符后）存在于技能 N 的 `Writes` + `Updates` 列表中。

### G5 — T2 Phase 专项 Gate

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G5.1 | Phase 链上每个技能的 T1 分数 ≥ 阈值（从 deps.json 读取该 phase 的 prerequisite 列表，逐一检查） | 拒绝 Phase 评分 |
| G5.2 | 链上技能 N 的声明输出文件 = 技能 N+1 的声明输入文件（handoff 完整性：对比两个 SKILL.md 的数据契约段） | 列出缺失 → handoff 断裂 |
| G5.3 | Cross-skill 一致性：技能 B 产出的 character 文件中引用的角色名出现在技能 A 的 character 输出中 | 每个孤儿引用 → 扣分 |
| G5.4 | Cross-skill 一致性：规则/地点引用可在上游输出中找到原始定义（grep 角色名/地名/规则 ID） | 每个孤儿引用 → 扣分 |
| G5.5 | Phase 预期输出文件完整存在（根据该 phase 的 deps.json 定义） | 缺失文件 → 扣分 |
| G5.6 | Phase 内无回归：每个技能在 T2 中产出的文件通过 G4 对应技能的脚本层级检查（不是完整评分，而是脚本可验证的结构性检查） | 任何失败 → Kill switch |

### G6 — T3 Pipeline 专项 Gate

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G6.1 | 实际生成章节数 ≥ ceil(expected_chapters × 50%) | 拒绝 Pipeline 评分 |
| G6.2 | 章节文件序列无断号（ch1→ch2→ch3 连续，按 `chapters/chapter-N.md` 文件名中的数字排序） | 缺失章 → 标记 gap |
| G6.3 | 每一章通过 G2 全套 + G4 chapter-drafting 脚本层级检查 | 失败章列表返回 |
| G6.4 | P0 级 hook（core_hook=true）：(当前章节 - last_reinforced) ≤ 3 | 沉默 hook → 扣分 |
| G6.5 | 当前章节 - plant_chapter > max_distance 的 hook 数 = 0 | 每个过期 hook → 扣分 |
| G6.6 | character_matrix 中标记"状态: 死亡"的角色名不出现在后续章节正文中（grep 排除 character_matrix 自身引用） | 幽灵角色 → Kill switch |
| G6.7 | 章节中引用的每个角色名可在 character_matrix 中找到（提取章节正文中所有 2-4 字中文人名模式——连续中文字符不含标点、非停用词——与 character_matrix.metadata.characters 中记录的角色名列表做精确匹配 + 子串匹配。匹配失败者为孤儿引用） | 孤儿引用 → 扣分 |
| G6.8 | 章节中引用的每个地点名可在 locations.md 中找到 | 孤儿引用 → 扣分 |
| G6.9 | chapter_summaries.md 含全部已完成章节摘要（计数 `## 第N章` 标题） | 缺失 → 扣分 |
| G6.10 | current_state.md 的 `updated` frontmatter 日期 ≥ 最新章节文件的修改日期 | 状态滞后 → 扣分 |
| G6.11 | emotional_arcs.md 含全部已完成章节的情绪轨迹（计数 `### 第N章 情绪轨迹` 标题） | 缺失 → 扣分 |
| G6.12 | 无平台违规内容（敏感词列表命中检查） | Kill switch → 总分 0 |

### G7 — 轮次关闭

| # | 检查项 | 失败行为 |
|---|--------|---------|
| G7.1 | summary.json 中每个 t1_scores key ∈ skills/ 目录名（逐项 diff） | 标记 round 无效 |
| G7.2 | summary.json 中每个技能有对应 skill-traces/ 文件 | 标记缺失 |
| G7.3 | summary.json 中每个技能有对应 t1-reports/ 文件 | 标记缺失 |
| G7.4 | novel-output/ 含预期文件（根据 deps.json `expected_outputs` 的 glob 模式逐一检查）。通配符 `*` 匹配规则：`chapter-*.md` 要求至少匹配 expected_chapters 个文件（缺失一章即失败）；`major/*.md` 要求匹配 ≥1 个文件；`chapter-*-plan.md` 要求匹配章节数等于实际章节数。精确路径（无通配符）直接检查文件存在 | 标记缺失 |
| G7.5 | 无文件仍是模板占位符（全文 grep "待填充"，命中行数 < 文件总行数的 10%） | 标记未完成 |
| G7.6 | 所有 truth 文件 frontmatter status ≠ "pending" | 标记未完成 |
| G7.7 | CHANGELOG.md 已追加本轮条目 | 自动追加 |
| G7.8 | 本轮无 FAIL 状态 Gate 悬而未决（progress.json gate_blockers 为空） | 标记 round 未完成 |

## 4. 工具改造

### 4.1 scoring.py

改造为内嵌依赖检查：

```python
# 新增 --tier 和 --phase 参数
# scoring.py --tier T2 --phase planning <rubric> <scores>
#   → 第一步：读取 deps.json，检查所有 T1 评分报告存在
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
#   → 运行 G2 + G4 chapter-drafting 全套检查（脚本层级）
#   → 输出 JSON 结果
# validate-gate.py G_TRANSITION generative bug-hunt
#   → 运行 GT.1-GT.5 检查
#   → 输出 JSON 结果
# validate-gate.py G_DISPATCH generative
#   → 运行 GD.1-GD.3 检查
#   → 输出 JSON 结果
# validate-gate.py G_RECONCILE
#   → 运行 GR.1-GR.4 检查
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

# 创建 round 时生成一次性绕过令牌：
#   → 生成 3 个随机令牌（32 字符 hex），打印到终端（不写入 Agent 可访问的文件）
#   → 令牌记录在 round meta 中（仅哈希值），用于验证绕过授权

# 新增 --validate 模式增强：
#   → 运行 G7.1-G7.8
#   → 输出逐项 PASS/FAIL
```

### 4.4 agent_id 生成与追踪

```python
# round-exec.sh 在每次 subagent 派发时生成唯一 agent_id
# agent_id = f"{round_num}-{skill_name}-{test_type}-{uuid4().hex[:8]}"
# 记录到 progress.json:
#   "agent_trace": {
#     "generator": {"agent_id": "003-worldbuilding-generative-a1b2c3d4", "timestamp": "..."},
#     "scorer": null  // 待填充
#   }

# G3.4 检查: 评分 subagent 派发前，读取 progress.json 该技能的 agent_trace，
#           确认 scorer agent_id ≠ generator agent_id
# G3.5 检查: 评分 subagent 派发前，读取 progress.json 该技能的 scoring_history 数组，
#           确认当前 scorer agent_id 不在历史记录中
```

### 4.5 progress.json（新进度追踪文件）

```json
{
  "round": "003",
  "tier": "T1",
  "test_cycle_phase": "generative",
  "subagent_completion_count": 45,
  "completed_skill_names": ["shenbi-worldbuilding", "shenbi-character-design", "shenbi-story-architecture"],
  "skills": {
    "shenbi-worldbuilding": {
      "generative": {"status": "DONE", "score": 97.0, "gate": "PASS"},
      "bug-hunt": {"status": "PENDING"},
      "clean": {"status": "PENDING"},
      "agent_trace": {
        "generative_generator": "003-worldbuilding-generative-a1b2c3d4",
        "generative_scorer": "003-worldbuilding-scorer-e5f6g7h8"
      },
      "scoring_history": [
        {"scorer_id": "003-worldbuilding-scorer-e5f6g7h8", "timestamp": "2026-06-11T10:00:00Z", "score": 97.0}
      ],
      "remediation_attempts": {},
      "output_files": ["world/story_bible.md", "world/rules.md", "world/locations.md"]
    }
  },
  "remaining_generative": ["shenbi-review-character", "shenbi-review-continuity"],
  "remaining_bug_hunt": [],
  "remaining_clean": [],
  "gate_blockers": [],
  "total_framework_skills": 59
}
```

**术语约定**：本文档使用两套"阶段"术语，严格区分：
- **test_cycle_phase**（测试周期阶段）：generative → bug-hunt → clean → T2 → T3。存储在 progress.json 的 `test_cycle_phase` 字段。
- **skill_group**（技能组/Phase）：genesis / architecture / planning / drafting / audit / management 等。定义在 deps.json 中。

progress.json 中的 `completed_skill_names` 是已完成技能名的数组（供 GD.1 做 set 比较）。`subagent_completion_count` 是每次 subagent 成功返回的递增计数器（供 G_RECONCILE 触发和 G_DISPATCH 看门狗使用）。`output_files` 是每个技能产出的文件路径数组（供 GR.4 做 orphan 检测）。`remediation_attempts` 为 `{remediation_type: count}` 映射（如 `{"word_count_expand": 2}`），存储在每个技能的 entry 中，追踪 G2.6 等自动修复的重试次数。

**规则**：此文件由 `validate-gate.py` 和 `round-exec.sh` 写入。Agent 只读。

**并发安全**：progress.json 的写入必须使用原子操作（写入临时文件 + os.rename）。`round-exec.sh` 写入前需获取 `progress.json.lock` 文件锁（与 G1.5 使用相同的文件锁协议，参见 Section 3.1）。同一时刻只有一个写入者持有锁。

### 4.6 自动化触发机制

**G_RECONCILE 触发**：`round-exec.sh` 在 progress.json 中维护 `subagent_completion_count` 计数器。每次 subagent 返回并通过 G2 后递增。当 `counter % 5 == 0` 时，自动调用 `validate-gate.py G_RECONCILE`。不依赖 Agent 记住触发。

**G_DISPATCH 触发**：Agent 声明 phase 完成后，`round-exec.sh` 调用 `validate-gate.py G_DISPATCH <phase>`。额外保护：如果 `subagent_completion_count` 停止增长超过 10 分钟（且 remaining 队列非空），`round-exec.sh` 的看门狗进程打印警告到终端，提醒人工介入。

**G_TRANSITION 触发**：Agent 声明 phase 切换意向后，`round-exec.sh` 调用 `validate-gate.py G_TRANSITION <from_phase> <to_phase>`。Gate 不通过则拒绝切换。

**G2.6 自动重跑机制**：当 G2.6（字数 < floor）失败时，`round-exec.sh` 自动执行：
1. 调用 `validate-gate.py G1 length-normalizing` 确保输入就绪
2. 派发新的 length-normalizing subagent（生成器角色，目标 = floor × 1.2）
3. subagent 返回后运行 G2 检查
4. 如果仍 < floor → 重试（最多 2 次，总共 3 次包括原始）
5. 3 次后仍失败 → 标记 DEAD
6. 重跑次数记录在 progress.json 的 `remediation_attempts` 字段，防无限循环

### 4.7 外部数据源

**敏感词列表**：位置 `tests/fixtures/sensitive_words.txt`。每行一个敏感词（支持正则表达式）。由项目维护者手动维护。G6.12 读取此文件进行全文章节扫描。

**G6.12 文件缺失行为**：如果 `sensitive_words.txt` 在 G6.12 执行时不存在 → 该检查标记为 SKIP，但 G6.12 的 Kill switch 属性不变——因为敏感词检测是非可绕过安全 Gate，SKIP 意味着"本轮无法验证平台安全性"，round 状态标记为 `INCOMPLETE (G6.12 skipped — sensitive_words.txt missing)`。此时 round 不能标记为正式通过，即使其他所有 Gate 都 PASS。

**绕过令牌哈希存储**：位置 `tests/rounds/round-NNN/.token-hashes.json`。此文件由 `round-exec.sh` 在 round 创建时写入，由 `validate-gate.py` 在验证绕过时读取。Agent 不可访问（文件权限 600，owner 为运行 round-exec.sh 的用户）。格式：
```json
{
  "tokens": [
    {"hash": "sha256_of_token_1", "spent": false},
    {"hash": "sha256_of_token_2", "spent": false},
    {"hash": "sha256_of_token_3", "spent": false}
  ]
}
```

**安全模型**：令牌保护基于信任模型——Agent 进程与 round-exec.sh 在同一用户下运行，文件权限（600）提供的是约定性保护而非强制安全边界。Agent 理论上可以读取 `.token-hashes.json`（同一用户），但无法从哈希逆推出明文令牌（SHA-256 单向性）。真正的安全依赖：明文令牌仅出现在人类终端输出中。如果 Agent 能从终端历史中访问令牌明文（例如读取 shell history），则令牌机制失效。这在此设计中是可接受的风险——绕过系统的目的是防止 Agent 无意识地跳过检查，而非防御恶意 Agent。

## 5. 紧急绕过条款

### 5.1 令牌机制

绕过非安全 Gate 需要人工授权的加密令牌。

**令牌生成**：`round-exec.sh` 在创建 round 时生成 3 个一次性令牌（32 字符 hex），打印到终端。

```
=== Round 003 Override Tokens (SAVE THESE) ===
Token 1: a7f3c9e1b2d4f6a8c0e2d4f6a8b0c2d4
Token 2: f1e3d5c7b9a1f3e5d7c9b1a3f5e7d9c1
Token 3: c4d6e8f0a2b4c6d8e0f2a4b6c8d0e2f4
=== Store securely. Each token is SINGLE-USE. ===
```

**使用方式**：用户在 prompt 中写 `OVERRIDE <token> <gate_id> <reason>`。`validate-gate.py` 验证令牌哈希匹配且未使用过。

**令牌记录**：仅哈希值存储在 `tests/rounds/round-NNN/.token-hashes.json` 中（参见 Section 4.7）。明文令牌不出现在 Agent 可访问的任何文件中。

### 5.2 不可绕过的 Gate

以下 Gate 永远不可绕过（即使有令牌）：
- G6.12（平台违规内容检测）
- G4.b1 bug-hunt Kill switch（missed planted defect）
- G4.c1 clean Kill switch（false positive）
- G6.6 幽灵角色 Kill switch

### 5.3 绕过限制

- 每轮最多 3 次绕过（对应 3 个令牌）
- 每个令牌单次使用，使用后立即标记为 spent
- 绕过仅对当次评分有效，不延续到后续 Gate
- 绕过记录写入 `tests/rounds/round-NNN/overrides.json`（由 `validate-gate.py` 写入）
- 绕过结果标记为 `PASS (override)`，不计入正式通过统计

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
