# 修复状态机 current_step 损坏 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** 无
> **目的:** 修复 Chapter 56 `current_step=""` 但 `step_index=9` 的状态不一致——确保 `_advance` 的所有退出路径正确设置 `current_step` 字段。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

`pipeline-state.json` 中 Chapter 56 的状态：

```json
"chapter_loop": {
    "current_chapter": 56,
    "current_step": "",        // 🔴 空字符串
    "step_index": 9
}
```

Chapter 56 的 `chapter_states`：
```json
"56": {
    "status": "pending",
    "steps_done": [
        "shenbi-intent-management",
        "shenbi-chapter-planning",
        "shenbi-foreshadowing-plant",
        "pipeline-context-assemble",
        "shenbi-context-composing",
        "shenbi-chapter-drafting",
        "shenbi-state-settling",
        "shenbi-foreshadowing-track",
        "shenbi-foreshadowing-recall"
    ]
}
```

**状态矛盾**：
- `step_index=9` 表示已完成 9 步
- `current_step=""` 表示当前没有执行中的步骤
- `status=pending` 表示章节未完成
- 但 9 步已完成 → 应该可以确定下一个 step 是什么

### 1.2 影响

`pipeline resume` 依赖 `current_step` 来决定从哪个步骤恢复。空字符串可能导致：
- 无法确定恢复点，跳过步骤
- 错误地从 step 0 重新开始
- 状态机进入未定义行为

---

## 2. 根因分析

### 2.1 `_advance` 的字段设置

`chapter_loop.py:489-563`（`_advance` 函数）：

```python
def _advance(state, project_dir, chapter_loop):
    # ...
    chapter_loop.step_index = step_idx + 1
    # 注意：没有显式设置 current_step
```

`_advance` **设置了 `step_index` 但没有设置 `current_step`**。`current_step` 可能在其他地方设置（如 `run_chapter_step` 开始处），但如果 pipeline 在步骤之间被终止，状态持久化时 `current_step` 可能为空。

### 2.2 ChapterLoopStateData 定义

`state.py:133-143`：
```python
class ChapterLoopStateData:
    current_chapter: int = 1
    current_step: str = ""       # 默认为空字符串
    step_index: int = 0
    chapter_states: dict = {}
    retry_counts: dict = {}
    modify_feedback: dict = {}
    retry_feedback: dict = {}
    soft_fail_trackers: dict = {}
```

`current_step` 的默认值本身就是空字符串——这解释了为什么"无当前步骤"时该字段为空，但 `step_index > 0` 时应该能推导出当前步骤。

### 2.3 修复原则

两个选择：
1. **每次状态变更时显式设置 `current_step`**（完整但改动大）
2. **在状态加载/保存时自愈：从 `step_index` 推导 `current_step`**（最小改动）

---

## 3. 修复方案

### 3.1 主要修复：自愈逻辑

在 `PipelineState` 的加载或保存路径增加自愈：

```python
# state.py 或 pipeline 持久化处
def _heal_current_step(state: PipelineState) -> None:
    """从 step_index 推导并修复 current_step。"""
    cl = state.chapter_loop
    if not cl.current_step and cl.step_index > 0:
        if cl.step_index < len(CHAPTER_STEPS):
            cl.current_step = CHAPTER_STEPS[cl.step_index].skill
        else:
            cl.current_step = "chapter_complete"
```

### 3.2 辅助修复：`_advance` 显式设置

在 `chapter_loop.py:489-563` 的 `_advance` 函数中，设置完 `step_index` 后同步设置 `current_step`：

```python
chapter_loop.step_index = step_idx + 1
# 同步设置 current_step
if chapter_loop.step_index < len(CHAPTER_STEPS):
    chapter_loop.current_step = CHAPTER_STEPS[chapter_loop.step_index].skill
else:
    chapter_loop.current_step = "chapter_complete"
```

### 3.3 防御层：状态加载时验证

在 pipeline resume 的初始化处增加状态一致性检查：

```python
def _validate_state_consistency(state: PipelineState) -> list[str]:
    """检查 pipeline state 的内部一致性。"""
    issues = []
    cl = state.chapter_loop

    if cl.step_index > 0 and not cl.current_step:
        issues.append(f"Chapter {cl.current_chapter}: step_index={cl.step_index} but current_step is empty")
        _heal_current_step(state)

    if cl.current_step == "chapter_complete" and cl.step_index < len(CHAPTER_STEPS):
        issues.append(f"Chapter {cl.current_chapter}: marked complete but step_index={cl.step_index} < {len(CHAPTER_STEPS)}")

    return issues
```

---

## 4. 验证标准

1. **单元测试**：`tests/unit/pipeline/test_state_machine.py`
   - 构造 `step_index=9, current_step=""` 的状态 → 自愈后 `current_step=CHAPTER_STEPS[9].skill`
   - `_advance` 后断言 `current_step` 非空
   - 完成所有步骤后 `current_step="chapter_complete"`

2. **回归检查**：`just check` 全量通过
3. **集成测试**：在测试 project 上模拟中断-恢复，确认状态一致

---

## 5. 依赖关系

```
无前置依赖（独立修复）
  ↓
对 Spec H4（staging 清理）有弱关联（都影响 resume 路径）
```
