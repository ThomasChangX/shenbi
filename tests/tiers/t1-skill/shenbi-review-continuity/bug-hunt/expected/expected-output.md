# Expected Output: shenbi-review-continuity Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Timeline contradiction — ch2 time marker "三天后" (chapter 2, last paragraph) establishes 3-day gap, but ch3 paragraph 7 describes "五天的恢复" (5-day recovery), creating a 2-day discrepancy | error | `drafts/chapter-2.md`: last paragraph; `drafts/chapter-3.md`: paragraph 7 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with character continuity across chapters (consistent)
- Issues with setting/location continuity (consistent)
- Issues with object continuity (consistent)

## Expected Output Structure
- Timeline extraction table with all explicit time markers
- Cross-chapter comparison showing the discrepancy
- Finding table with the timeline contradiction
- Fix recommendation: reconcile either "三天后" or "五天的恢复" to be consistent
