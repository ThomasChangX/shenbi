# Expected Output: shenbi-chapter-revision Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Scope violation — revision introduces a new subplot character (mysterious stranger in dark cloak with silver eyes) in paragraph 9 that does not correspond to any audit finding | error | `drafts/chapter-12-revised.md`: paragraph 9 |
| 2 | Length constraint violation — revised chapter is 5100 words vs original 4200 words, a 21.4% increase exceeding the ±15% limit | error | `drafts/chapter-12-revised.md`: full document word count |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with fix accuracy for the two original audit findings (sword name fix and time-of-day fix are correct)
- Issues with content preservation for established plot/character elements unrelated to the scope violation
- Non-regression issues with blocking/critical/AI-trace counts (they did not increase from original audit)

## Expected Output Structure
- Quality check report with finding table
- Scope discipline analysis showing the new element has no corresponding audit finding
- Word count comparison: original vs revised with percentage delta
- Confirmation that the two legitimate audit fixes were correctly applied
