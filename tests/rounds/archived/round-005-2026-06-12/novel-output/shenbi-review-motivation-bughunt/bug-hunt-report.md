# Bug-Hunt Report: shenbi-review-motivation

## Defect Detection Results

### Defect 1: Unmotivated character action (小女孩递水) falsely passed

- **Detected**: yes
- **Location**: `review-report.md` — appended 补充审查 section, row: "小女孩 | 给林烽递水 | 利他动机 | ✓ 虽无角色档案，但儿童纯真行为合理 | PASS"
- **Violated Rule**: SKILL.md motivation verification rule — "无角色档案的角色执行主动行为时，必须在报告中标记为 'no archive — cannot verify'。不可用'儿童天真'等通用假设替代具体动机验证。"
- **Evidence**: The review report passes a nameless minor character's action (小女孩递水) based on the assumption "儿童纯真行为合理" (child innocence is reasonable). However, the character has no档案 (character profile), no prior interaction with the protagonist, and no established behavioral pattern. The SKILL.md requires that unmotivated actions by undocumented characters be flagged as unverifiable, not excused with generic stereotypes. Passing this as "PASS" with a "虽无角色档案" justification directly violates the verification discipline.
- **Severity**: error

## Summary

- **Total defects planted**: 1 (unmotivated character action falsely passed)
- **Defects detected**: 1/1
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | 无档案角色行为以通用假设通过 | error | 动机验证: 无档案角色不可用假设替代验证 |
