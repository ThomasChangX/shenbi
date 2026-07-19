# 修复 21 章缺少 revision-decisions.json Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec H2（修订系统修复）
> **目的:** 修复触发修订但未产出 revision-decisions.json 的 21 章——修订路由执行后文件未持久化。

---

## 1. 背景

### 1.1 发现（Agent 3）

21 章有修订路由但缺少 revision-decisions.json：
Ch3, 4, 10, 13, 14, 16, 17, 25, 27-32, 34, 36-38, 42, 54

这些章节 pipeline state 记录了修订路由（如 spot-fix、no-revision），但对应的 JSON 文件未写入磁盘。

---

## 2. 根因分析

可能原因：
1. 修订路由为 "no-revision" 时 skill 被跳过，但 pipeline 期望即使跳过也写入 decisions
2. 修订 dispatch 超时或失败但 pipeline 标记为完成
3. 写入路径问题——staging 未 commit

---

## 3. 修复方案

### 3.1 确保所有路由产出 decisions

无论什么修订路由（包括 no-revision），都必须写入 `revision-decisions.json`：

```python
# chapter_loop.py: after revision step
rev_path = project_dir / f"chapters/chapter-{chapter}-revision-decisions.json"
if not rev_path.exists():
    # 即使 no-revision，也写入一个最小 decisions
    min_decisions = {
        "route": "no_revision",
        "changes": [],
        "rationale": "All audits passed, no revision needed."
    }
    safe_write(rev_path, json.dumps(min_decisions, ensure_ascii=False, indent=2))
```

---

## 4. 验证标准

1. 所有 56 章有 revision-decisions.json（无论路由）
2. `just check` 全量通过
