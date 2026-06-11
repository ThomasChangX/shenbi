# Expected Output: shenbi-review-foreshadowing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Lifecycle tracking gap — "mysterious-key" hook PLANTED → ADVANCED transition has no text evidence; missing chapter citation and specific prose passage for the ADVANCED state | error | `audit/foreshadowing-review.md`: mysterious-key ADVANCED entry; expected evidence at `drafts/chapter-4.md`: paragraph 12 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the PLANTED state evidence (it correctly cites chapter 3, paragraph 8)
- Issues with other hooks tracked in the report (they have proper lifecycle evidence)

## Expected Output Structure
- Hook lifecycle tracking table with state transitions
- Each transition must cite chapter + specific prose passage
- Finding table identifying the missing evidence
- Fix recommendation: add text evidence citation for ADVANCED state (chapter 4, paragraph 12: "用那把从地板下找到的旧钥匙打开了门")
