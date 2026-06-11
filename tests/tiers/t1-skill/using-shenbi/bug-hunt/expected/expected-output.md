# Expected Output: using-shenbi Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| 1 | Request 3 misrouted to character-design instead of review-character | error | Trigger map says "看看角色" → review, not design |
| 2 | Request 7 misrouted to world-rules instead of review-continuity | error | "时间线" keywords match continuity audit |
| 3 | Request 9 skipped anti-detect check before polishing | warning | 1% rule requires checking all applicable skills |

## Expected Output Structure
- Each request shows the skill-check flow
- Route decisions are explicit
- 1% rule is documented for borderline cases
