# 修复 review-summary 审计全相同 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** 无
> **目的:** 修复所有 55 个 `audits/chapter-N-review-summary.md` 为相同占位符模板（99.4% 相似，零章节特定信息）的缺陷。

---

## 1. 背景

### 1.1 发现（Agent 2 Audit 2a）

所有 55 个 `review-summary.md` 文件近似相同：

```
# Chapter N — Consolidated Review Results
- **Reviews executed**: 11
- **Successful**: 11
- **Failed**: 0
```

- 平均成对相似度：**99.4%**
- 仅章节号变化
- 零章节特定信息
- 总浪费：~12KB + 55 次 LLM dispatch

### 1.2 影响

- review-summary 是给人类审阅者的汇总报告——完全无用
- 如果任何审计实际失败，此模板仍会报告"Failed: 0"
- 55 次 dispatch 的 token 完全浪费

---

## 2. 根因分析

`shenbi-escalation-review` SKILL.md 的设计意图是仅在 `escalation_check` 返回非空信号时触发。但在实际运行中，该 skill 每章都被调度且 LLM 产出了一个固定模板响应。

可能原因：
1. escalation 条件始终为 false → skill 应被跳过但未被跳过
2. skill 被无条件调用（非条件触发）
3. 或条件触发逻辑正确但 LLM 仍被要求产出文件

---

## 3. 修复方案

### 3.1 条件触发修正

```python
# chapter_loop.py: _should_run_step for shenbi-escalation-review
if step.skill == "shenbi-escalation-review":
    # 仅在 escalation 信号非空时才运行
    signals = _check_escalation_signals(state)
    if not signals:
        return False  # 跳过此步骤
```

### 3.2 替代方案：确定性汇总

如果 escalation 未触发，跳过 LLM dispatch，由代码生成汇总：

```python
def _generate_review_summary(project_dir, chapter):
    """确定性生成 review 汇总（无需 LLM）。"""
    audit_dir = project_dir / "audits"
    results = {}
    for audit_type in AUDIT_TYPES:
        af = audit_dir / f"chapter-{chapter}-{audit_type}.md"
        if af.exists():
            # 简单解析审计结果
            results[audit_type] = "PASS"  # 或实际解析
    return _render_summary_template(chapter, results)
```

---

## 4. 验证标准

1. 无 escalation 时 → 不生成 review-summary.md
2. 有 escalation 时 → review-summary.md 含章节特定信息
3. 确定性汇总正确反映各审计类型的存在/缺失
4. `just check` 全量通过

---

## 5. 依赖

```
无前置依赖（独立修复）
  ↓
对 Spec M1（Token 浪费）有贡献（节省 55 次 dispatch）
```
