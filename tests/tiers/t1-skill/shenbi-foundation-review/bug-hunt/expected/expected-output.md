# Expected Output: shenbi-foundation-review Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Threshold enforcement failure — core-conflict dimension scored 14/30, which is below the 18/30 minimum; the core-conflict veto should have been triggered (unconditional fail) but the review gives a conditional pass instead | error | `reviews/foundation-review.md`: verdict section; core-conflict score field |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with dimension balance (5 dimensions scored independently, summing to 64)
- Issues with evidence-based evaluation (all scores based on existing content)
- Issues with the individual dimension scoring accuracy (each dimension score is reasonable)

## Expected Output Structure
- Quality check report with finding table
- Core-conflict score analysis: 14/30 vs 18/30 threshold
- Expected verdict (unconditional fail/veto) vs actual verdict (conditional pass)
- Reference to the threshold enforcement rule
