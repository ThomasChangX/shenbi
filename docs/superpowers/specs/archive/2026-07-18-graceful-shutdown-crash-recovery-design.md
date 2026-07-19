# Pipeline 优雅关闭与崩溃恢复 Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec H5（状态机修复）
> **目的:** 修复 pipeline 在 Ch56 中断时无信号处理、无紧急快照、无状态恢复的缺陷——确保任何终止方式（SIGTERM/Ctrl-C/超时）都能安全保存进度。

---

## 1. 背景

### 1.1 证据

Ch56 在 `current_step=''`, `step_index=9` 时中断。`pipeline-state.json` 保留了中断前的状态，但：
- `current_step` 为空字符串（H5 的根因）
- 无紧急快照保护当前章节
- 无信号处理器——`kill` 或 `Ctrl-C` 直接终止进程
- `pipeline resume` 无法确定从哪个步骤恢复

### 1.2 影响

- 中断章节的部分工作可能丢失（已写入的 staging 文件未清理）
- 长时间运行（40 小时/56 章）的 pipeline 可能在任何时刻因 OOM、API 限流、网络中断而崩溃
- 无崩溃恢复能力 = 生产不可用

---

## 2. 修复方案

### 2.1 信号处理器

```python
# src/shenbi/pipeline/crash_recovery.py (新增)

import atexit
import signal
import sys
from pathlib import Path

# 模块级状态——由 pipeline 入口设置
_emergency_state: dict = {
    'project_dir': None,
    'pipeline_state': None,
    'shutdown_requested': False,
}

def register_emergency_handlers(project_dir: Path, state: 'PipelineState'):
    """在 pipeline 启动时注册紧急处理器。"""
    _emergency_state['project_dir'] = project_dir
    _emergency_state['pipeline_state'] = state

    # SIGTERM（kill 命令）
    signal.signal(signal.SIGTERM, _handle_emergency_signal)
    # SIGINT（Ctrl-C）
    signal.signal(signal.SIGINT, _handle_emergency_signal)
    # atexit（正常退出也会触发，通过 shutdown_requested 区分）
    atexit.register(_emergency_cleanup)

def _handle_emergency_signal(signum, frame):
    """信号处理器——设置标志后优雅退出。"""
    logger.warning("emergency_signal_received", signal=signum)
    _emergency_state['shutdown_requested'] = True

    # 执行紧急清理
    _emergency_cleanup()

    # 重新抛出信号（让进程以正确的退出码终止）
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)

def _emergency_cleanup():
    """紧急清理——保存状态 + 生成快照。"""
    if _emergency_state['shutdown_requested']:
        _save_emergency_state()

    # 正常退出时也保存（atexit）——但仅当有未保存的变更时
    elif _has_unsaved_changes():
        _save_emergency_state()

def _save_emergency_state():
    """保存当前 pipeline 状态和紧急快照。"""
    project_dir = _emergency_state['project_dir']
    state = _emergency_state['pipeline_state']

    if project_dir is None or state is None:
        return

    try:
        # 1. 标记当前步骤为紧急关闭
        cl = state.chapter_loop
        if cl.step_index < len(CHAPTER_STEPS):
            cl.current_step = f"EMERGENCY_SHUTDOWN_AT_{CHAPTER_STEPS[cl.step_index].skill}"

        # 2. 保存 pipeline 状态
        from shenbi.pipeline.state import save_pipeline_state
        save_pipeline_state(project_dir, state)
        logger.info("emergency_state_saved", chapter=cl.current_chapter, step_index=cl.step_index)

        # 3. 生成紧急快照
        from shenbi.pipeline.chapter_loop import _snapshot_chapter_files
        _snapshot_chapter_files(project_dir, state, label="emergency")
        logger.info("emergency_snapshot_created", chapter=cl.current_chapter)

        # 4. 清理 staging
        from shenbi.pipeline.checkpoint import clear_staging
        clear_staging(project_dir)

    except Exception as e:
        logger.error("emergency_cleanup_failed", error=str(e))
        # 不抛出——清理失败不应阻止进程退出

def is_shutdown_requested() -> bool:
    """供 chapter_loop 在步骤间检查——优雅地在步骤边界退出。"""
    return _emergency_state['shutdown_requested']
```

### 2.2 Chapter Loop 集成

```python
# chapter_loop.py: 主循环中

for step in CHAPTER_STEPS:
    # 每步前检查是否收到关闭信号
    if is_shutdown_requested():
        logger.info("graceful_shutdown_at_step_boundary",
                    chapter=state.chapter_loop.current_chapter,
                    step=step.skill)
        break  # 不在步骤中途退出

    result = run_chapter_step(state, step)
    # ... 正常流程 ...
```

### 2.3 Resume 恢复逻辑

```python
# cli.py: pipeline resume

def cmd_resume(project_dir):
    state = load_pipeline_state(project_dir)
    cl = state.chapter_loop

    # 检查是否从紧急关闭恢复
    if cl.current_step and cl.current_step.startswith("EMERGENCY_SHUTDOWN"):
        logger.warning("resuming_from_emergency_shutdown",
                       chapter=cl.current_chapter,
                       step_index=cl.step_index)
        # 清除紧急标记
        cl.current_step = CHAPTER_STEPS[cl.step_index].skill if cl.step_index < len(CHAPTER_STEPS) else ""
        save_pipeline_state(project_dir, state)

    # 正常 resume 流程...
```

---

## 3. 验证标准

1. `kill -TERM <pid>` → pipeline 保存状态 + 生成紧急快照后退出
2. `Ctrl-C` → 同上
3. `pipeline resume` 从紧急关闭恢复 → `current_step` 被正确恢复
4. 步骤边界检查——在步骤之间退出，不中断正在执行的 LLM 调用
5. 紧急清理失败不阻止进程退出（防御性 try/except）
6. `just check` 全量通过

---

## 4. 依赖

```
Spec H5（状态机修复）← current_step 正确性是恢复的前提
Spec M3（快照覆盖）← 紧急快照依赖 snapshot 机制
  ↓
本 Spec
```
