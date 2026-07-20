# 角色档案系统完整性修复 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** Spec CN1（主角消失）、Spec CN3（Truth 文件覆盖）
> **目的:** 修复 `shenbi-character-design` 仅产出主角档案的缺陷——`characters/major/*.md` 和 `characters/minor/*.md` 从未被创建，6+ 个有名有姓的配角无独立档案。同时引入历史原型驱动的人物设计方法论，使角色形象更鲜活。

---

## 1. 背景

### 1.1 现状

```
characters/
├── protagonist.md          ✅ 7,976B — 仅林烽
├── relationships.md        ✅ 28,340B — 6对关系
├── major/                  ❌ 不存在
└── minor/                  ❌ 不存在
```

SKILL.md 契约（`skills/shenbi-character-design/SKILL.md`）明确要求：

```yaml
writes:
  - characters/protagonist.md
  - characters/major/*.md       # 从未创建
  - characters/minor/*.md       # 从未创建
  - characters/relationships.md
```

### 1.2 影响

| 角色 | 在 plans 中出现 | relationships.md 中 | 独立档案 | 影响 |
|------|----------------|--------------------|---------|------|
| 陈卫民 | Ch10+（精神导师） | ✅ 详细弧线（Ch12-45） | ❌ | 无法独立查询角色动机、背景、人格 |
| 赵铁柱 | Ch12+（军事搭档） | ✅ 详细弧线（Ch12-47） | ❌ | 同上 |
| 楚云岚 | Ch25+ | ✅ 提及 | ❌ | 同上 |
| 科恩·怀特曼 | Ch30+ | ✅ 提及 | ❌ | 同上 |
| 钢山铁哉 | Ch30+ | ✅ 提及 | ❌ | 同上 |
| 中年女人 | Ch1-5 | ❌ | ❌ | 无任何记录 |
| 催收员 | Ch10+ | ❌ | ❌ | 无任何记录 |

- **下游 skill 无法按角色查询状态**（chapter-planning、state-settling 均需引用角色信息）
- **character_matrix.md 被参数代理替换**（Spec CN1）——失去唯一的结构化角色追踪
- **角色一致性无法保证**——无独立档案意味着每次 LLM 调用都重新"记忆"角色特征

### 1.3 根因

1. **G4 检查不对称**：`character-design` 的 G4 仅检查 `G4.protag.*`（主角结构），未验证 `characters/major/` 和 `characters/minor/` 目录是否非空
2. **LLM 输出截断**：`_write_parsed_outputs` 可能未正确处理通配符路径（`characters/major/*.md`）
3. **SKILL.md prompt 偏斜**：角色设计 prompt 过度聚焦主角（约占 80% token），配角仅被简要提及

---

## 2. 修复方案

### 2.1 上游修复 1：确保 major/minor 目录产出

#### 2.1.1 `_write_parsed_outputs` 支持通配符路径

`dispatch_helper.py:294-323` 当前按 `### FILE: path/to/file.md` 逐个文件解析。需增加：
- 识别输出路径中的通配符（`*`）
- 当 LLM 输出 `### FILE: characters/major/chen-weimin.md` 时，自动创建 `characters/major/` 目录

```python
# dispatch_helper.py:_write_parsed_outputs 修改
def _resolve_output_path(base_dir: Path, pattern: str, content: str) -> Path:
    """解析输出路径，支持通配符展开。"""
    if '*' in pattern:
        # 通配符路径：期望 LLM 在 FILE 标记中给出具体文件名
        # 暂不展开，由 LLM 输出的具体 FILE 标记驱动
        return None  # 信号：需从 FILE 标记动态确定
    return base_dir / pattern
```

#### 2.1.2 SKILL.md prompt 重构

在 `skills/shenbi-character-design/SKILL.md` 中将角色设计分为三个阶段：

```markdown
## 输出流程

### Phase 1: 主角深度画像 → characters/protagonist.md
### Phase 2: 主要配角画像 → characters/major/{character-slug}.md（每人一个文件）
### Phase 3: 次要角色登记 → characters/minor/{character-slug}.md（每人一个文件）
### Phase 4: 关系图谱 → characters/relationships.md

**铁律**：
- 每个被 chapter_outline.md 或 three_act.md 中明确命名的角色都必须有对应的 major/ 或 minor/ 档案
- major/ 角色：在 ≥3 章中出场且有独立人物弧线
- minor/ 角色：在 1-2 章中出场或仅作为功能性角色
```

#### 2.1.3 G4 检查增强

`g4/character_design.py` 增加：

```python
# G4.char.major_count: major/ 目录至少包含 N 个角色文件
major_dir = project_dir / 'characters' / 'major'
major_files = list(major_dir.glob('*.md')) if major_dir.exists() else []
if len(major_files) < 3:  # 至少 3 个主要配角
    issues.append(f"G4.char.major_count: only {len(major_files)} major characters (min 3)")

# G4.char.minor_count: minor/ 目录至少包含 M 个角色文件
minor_dir = project_dir / 'characters' / 'minor'
minor_files = list(minor_dir.glob('*.md')) if minor_dir.exists() else []
if len(minor_files) < 2:  # 至少 2 个次要角色
    issues.append(f"G4.char.minor_count: only {len(minor_files)} minor characters (min 2)")
```

---

### 2.2 上游修复 2：历史原型驱动的角色设计

#### 2.2.1 方法论

当前 `protagonist.md` 使用**抽象标签**描述角色（"利己主义"、"实用主义"、"幽默自嘲"）——这些标签缺乏具体的行为锚点。

**改进**：每个角色基于 1-2 个**具体历史人物原型**进行设计和改造，使角色具有可追溯的行为逻辑和鲜活质感。

#### 2.2.2 角色档案模板

每个 `characters/major/{slug}.md` 必须包含：

```markdown
---
name: {角色名}
role: {major|minor}
slug: {英文标识}
archetype_sources:  # 新增：历史原型
  - name: {历史人物名}
    period: {时代}
    traits_borrowed: [{借用的特质1}, {借用的特质2}]
    traits_discarded: [{不借用的特质}]
    adaptation_rationale: {为何选择该原型，如何改造以适应小说世界观}
---

# {角色名}

## 历史原型溯源
{详细说明从哪个/哪些历史人物身上提取了哪些特质，以及如何将其适配到梅德兰帝国的世界观中。

示例：
陈卫民的设计融合了两个历史原型：
1. **周恩来**（1930-40年代地下工作时期）——借用了"在敌对环境中建立秘密网络的能力"、"务实灵活的组织方法论"、"对年轻革命者的 mentorship 风格"。舍弃了"总理身份的外交职能"——在小说中转化为"灵火会精神导师"。
2. **陈云**（经济重建时期）——借用了"实事求是、不唯上不唯书只唯实"的方法论标签。舍弃了"计划经济管理"的具体技能。}

## 世界观适配
- 历史原型中的 {X} 在小说中转化为 {Y}
- 历史原型中的 {A} 在小说中转化为 {B}

## 基础信息
- 性别:
- 大致年龄:
- 社会阶层:（映射到梅德兰种姓制度）
- 首次出场章节:
- 核心冲突:

## 人格矩阵
| 维度 | 特质 | 历史原型依据 | 小说中的行为锚点 |
|------|------|------------|----------------|
| 核心价值观 | ... | 原型中的... | 例如 Ch12"十六字诀"让陈卫民震动 |
| 恐惧 | ... | 原型中的... | ... |
| 欲望 | ... | 原型中的... | ... |
| 说话风格 | ... | 原型中的... | 口头禅、句式特征 |
| 决策模式 | ... | 原型中的... | 面对道德困境时的典型选择 |

## 角色弧线
（与 protagonist.md 相同的弧线结构）

## 与其他角色的关系
（引用 relationships.md 中的条目，此处仅摘要）
```

#### 2.2.3 历史原型选取指南

在 SKILL.md prompt 中增加原型选取约束：

```markdown
### 历史原型选取原则

1. **优先选择具体历史人物而非抽象类型**：
   - ✅ "周恩来 1930年代上海地下工作" → 具体的组织方法论和行为细节
   - ❌ "智慧老人 archetype" → 空洞的类型标签

2. **每个角色至少 1 个、最多 2 个历史原型**：
   - 1 个原型提供核心行为逻辑
   - 第 2 个原型提供补充维度（可选）

3. **原型必须适配世界观**：
   - 历史人物的技能需转化为梅德兰世界的等价物
   - 历史人物的社会角色需映射到种姓制度
   - 历史人物的语言风格需转化为符合小说语境的表达

4. **借用与舍弃清单**：
   - 明确列出借用了哪些特质（≥ 3 项）
   - 明确列出舍弃了哪些特质（≥ 2 项）——角色不是历史人物的复制品
   - 解释 adaptation_rationale

5. **避免的原型**：
   - 过度使用的人物（如毛泽东、希特勒等）
   - 神话/虚构人物（没有可追溯的行为记录）
   - 仍然在世的公众人物
```

#### 2.2.4 示例：赵铁柱的历史原型驱动设计

```markdown
## 历史原型溯源

赵铁柱的设计融合了两个历史原型：

1. **许世友**（中国解放军上将）
   - 借用：粗犷豪迈的军事作风、对指挥官的个人忠诚、"刀子嘴豆腐心"的性格反差、少林武术底子（转为灵能近战技巧）
   - 舍弃：红军时期的具体战斗经历、对毛泽东个人的特殊关系
   - 转化：少林武术 → 灵能近战格斗术；红军指挥经验 → 梅德兰游击战经验

2. **曾国荃**（湘军将领）——补充维度
   - 借用："攻城不怕坚"的攻坚意志、与兄长（曾国藩）的关系模式
   - 舍弃：湘军的具体历史背景、晚清政治立场
   - 转化：与兄长的关系 → 与陈卫民的间接 mentor 关系（通过陈卫民的推荐而加入）

## 世界观适配
- 许世友的"少林武术"在梅德兰转化为：赵铁柱是少数几个天生拥有灵能近战天赋的底层矿工，这种天赋在种姓制度下被压制
- 曾国荃的"攻城意志"在小说中转化为：赵铁柱是所有重大战役中"最后一道防线"的指挥官——从不撤退
```

---

### 2.3 下游修复：character_matrix.md 恢复

Spec CN1 修复主角消失后，`character_matrix.md` 应从参数代理恢复为人类角色矩阵。

新增字段关联角色档案：

```markdown
| 角色 | slug | 当前状态 | 当前位置 | 当前情感 | 活跃关系 | 弧线阶段 | 最后更新章 |
|------|------|---------|---------|---------|---------|---------|-----------|
| 林烽 | lin-feng | 活跃 | ... | ... | 陈卫民(精神导师) | Stage 1→2 | Ch56 |
| 陈卫民 | chen-weimin | 已故(Ch45) | — | — | 林烽(继承者) | 完成 | Ch45 |
| 赵铁柱 | zhao-tiezhu | 活跃 | ... | ... | 林烽(搭档) | Stage 3 | Ch56 |
```

每章 state-settling 更新 `character_matrix.md` 时，引用角色档案中的 `slug` 字段。

---

## 3. 验证标准

### 3.1 角色档案完整性

1. Genesis 完成后 `characters/major/` 至少 3 个 `.md` 文件
2. Genesis 完成后 `characters/minor/` 至少 2 个 `.md` 文件
3. 每个 major 角色档案包含 `archetype_sources` 字段（至少 1 个历史原型）
4. 每个档案包含"借用与舍弃清单"

### 3.2 历史原型质量

5. 原型是具体历史人物（非抽象类型标签）
6. adaptation_rationale ≥ 100 字
7. 借用特质 ≥ 3 项，舍弃特质 ≥ 2 项

### 3.3 集成测试

8. 下游 skill（chapter-planning）可读取 `characters/major/{slug}.md` 获取角色特征
9. state-settling 更新 `character_matrix.md` 时使用 slug 引用
10. `just check` 全量通过

### 3.4 角色弧线追踪（新增）

11. 连续 10 章后 `protagonist.md` 的 `arc_log` 包含阶段性进展记录
12. 弧线阶段推进有明确的触发证据（引用章节行号）

---

## 4. 依赖

```
Spec CN1（主角消失修复）← character_matrix.md 恢复依赖此项
Spec CN3（Truth 追加模式）← character_matrix 增量更新依赖此项
  ↓
本 Spec
  ↓
shenbi-character-design SKILL.md 重写
shenbi-state-settling（character_matrix 更新逻辑）
shenbi-chapter-planning（角色信息消费）
```

---

## 5. 与现有 Spec 的关系

| Spec | 关系 |
|------|------|
| CN1（主角消失） | character_matrix.md 恢复是人类角色档案系统的前提 |
| CN3（Truth 覆盖） | character_matrix 需改为追加模式 |
| H1（JSON 格式） | 角色档案为 markdown，不受影响 |
| 本 Spec | 补齐角色档案系统 + 引入历史原型方法论 |
