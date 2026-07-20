# Pipeline 步骤并行化 Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🟡 Medium（性能优化）
> **前置:** Spec 步骤重组（MERGE-1 foreshadowing 合并必须先落地）
> **目的:** 识别并实现可并行化的 LLM 调用——在不影响生成质量的前提下减少串行等待时间。

---

## 1. 背景

### 1.1 依赖分析结论

对流水线全部 LLM 调用的读/写依赖进行逐对分析：

```
planning ──→ drafting ──→ state-settling
                │              │
                │              ├→ current_state.md, character_matrix.md,
                │              │   chapter_summaries.md, emotional_arcs.md,
                │              │   particle_ledger.md, subplot_board.md
                │              │
                └→ foreshadowing-lifecycle
                               │
                               └→ pending_hooks.md
```

**关键发现**：state-settling 和 foreshadowing-lifecycle 都依赖 drafting 完成，但**写入不同的 truth 文件**——零写冲突。

### 1.2 不可并行化的调用

| 尝试 | 阻断 | 数据类型 |
|------|------|---------|
| planning ∥ drafting | drafting 读 plan | 读写依赖 |
| drafting ∥ audits | audits 读 chapter | 读写依赖 |
| plant ∥ context-composing | composing 读 plant 更新后的 pending_hooks | 写后读依赖 |
| track ∥ recall | recall 读 track 更新后的 pending_hooks | 写后读依赖 |
| audits ∥ revision | revision 读 audit 结果 | 读写依赖 |

**这些依赖是正确且必要的**——不能审计还没写的章节，不能基于旧版 pending_hooks 做 recall。

---

## 2. 修复方案

### 2.1 重组后流水线：foreshadowing-lifecycle ∥ state-settling

**前提**：Spec 步骤重组的 MERGE-1（3 个 foreshadowing → 1 个 lifecycle）已落地。

**当前串行**：
```python
# chapter_loop.py: run_chapter_step 中
for step in [drafting_step, lifecycle_step, state_settling_step]:
    result = run_chapter_step(state, step)  # 串行等待
```

**改为并行**：
```python
# chapter_loop.py: run_chapter_step 中

# Step 1: drafting（必须串行——后续步骤都依赖它）
drafting_result = run_chapter_step(state, drafting_step)

# Step 2: lifecycle ∥ state-settling（并行——无数据冲突）
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    lifecycle_future = executor.submit(run_chapter_step, state, lifecycle_step)
    settling_future = executor.submit(run_chapter_step, state, state_settling_step)

    # 等待两者完成
    lifecycle_result = lifecycle_future.result()
    settling_result = settling_future.result()

# 验证两者都成功
if not lifecycle_result.success or not settling_result.success:
    # 处理失败——可能需要重试其中一个
    ...
```

**安全性验证**：

| 检查项 | lifecycle | state-settling | 结论 |
|--------|-----------|----------------|------|
| 共同依赖 | drafting 完成 | drafting 完成 | ✅ 相同 |
| 写入文件 | `pending_hooks.md` | `current_state.md`, `character_matrix.md`, `chapter_summaries.md`, `emotional_arcs.md`, `particle_ledger.md`, `subplot_board.md` | ✅ 零交集 |
| 读取对方写入 | 否 | 否 | ✅ 零读后写 |
| 读取相同文件 | `chapter-N.md`, `pending_hooks.md`(读) | `chapter-N.md` | ✅ 只读不写冲突 |
| 失败隔离 | lifecycle 失败不影响 truth | state-settling 失败不影响 hooks | ✅ 独立重试 |

**唯一共享资源**：`chapter-N.md`（只读）——两个调用同时只读相同文件是安全的。

### 2.2 当前流水线（过渡方案）：state-settling ∥ foreshadowing-track

在 MERGE-1 落地之前，可以先并行化当前流水线：

```python
# 当前：Step 7 state-settling, Step 8 foreshadowing-track
# 改为并行：
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    settling_future = executor.submit(run_chapter_step, state, state_settling_step)
    track_future = executor.submit(run_chapter_step, state, foreshadowing_track_step)

    settling_result = settling_future.result()
    track_result = track_future.result()
```

**安全性**：state-settling 写 6 个 truth 文件，track 写 `pending_hooks.md`。零冲突。

**注意**：foreshadowing-recall（Step 9）必须在 track 完成后串行运行——recall 需要读取 track 更新后的 `pending_hooks.md`。

### 2.3 `safe_write` 锁机制验证

当前 `safe_write` 使用 `fcntl.flock`（POSIX）或 O_EXCL lockfile（fallback）——**文件级锁**。两个并行调用写入不同文件时不会互相阻塞。✅

```python
# safe_write.py:40-88
# 锁作用于目标文件的父目录或专用 lockfile
# 不同文件 → 不同锁 → 零竞争
```

---

## 3. 不可并行化的根本原因

流水线的核心路径是严格顺序的：

```
Plan → Draft → Audit → Revise
```

这四条路径构成了 **WAR（Write-After-Read）依赖链**——每一步消费前一步的产出。这是正确的架构——无法且不应并行化核心创作路径。

并行化空间仅存在于**消费同一上游产出、写入不同下游**的"扇出"步骤之间。在 shenbi 流水线中，这些是 drafting 之后的 truth 文件更新步骤。

---

## 4. 效果

| 场景 | 串行耗时 | 并行耗时 | 节省 |
|------|---------|---------|------|
| 重组后：lifecycle + state-settling | 3.5 + 7.0 = 10.5 min | max(3.5, 7.0) = 7.0 min | **3.5 min (33%)** |
| 当前：track + state-settling | 2.0 + 7.0 = 9.0 min | max(2.0, 7.0) = 7.0 min | 2.0 min (22%) |
| 当前：recall + state-settling | 1.0 + 7.0 = 8.0 min | max(1.0, 7.0) = 7.0 min | 1.0 min (13%) |

**累计效果（重组+并行化后每章）**：

| 阶段 | 优化前 | 优化后 |
|------|--------|--------|
| 串行 LLM | ~23.2 min | ~19.7 min |
| 并行审计 | ~3.8 min | ~3.8 min |
| 条件调用 | ~0.7 min | ~0.7 min |
| 重试 | ~2.5 min | ~2.5 min |
| **总计** | **~30 min** | **~27 min** |

---

## 5. 验证标准

1. `chapter_loop.py` 中 drafting 后的步骤使用 `ThreadPoolExecutor` 并行执行
2. 并行执行时 `safe_write` 无死锁或竞争
3. 并行产生的 `pending_hooks.md` 与串行版本内容一致（回归测试）
4. 并行产生的 6 个 truth 文件与串行版本内容一致
5. 失败隔离：lifecycle 失败不影响 state-settling 继续（反之亦然）
6. `just check` 全量通过

---

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 两个并行调用同时读取 chapter-N.md 可能触发 I/O 瓶颈 | 只读访问无需锁，操作系统页面缓存处理并发读 |
| 并行调用可能触发 API rate limit | DeepSeek API 通常允许 ≥2 并发请求；如有限制，使用信号量控制 |
| `pipeline-state.json` 被两个并行步骤同时更新 | 两个步骤写入 `chapter_states` 的不同 key（不同的 steps_done 条目），但需要确保 `PipelineState` 对象的线程安全 |
| 状态持久化的线程安全 | `PipelineState` 的 `_record_step_done` 需要加锁或使用 `threading.Lock` |

### 6.1 PipelineState 线程安全

```python
# state.py 或 chapter_loop.py
import threading

_state_lock = threading.Lock()

def _record_step_done_threadsafe(state, chapter, skill_name):
    with _state_lock:
        ch_state = state.chapter_loop.chapter_states.setdefault(str(chapter), {})
        steps = ch_state.setdefault('steps_done', [])
        if skill_name not in steps:
            steps.append(skill_name)
```

---

## 7. 依赖

```
Spec 步骤重组（MERGE-1: foreshadowing 合并）
  ↓ 必须先落地——否则并行化目标不同
本 Spec
  ↓
chapter_loop.py 执行引擎修改
```
