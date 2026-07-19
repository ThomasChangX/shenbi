# Review Checklist 静态字段提取：消除 65% 跨章冗余 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec HN7（审查清单完全静态）
> **目的:** 修复 `shenbi-context-composing` 每章重新生成 7 个从不变化的静态字段的根因——提取为共享模板，仅按章生成 3 个动态字段。

---

## 1. 背景

### 1.1 发现

`context/review-checklist-N.json` 的 10 个字段中，**7 个在所有 56 章中值完全相同**：

| 字段 | 值 | 变化？ |
|------|-----|--------|
| `chapter` | 1-56 | ✅ 每章不同 |
| `transition_budget` | 5-11 | ✅ 有变化 |
| `ending_constraints` | 0-3 | ✅ 有变化 |
| `ai_blacklist` | 始终 14 项 | 🔴 永不变化 |
| `fatigue_warnings` | 始终相同 | 🔴 永不变化 |
| `voice_constraints` | 始终相同 | 🔴 永不变化 |
| `pov_mode` | 始终 `""` | 🔴 永不变化 |
| `hook_deliverables` | 始终 `0` | 🔴 永不变化 |
| `world_rules_brief` | 始终相同长文本 | 🔴 永不变化 |
| `sensitivity_flags` | 始终 `0` | 🔴 永不变化 |

每次 LLM dispatch 为 56 章中的每一章重新生成这 7 个静态字段——浪费 token 且引入不必要的格式漂移风险。

### 1.2 根因

`shenbi-context-composing` SKILL.md 要求每章输出完整 checklist JSON。但 7/10 字段的值来源于：
- `world_rules_brief`：来自 `world/rules.md`（Genesis 阶段固定）
- `ai_blacklist`：来自 `style/style_profile.md`（仅 Genesis 时更新）
- `fatigue_warnings`、`voice_constraints`、`pov_mode`：来自项目配置（运行期间不变）

这些字段在 chapter loop 运行期间**不可能改变**——但 LLM 每章都被要求重新输出它们。

---

## 2. 上游修复

### 2.1 分离静态模板与动态增量

**Step 1：创建静态模板文件**

`context/review-checklist-template.json`（Genesis 阶段生成一次）：

```json
{
  "ai_blacklist": [...],
  "fatigue_warnings": [...],
  "voice_constraints": {...},
  "pov_mode": "...",
  "world_rules_brief": "...",
  "sensitivity_flags": [...]
}
```

由 `shenbi-context-composing` 在 Genesis 阶段生成一次，之后仅当 style-learning 更新（每 12 章）或 genre-config 变更时重新生成。

**Step 2：每章仅生成动态字段**

`context/review-checklist-chapter-N.json`（chapter loop 中每章生成）：

```json
{
  "chapter": 5,
  "transition_budget": 6,
  "ending_constraints": 3,
  "hook_deliverables": ["MH-001", "MH-020"]
}
```

**Step 3：下游消费者合并**

```python
def get_checklist(project_dir, chapter):
    template = json.loads((project_dir / 'context' / 'review-checklist-template.json').read_text())
    delta = json.loads((project_dir / 'context' / f'review-checklist-chapter-{chapter}.json').read_text())
    return {**template, **delta}
```

### 2.2 `hook_deliverables` 从静态改为动态

当前 `hook_deliverables` 始终为 0——这是一个 bug（Spec HN7）。修复后，它应从 chapter plan 的 Section 7 hook ledger 中自动提取：

```python
def extract_hook_deliverables(plan_path):
    plan_text = plan_path.read_text()
    s7 = extract_section(plan_text, 7)
    # 提取 open/advance/resolve 操作
    return re.findall(r'MH-\d+.*?(open|advance|resolve)', s7)
```

### 2.3 `shenbi-context-composing` SKILL.md 更新

- 输出改为仅包含动态字段 + hook_deliverables
- 静态字段由 Genesis 阶段单独生成
- Prompt 中移除静态字段的输出要求

---

## 3. 下游影响

- 所有读取 `review-checklist-N.json` 的 skill（chapter-drafting 的 PRE_WRITE_CHECK 构建）需改为合并模板+增量
- `chapter_loop.py` 中 context assembly 步骤需加载合并后的 checklist

---

## 4. 验证标准

1. Genesis 后 `review-checklist-template.json` 存在且包含 6 个静态字段
2. 运行 5 章后——每章仅有 `review-checklist-chapter-N.json`（≤ 500 bytes）
3. `get_checklist(N)` 返回的合并结果与当前 `review-checklist-N.json` 等效
4. `hook_deliverables` 不再为 0（当 plan 中有活跃钩子时）
5. `just check` 全量通过

---

## 5. 依赖

```
Spec HN7（审查清单静态）← 共享诊断
Spec CN4（Style Learning 更新）← 触发模板重新生成
  ↓
本 Spec
  ↓
shenbi-chapter-drafting（checklist 消费者适配）
```
