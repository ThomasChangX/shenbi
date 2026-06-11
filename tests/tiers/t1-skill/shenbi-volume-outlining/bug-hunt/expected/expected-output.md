# Expected Output: shenbi-volume-outlining Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Volume 2 has no cross-volume bridge — ends with all threads resolved, no hooks toward Volume 3 | error | `story/volumes/volume-2.md`: ending section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with Volume 1 (has proper hook bridging to Volume 2)
- Issues with Volume 3 (has proper hook bridging)
- Issues with OKR executability (all KRs map to specific chapter ranges)
- Issues with tension curve design (wave pattern is properly applied)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of Volume 2's clean ending with no hook
- Severity classification for each issue
