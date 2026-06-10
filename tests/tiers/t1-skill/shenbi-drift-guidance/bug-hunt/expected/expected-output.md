# Expected Output: shenbi-drift-guidance Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Classification violation — error-level finding CC-F001 from `audits/chapter-14-continuity.md` is conducted forward into drift guidance; errors must be blocked and only warnings should pass through | error | `guidance/drift-chapter-14.md`: drift item 1; `audits/chapter-14-continuity.md`: CC-F001 severity field |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with warning-level findings CC-F002, CH-F001, PC-F001 (correctly forwarded)
- Issues with cap enforcement (3 items ≤ 5 limit)
- Issues with the actionability of the warning-derived items

## Expected Output Structure
- Quality check report with finding table
- Severity classification analysis: audit findings vs drift guidance items
- Specific mapping showing CC-F001 (error) should have been blocked
- Confirmation that warning-level findings are correctly included
