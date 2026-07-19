# 提升 Pipeline 可观测性指标 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔵 Low
> **前置:** Spec M2（progress 追踪）— 共享 trace 基础设施
> **目的:** 增加 per-step 计时日志、API token 追踪、章节字数稳定性监控，为未来 P1.1（可观测性）和 P1.7（成本预算）打基础。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

三个 Low 级别的可观测性缺陷：

**L1 — 耗时波动大：**
- 章间耗时范围：10 min（Ch13）→ 93 min（Ch26），波动 9.3x
- 无 per-step 计时日志，无法定位瓶颈在哪个 skill

**L2 — 成本追踪缺失：**
- 整个 40 小时运行无 token 计数、无成本日志
- 估算约 $0.84，但精确数据不可得
- API executor（`dispatch_helper.py`）未记录 `response.usage`

**L3 — 字数波动大：**
- 范围：101 字（Ch55，损坏）→ 18,363 字（Ch47），正常范围约 8K-18K 字
- 标准差过大，暗示 chapter memo 的字数约束不稳定

---

## 2. 修复方案

### 2.1 L1：per-step 计时

在 `run_chapter_step`（`chapter_loop.py:1072`）中增加：

```python
import time
step_start = time.monotonic()
try:
    # ... 执行 step ...
finally:
    elapsed = time.monotonic() - step_start
    logger.info("step_timing", chapter=state.chapter_loop.current_chapter,
                step=step.skill, elapsed_seconds=round(elapsed, 1))
    # 存储到 PipelineState 供后续分析
    _record_step_timing(state, step.skill, elapsed)
```

结束时输出汇总：
```
Step timing summary:
  shenbi-chapter-drafting:  avg 12.3min (min 8.2, max 22.1)
  shenbi-state-settling:    avg 5.7min  (min 3.1, max 15.0)
  shenbi-review-resonance:  avg 4.2min  (min 2.0, max 8.5)
```

### 2.2 L2：API token 追踪

在 `dispatch_helper.py` 的 API dispatch 路径中记录 usage：

```python
# 在 API response 处理后
if hasattr(response, 'usage'):
    usage = response.usage
    logger.info("llm_token_usage",
                skill=skill_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens)
    _record_token_usage(state, skill_name, usage)
```

非 API 路径（codex CLI）暂跳过（Spec M2 progress 追踪可近似推算）。

### 2.3 L3：字数稳定性

在 chapter memo 和 chapter planning 的 prompt 中收紧字数范围：

```markdown
- 目标字数: 5000-8000 字（Transition 章）/ 8000-12000 字（Advance 章）
- **禁止**低于 4000 字（除非 chapter_role 为"过渡/铺垫"且有明确理由）
- **禁止**超过 15000 字（超过视为未遵守约束）
```

增加 G4 post-write 字数范围检查：

```python
# G4.chapter_drafting 新增
if chapter_role == "transition" and word_count > 8000:
    issues.append("G4.cd.word_ceiling:transition_exceeded")
if chapter_role == "climax" and word_count < 6000:
    issues.append("G4.cd.word_floor:climax_below_minimum")
```

---

## 3. 验证标准

1. Pipeline 运行后日志含 per-step 计时
2. Pipeline 完成时打印 timing 汇总
3. API 路径运行时日志含 token usage
4. 连续 10 章字数在目标范围内（±30%）

---

## 4. 依赖关系

```
Spec M2（progress 追踪） ← 弱依赖（共享 trace 基础设施）
  ↓
为未来 P1.1（可观测性）和 P1.7（成本预算）提供数据基础
```
