# Bug-Hunt Report: shenbi-foundation-review

## Defect Detection Results

### Defect 1: Core-conflict score below threshold but no veto triggered
- **Detected**: yes
- **Location**: `foundation-review-report.md` — core-conflict scoring table: "14/30 | 18/30 | conditional pass"
- **Violated Rule**: SKILL.md threshold enforcement — "核心冲突得分 < 18/30 必须触发 core-conflict veto，无条件失败"
- **Evidence**: Core conflict scored 14/30 (below the 18/30 threshold), but the report gives "conditional pass" instead of triggering the mandatory veto. Any score below threshold must result in unconditional failure, not conditional pass.
- **Severity**: error

## Summary
- Defects planted: 1, Detected: 1/1, False positives: 0
