# 恢复 progress 追踪 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** 无
> **目的:** 确保 `progress.json`（trace-derived view）在 chapter loop 期间被正确更新——当前 40 小时/56 章运行中完全未更新。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

`progress.json` 的最后修改时间停留在 Genesis 结束时（04:53:55），内容为：

```json
{
  "current_scorer_agent": "pipeline-g3-scorer-66b27075583e",
  "scoring_history": [
    {"agent": "pipeline-skill-generator", "g2_passed": true}
  ]
}
```

此后 40 小时、56 章的 chapter loop 未对 `progress.json` 做任何更新。

### 1.2 设计说明

`progress.json` 是 **trace-derived view**（`trace/materialize.py:31-101`）：从事件追踪（`MARK_DONE` 事件）重建。

问题在于 `_record_step_done`（`chapter_loop.py:443-451`）只更新内存中的 `PipelineState`，未发射 trace 事件：

```python
def _record_step_done(state, chapter, skill_name):
    ch_state = state.chapter_loop.chapter_states.setdefault(str(chapter), {})
    steps = ch_state.setdefault('steps_done', [])
    if skill_name not in steps:
        steps.append(skill_name)
    # ❌ 未发射 trace 事件
```

---

## 2. 修复方案

### 2.1 发射 MARK_DONE trace 事件

在 `_record_step_done` 中增加 trace 事件写入：

```python
def _record_step_done(state, chapter, skill_name):
    # ... 现有逻辑 ...

    # 新增：发射 trace 事件
    from shenbi.trace.writer import write_event
    write_event(
        project_dir,
        event_type="MARK_DONE",
        skill=skill_name,
        chapter=chapter,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

### 2.2 定期 materialize progress.json

在 chapter loop 的关键节点调用 `materialize_progress`：

```python
# 每章完成时
# 每 5 步时
# pipeline 暂停/终止时

from shenbi.trace.materialize import materialize_progress

def _maybe_update_progress(project_dir, force=False, steps_since_last=0):
    if force or steps_since_last >= 5:
        materialize_progress(project_dir)
```

### 2.3 启动时自愈

pipeline resume 时，如果 trace 有事件但 progress.json 未更新，自动调用 `materialize_progress` 重建。

---

## 3. 验证标准

1. 运行 3 章 mini-pipeline，每章完成后 progress.json 内容更新
2. progress.json 包含最新的 `completed_skill_names` 和 chapter 进度
3. 中断-恢复后 progress.json 反映最新状态

---

## 4. 依赖关系

```
无前置依赖（独立修复）
  ↓
为未来 P1.7（成本预算）和 P1.1（可观测性）提供数据基础
```
