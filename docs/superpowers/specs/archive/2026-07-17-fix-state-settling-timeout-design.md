# 修复 state-settling 超时处理 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** 无
> **目的:** 解决大章节（如 Ch35 38KB）的 state-settling 超过 900s dispatch timeout 的问题。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

Chapter 35 的 state-settling 耗时超过 900s，触发 escalation checkpoint。重试后成功，但暴露了硬编码超时不适合大章节的问题。

章节大小 vs 可能的 state-settling 时间：

| 章节大小 | state-settling 预期耗时 | 当前超时 | 风险 |
|---------|----------------------|---------|------|
| < 10KB | 2-5 min | 900s | 无 |
| 10-20KB | 5-10 min | 900s | 无 |
| 20-30KB | 10-15 min | 900s | 无 |
| 30-40KB (Ch35) | 15-25 min | 900s | **边界** |

### 1.2 当前超时配置

`dispatch_helper.py` 的 dispatch timeout 是**全局硬编码**的（900s = 15min）。state-settling 作为最重的步骤（需读取所有 truth 文件 + 当前章节 + 更新 7 个 truth 文件），在大章节时容易触发。

---

## 2. 修复方案

### 2.1 动态超时（推荐）

基于章节字数动态计算 timeout：

```python
# dispatch_helper.py
def _compute_dispatch_timeout(chapter_path: Path | None = None) -> int:
    """基于章节大小计算 dispatch timeout。

    基础: 300s (5min)
    每 1KB 章节内容: +30s
    上限: 1800s (30min)
    """
    base = 300
    if chapter_path and chapter_path.exists():
        chapter_size_kb = chapter_path.stat().st_size / 1024
        extra = int(chapter_size_kb * 30)
    else:
        extra = 0
    return min(base + extra, 1800)
```

### 2.2 state-settling 特殊处理

对 state-settling 使用 2x 系数（因为它需要读取大量 truth 文件）：

```python
if skill_name == "shenbi-state-settling":
    timeout = int(timeout * 2.0)
```

### 2.3 超时后优雅降级

超时后不直接失败，而是：
1. 保存 LLM 已输出的部分结果
2. 对未完成的 truth 文件使用上一次的版本
3. 记录 WARN（非 HARD 失败）

---

## 3. 验证标准

1. 10KB 章节 timeout ≈ 600s
2. 38KB 章节 timeout ≈ 1440s（24min）
3. 上限不超过 1800s

---

## 4. 依赖关系

```
无前置依赖（独立修复）
```
