# Expected Output: shenbi-chapter-pattern Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Threshold strictness violation — chapters 3-7 form a run of 5 consecutive "action" primary pattern chapters, exceeding the 3-chapter consecutive limit; not flagged in analysis | error | `analysis/chapter-patterns.md`: threshold analysis section; chapters 3-7 pattern assignments |
| 2 | Threshold strictness violation — chapters 10-14 form a run of 5 consecutive "action" primary pattern chapters, exceeding the 3-chapter consecutive limit; not flagged in analysis | error | `analysis/chapter-patterns.md`: threshold analysis section; chapters 10-14 pattern assignments |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with individual chapter pattern classifications (each chapter is correctly assigned)
- Issues with entropy calculation (the entropy value is correctly computed)
- Issues with chapters that are not part of consecutive runs

## Expected Output Structure
- Quality check report with finding table
- Consecutive pattern run analysis showing both violations (chapters 3-7 and chapters 10-14)
- Expected threshold (3) vs actual consecutive counts (5)
- Recommendation that pattern variety should be introduced in both runs
