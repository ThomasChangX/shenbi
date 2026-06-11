# Expected Output: shenbi-review-anti-ai Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Incomplete pattern coverage — checks 8, 9, 10 silently skipped; audit report contains only 7 of 10 required deterministic checks with no PASS/ERROR result for the missing 3 | error | `audit/anti-ai-review-ch9.md`: absence of checks 8, 9, 10 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with checks 1-7 that returned PASS (they are correct)
- Issues with check 3 and check 7 that returned ERROR (those are legitimate findings)

## Expected Output Structure
- Full 10-check checklist with PASS/ERROR result for each
- Finding table identifying the 3 missing checks
- Fix recommendation: execute checks 8, 9, 10 and report their results
