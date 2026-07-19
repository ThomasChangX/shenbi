# 修复 Volume Map 未被 Chapter Loop 消费 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** Spec CN3（Truth 追加模式）、Spec C2（文风漂移）
> **目的:** 修复流水线最严重的架构缺陷——`volume_map.md` 作为 100 章 5 卷的完整蓝图，在 56 章生成过程中**完全未被消费**。所有 100 章与蓝图偏离，16/16 个关键情节点缺失，4/4 个跨卷桥接未激活。

---

## 1. 背景

### 1.1 发现

`outline/volume_map.md` 是一份 460 行的精密规划文档，包含：

| 层级 | 内容 | 状态 |
|------|------|------|
| L1: Volume | 5 卷，每卷 Objective + 章节范围 | 已规划 |
| L2: Key Result | 每卷 3-4 个 KR，每 KR 有 开篇/承接/转折/收官 节点 | 已规划 |
| L3: Chapter | 100 章每章的节点角色和具体内容描述 | 已规划 |
| L4: Tension | 每卷四段张力曲线 + 占比约束 | 已规划 |
| L5: Bridge | 16 个跨卷钩子（物品/事件/信息/人物）+ 预期激活章 | 已规划 |

但 pipeline 实际产出的 56 章：

| 度量 | 结果 |
|------|------|
| 与 volume_map 偏离的章节 | **100/100（100%）** |
| 关键情节点缺失 | **16/16（100%）** |
| 跨卷桥接未激活 | **4/4（100%）** |
| 角色按时登场 | **0/6**（陈卫民、赵铁柱、楚云岚、科恩、钢山铁哉、中年女人均未按计划登场） |

### 1.2 根因

```
volume_map.md 由 shenbi-volume-outlining 在 Genesis 生成
  ↓
chapter_loop.py: 无任何代码读取 volume_map
context_assemble.py: 无任何代码读取 volume_map
dispatch_helper.py: 无任何代码读取 volume_map
  ↓
shenbi-chapter-planning: SKILL.md 声明 reads volume_map
  但 prompt 构建时未将其注入上下文
  ↓
每章 LLM 调用看不到蓝图 → 自由发挥 → 偏离
```

**唯一引用**：`skills/shenbi-chapter-planning/SKILL.md` 的 `reads` 合约声明了 `outline/volume_map.md`——但这一声明**从未在代码层被执行**。`dispatch_helper.py` 的 `_build_skill_prompt` 或 `context_assemble.py` 的 `assemble_context` 均未读取 volume_map 并将其注入 prompt。

### 1.3 为什么这是最严重的缺陷

volume_map 不是"建议"——它是 Genesis 阶段最大的产出（由 4 个 skill 联合生成：volume-outlining + story-architecture + pacing-design + plot-thread-weaver）。花费了大量 token 生成了精密蓝图，然后**完全丢弃**。

这解释了：
- C2（文风崩塌）：LLM 失去了叙事方向，退化为参数枚举
- CN1（主角消失）：volume_map 明确规划了每章的人物登场和弧线推进，但 LLM 看不到
- CN2（钩子断裂）：16 个跨卷桥接有精确的激活章节，但无人追踪
- 整体叙事偏离：流水线从 Ch10 起就开始与蓝图分道扬镳

---

## 2. 上游修复

### 2.1 `context_assemble.py`：将 volume_map 注入上下文

`context_assemble.py:174-188`（Route C 固定规则）当前仅加载 `book_spine.md`、`audit_drift.md`、`style_profile.md`。需增加 volume_map 的当前卷上下文：

```python
# context_assemble.py: Route C 扩展

def _load_volume_context(project_dir: Path, chapter: int) -> str:
    """从 volume_map 提取当前章节所在的卷级上下文。

    返回：
    - 当前卷的 Objective
    - 当前 KR 的目标和节点
    - 当前章节在 volume_map 中的预期内容
    - 下一个跨卷桥接的预期激活章
    """
    volume_map = (project_dir / 'outline' / 'volume_map.md').read_text()

    # 确定当前卷
    current_volume = None
    for vol_name, (ch_start, ch_end) in [
        ('第一卷', (1, 15)), ('第二卷', (16, 35)),
        ('第三卷', (36, 55)), ('第四卷', (56, 75)), ('第五卷', (76, 100))
    ]:
        if ch_start <= chapter <= ch_end:
            current_volume = vol_name
            vol_range = (ch_start, ch_end)
            break

    if not current_volume:
        return ""

    # 提取当前卷的完整 section
    vol_section = extract_volume_section(volume_map, current_volume)

    # 提取当前章节的节点信息
    chapter_node = extract_chapter_node(volume_map, chapter)

    # 提取即将激活的跨卷桥接
    pending_bridges = extract_pending_bridges(volume_map, chapter)

    return f"""## 卷级蓝图（来自 volume_map.md）

### 当前卷目标
{vol_section['objective']}

### 本章在卷中的位置
- 节点角色：{chapter_node['role']}
- 预期内容：{chapter_node['desc']}

### 即将激活的跨卷桥接
{pending_bridges}

### 卷张力曲线
{vol_section['tension_curve']}
"""
```

### 2.2 `chapter_loop.py`：增加蓝图对齐检查

在 chapter drafting 完成后，新增 G4 级别的蓝图对齐验证：

```python
# chapter_loop.py: run_chapter_step 中，drafting G4 通过后

def _check_volume_map_alignment(project_dir, chapter, chapter_text):
    """验证章节内容是否与 volume_map 的预期对齐。

    非 HARD 门禁——仅 WARN。蓝图是指导性的，允许创造性偏离。
    """
    volume_map = (project_dir / 'outline' / 'volume_map.md').read_text()
    node = extract_chapter_node(volume_map, chapter)

    if not node:
        return []

    issues = []

    # 1. 关键术语存在性检查
    key_terms = extract_key_terms(node['desc'])
    missing_terms = [t for t in key_terms if t not in chapter_text]
    if len(missing_terms) > len(key_terms) * 0.7:
        issues.append(
            f"G4.vol.alignment: chapter {chapter} expected '{node['desc'][:60]}' "
            f"but {len(missing_terms)}/{len(key_terms)} key terms missing: {missing_terms[:5]}"
        )

    # 2. 人物登场检查
    expected_chars = extract_expected_characters(volume_map, chapter)
    for char_name in expected_chars:
        if char_name not in chapter_text:
            issues.append(
                f"G4.vol.character:{char_name}: expected debut/appearance in Ch{chapter} per volume_map"
            )

    return issues  # WARN 级别，不阻断
```

### 2.3 `dispatch_helper.py`：注入 volume_map 到 planning prompt

在 `_build_skill_prompt` 中，对 `shenbi-chapter-planning` 增加 volume_map 上下文注入：

```python
# dispatch_helper.py:_build_skill_prompt 中

if skill_name == 'shenbi-chapter-planning':
    chapter = extract_chapter_from_context(context)
    vol_context = _load_volume_context(project_dir, chapter)
    # 注入到 system prompt 的上下文部分
    system_prompt = system_prompt.replace(
        '{VOLUME_CONTEXT}',
        vol_context
    )
```

### 2.4 跨卷桥接追踪器

在 `truth/` 中新增 `bridge_tracker.md`，追踪 16 个跨卷桥接的状态：

```markdown
| Bridge ID | 内容 | 预期激活章 | 实际激活章 | 状态 |
|-----------|------|-----------|-----------|------|
| V1-B1 | 梵天铭文金属片 | Ch26 | - | PENDING |
| V1-B4 | 楚云岚登场 | Ch27 | - | PENDING |
```

由 `shenbi-foreshadowing-track` 每章更新——当章节内容包含桥接关键术语时标记为 ACTIVATED。

---

## 3. 下游影响

- `shenbi-chapter-planning` 的 prompt 将包含当前卷的 Objective 和章节节点信息
- Chapter drafting 将看到"本章在卷中的位置"作为上下文
- G4 新增 WARN 级别的蓝图对齐检查（非阻断，指导性）
- Bridge tracker 使跨卷钩子可追踪

---

### 2.5 混合 Planning：volume_map 驱动的确定性骨架 + LLM 润色

当前 chapter planning 完全由 LLM 从零生成 8 节计划——即使 87.5% 的内容可以从 volume_map 确定性推导。

**各节确定性程度分析：**

| Section | volume_map 可提供 | LLM 角色 | 预计 token 节省 |
|---------|-------------------|---------|----------------|
| 1. 当前任务 | ✅ 完全（节点角色+内容描述→翻译为任务） | 润色措辞 | -80% |
| 2. 读者此刻在等什么 | 🟡 部分（张力曲线→读者期望方向） | 结合前章实际 | -40% |
| 3. 该兑现的/暂不掀的 | ✅ 跨卷桥接（bridge_tracker） | 补充章内钩子 | -50% |
| 4. 日常/过渡承担什么任务 | ✅ 节点角色（开篇/承接/转折/收官→过渡类型） | 润色措辞 | -80% |
| 5. 关键抉择过三连问 | ❌ 不可推导 | **完全 LLM** | -0% |
| 6. 章尾必须发生的改变 | ✅ 基本（当前节点+下一章预期→改变方向） | 细化具体改变 | -60% |
| 7. 本章 hook 账 | ✅ 桥接（bridge_tracker+pending_hooks） | 填充操作细节 | -50% |
| 8. 不要做 | 🟡 部分（卷级约束从 volume 边界推断） | 章级禁忌 | -30% |
| **总计** | | | **~55%** |

**实现：确定性骨架生成器**

新增 `src/shenbi/pipeline/plan_skeleton.py`：

```python
def generate_plan_skeleton(project_dir: Path, chapter: int) -> str:
    """从 volume_map 确定性生成 chapter plan 的骨架。

    返回一个 8 节 markdown 模板，其中：
    - section 1, 4, 6, 7 已填充确定性内容
    - section 2, 3, 5, 8 保留占位符供 LLM 填充

    LLM 的 prompt 接收此骨架作为输入，只需：
    1. 填充占位符部分
    2. 润色确定性部分的措辞
    """
    vm = (project_dir / 'outline' / 'volume_map.md').read_text()
    node = extract_chapter_node(vm, chapter)
    vol_ctx = extract_volume_context(vm, chapter)
    bridges = extract_pending_bridges(vm, chapter)
    next_node = extract_chapter_node(vm, chapter + 1)

    return f"""## 1. 当前任务

> 确定性骨架（来自 volume_map.md）：
> 本章是 {vol_ctx['kr_name']} 的 **{node['role']}章**。
> 核心任务：{node['desc']}
> 卷目标：{vol_ctx['objective']}

[LLM: 将上述骨架翻译为具体的章节任务描述，2-4句话。保持卷目标在视野内。]

## 2. 读者此刻在等什么

[LLM: 基于以下信息推断读者期望：
- 本章在张力曲线中的位置：{vol_ctx['tension_phase']}
- 前一章节点角色：{_get_prev_node_role(vm, chapter)}
- 当前章节点角色：{node['role']}
请写出制造期待和延迟期待两部分。]

## 3. 该兑现的 / 暂不掀的

> 确定性骨架：跨卷桥接即将激活：
{bridges}

[LLM: 补充章内伏笔的兑现/延期决策。hook_deliverables 从 pending_hooks 中选取。]

## 4. 日常/过渡承担什么任务

> 确定性骨架：本章节点角色为 **{node['role']}**
> - 开篇章：建立新情境，引入新人物/新冲突
> - 承接章：深化已有冲突，推进人物关系
> - 转折章：制造不可逆改变，打破现状
> - 收官章：完成当前 KR，收束支线，设置下一 KR 钩子

[LLM: 基于节点角色写出具体的过渡任务。]

## 5. 关键抉择过三连问

[LLM: 创造性设计本章的核心道德/策略困境。此处完全由 LLM 自由生成。]

## 6. 章尾必须发生的改变

> 确定性骨架：
> - 当前章节点：{node['role']} — {node['desc']}
> - 下一章节点：{next_node['role']} — {next_node['desc']}
> - 从当前到下一章的必须改变方向：{_infer_change_direction(node, next_node)}

[LLM: 将改变方向细化为具体的、可验证的改变项。≥1 项。]

## 7. 本章 hook 账

> 确定性骨架（来自 bridge_tracker + volume_map 跨卷桥接）：
{bridges}

[LLM: 为每个桥接选择合适的操作（open/advance/resolve/defer），补充章内 hook。]

## 8. 不要做

> 确定性骨架（来自卷级约束）：
> - 本章不得跨越卷边界（卷{vol_ctx['vol_num']}：Ch{vol_ctx['ch_start']}-{vol_ctx['ch_end']}）
> - 本章不得引入卷外人物

[LLM: 补充章级禁忌——基于前章的疲劳词分析和 AI 陷阱模式。]
"""
```

**LLM 角色从"生成者"变为"润色者+创造性填充者"**——token 消耗减少 ~55%，且计划与蓝图的对齐率从 0% 提升至接近 100%。

---

## 4. 验证标准

1. `context_assemble.py` 的 Route C 输出包含当前卷的 Objective
2. `plan_skeleton.py` 为每章生成确定性骨架，LLM planning prompt 接收骨架而非从零开始
3. 混合 planning 的 token 消耗相比纯 LLM planning 减少 ≥ 40%
4. 连续 10 章运行中，与 volume_map 的关键术语匹配率 ≥ 80%（从当前 0% 提升）
5. Section 5（关键抉择）保持 LLM 完全创造性生成——不因骨架化而丧失创造性
6. Bridge tracker 在预期激活章附近更新状态
7. `just check` 全量通过

---

## 5. 依赖

```
Spec CN3（Truth 追加）← bridge_tracker 需要追加模式
  ↓
本 Spec
  ↓
shenbi-chapter-planning（prompt 消费 volume_map）
shenbi-chapter-drafting（上下文消费 volume_map）
shenbi-foreshadowing-track（bridge_tracker 更新）
```
