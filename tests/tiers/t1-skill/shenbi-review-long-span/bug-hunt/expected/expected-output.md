# Expected Output: shenbi-review-long-span Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Excessive 6-char n-gram repetition — "他不禁想起了那" appears 5 times across chapters 6-10, exceeding threshold per SKILL.md formula; repetition rate above acceptable limit | error | `drafts/chapter-6.md`: p3; `drafts/chapter-7.md`: p11; `drafts/chapter-8.md`: p5; `drafts/chapter-9.md`: p2; `drafts/chapter-10.md`: p8 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with unique phrases that appear only once
- Issues with common function words that repeat naturally

## Expected Output Structure
- 6-char n-gram extraction table with repetition counts
- Repetition rate computation per SKILL.md formula
- Threshold comparison
- Finding table with the over-repeated n-gram
- Fix recommendation: replace variations of "他不禁想起了那" with diverse expressions
