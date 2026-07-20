# 修复快照含未分离管道输出 + Lockfile 权限 + 决策预算复制 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔵 Low（3 个低优先级合并）
> **前置:** 无
> **目的:** 修复 Ch41/42 快照包含完整管道输出（18x/9x 章节大小）、lockfile 权限错误（0755 应为 0644）、6 对相邻决策共享相同 budget 字段。

---

## 1. 发现

### LN1: Ch41/42 快照膨胀（Agent 2 §6b）

| 章节 | 快照 | 章节文件 | 比率 |
|------|------|---------|------|
| Ch41 | 139,737 chars | 7,776 chars | **18x** |
| Ch42 | 109,890 chars | 11,757 chars | **9x** |

快照包含完整审计报告、真相提取块、修订表——应仅保存章节状态。

### LN2: Lockfile 权限异常（Agent 3 §5）

`pipeline-state.json.lockfile`：0 字节，权限 0755（应为 0644）。

### LN3: 决策 budget 复制（Agent 2 §5a）

6 对相邻决策 JSON 的 `budget` 字段逐字相同——未重新计算每章预算。

---

## 2. 修复方案

### LN1: 快照内容过滤

`_snapshot_chapter_files` 仅保存章节文件和核心 truth 文件，不含审计报告。

### LN2: Lockfile 权限修正

```python
# safe_write.py: _acquire_lock
os.chmod(lockfile, 0o644)
```

### LN3: Budget 去重检测

在 `g4_decisions` 中增加相邻章 budget 比较——如果完全相同，WARN。

---

## 3. 验证标准

1. 快照大小 ≤ 章节文件 × 5
2. Lockfile 权限 0644
3. 相邻章 budget 不同（非强制，仅 WARN）
