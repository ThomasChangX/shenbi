# 修复 pipeline-state.json 数据陈旧 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** Spec H5（状态机修复）
> **目的:** 修复 `pipeline-state.json` 中审计计数与实际磁盘文件不一致的问题——报告 11 种审计但磁盘有 13 种，Ch56 报告 0 审计但磁盘有 7 个。

---

## 1. 背景

### 1.1 发现（Agent 3 §5）

- Pipeline 报告 11 种审计类型，但 `audits/chapter-N-*.md` 实际有 13 种
- `resonance.md` 和 `review-summary.md` 从未记录在状态中
- Ch56：pipeline 报告 0 审计，但磁盘存在 7 个审计文件

### 1.2 影响

- Pipeline 状态不可信——resume 可能跳过已完成步骤或重复执行
- 审计计数差异表明状态更新逻辑有 bug

---

## 2. 修复方案

### 2.1 审计计数从磁盘验证

在状态保存前，从磁盘验证实际审计文件数：

```python
def _count_audits_on_disk(project_dir, chapter):
    audit_dir = project_dir / "audits"
    return len(list(audit_dir.glob(f"chapter-{chapter}-*.md")))

# 状态保存前
actual_audits = _count_audits_on_disk(project_dir, chapter)
if actual_audits != recorded_audits:
    logger.warning("audit_count_mismatch", chapter=chapter,
                   recorded=recorded_audits, actual=actual_audits)
    # 自愈
    ch_state['audit_count'] = actual_audits
```

### 2.2 所有审计类型注册

确保 `resonance.md` 和 `review-summary.md` 在 AUDIT_TYPES 常量中注册。

---

## 3. 验证标准

1. Pipeline 状态中的审计计数与磁盘一致
2. `just check` 全量通过
