# 修复快照覆盖缺口 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** 无
> **目的:** 确保所有章节（含 Ch1-4 和异常终止章节）均生成快照，完善 rollback 安全网。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

- **有快照**：Ch5-55（51 章）
- **缺失快照**：Ch1-4, Ch56（5 章）
- **快照损坏**：Ch9/12/44/55 的快照包含修订元文本而非小说正文

### 1.2 快照生成时机

`chapter_loop.py:242-247`（step 19）：
```python
ChapterStep(step_num=19, skill="shenbi-snapshot-manage", name="Snapshot",
            is_audit=False, output_path="snapshots/chapter-NNN.md"),
```

`_snapshot_chapter_files`（`chapter_loop.py:903-960`）由 `_should_run_step`（line 977-1001）拦截，直接执行确定性快照（不使用 LLM）。

### 1.3 Ch1-4 缺失的原因

Snapshot 从 step 19 开始运行，但 Ch1-4 可能在不同版本或调试阶段生成，快照步骤未被包含。

---

## 2. 修复方案

### 2.1 确保 Chapter 1 起即有快照

在 chapter loop 初始化阶段生成 Chapter 1 的起始快照：

```python
# chapter_loop.py: chapter loop 初始化
if state.chapter_loop.current_chapter == 1 and state.chapter_loop.step_index == 0:
    _snapshot_chapter_files(project_dir, state, force=True)
```

### 2.2 异常终止时自动快照

在 pipeline 的 `finally` 块或信号处理中，对当前章节生成紧急快照：

```python
import atexit

def _emergency_snapshot(project_dir, state):
    """在异常终止时保存当前章节状态。"""
    try:
        _snapshot_chapter_files(project_dir, state, label="emergency")
    except Exception:
        pass

atexit.register(_emergency_snapshot, project_dir, state)
```

### 2.3 快照内容守卫

在 `_snapshot_chapter_files` 中增加对章节文件的内容检查：

```python
# 如果章节文件内容疑似元输出（<500 中文字符），标记快照为 suspect
text = chapter_path.read_text()
chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
if chinese_chars < 500:
    logger.warning("snapshot_suspect_content", chapter=chapter,
                   chinese_chars=chinese_chars)
    # 仍然保存快照，但标记元数据
```

---

## 3. 验证标准

1. Chapter 1 完成后 `snapshots/` 中立即有文件
2. 模拟 SIGTERM → 紧急快照生成
3. 快照内容 ≥ 500 中文字符（suspect warning 仅在真正异常时触发）

---

## 4. 依赖关系

```
无前置依赖（独立修复）
  ↓
对 Spec C1（章节恢复）有支持作用
```
