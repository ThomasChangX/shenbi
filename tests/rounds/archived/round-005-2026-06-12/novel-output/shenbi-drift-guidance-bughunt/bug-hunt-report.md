# Bug-Hunt Report: shenbi-drift-guidance

## Defect Detection Results

### Defect 1: Error-level finding CC-F001 incorrectly conducted forward as drift guidance

- **Detected**: yes
- **Location**: `drift-conduction-summary.md` line 23 — row 5 in 已传导项 table: "review-continuity | error | 19 | CC-F001 | 下一章应处理赵林时间线不一致问题"
- **Violated Rule**: SKILL.md classification rule — "只有 warning 级别发现可以传导到下游章节。error 级别发现必须在当前章修订中处理，不得传导。"
- **Evidence**: The 已传导项 table contains 5 entries. Entry #5 has severity "error" (CC-F001 from review-continuity). The error-level finding "赵林时间线不一致——角色提及了尚未发生的事件" was conducted forward as drift guidance to chapter 19, but error-level findings must be fixed in the current chapter, not forwarded. Only warnings should pass through to drift guidance. The original "未传导项" section was modified to remove the ERROR classification, hiding the violation.
- **Severity**: error

## Summary

- **Total defects planted**: 1 (error-level finding conducted forward)
- **Defects detected**: 1/1
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | CC-F001 (error) conducted as drift guidance instead of being blocked | error | Classification rule: error必须当前章处理，不得传导 |
