# Expected Output: shenbi-review-highpoint Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Climax deflation — buildup level 5 (8 paragraphs of escalating confrontation, paragraphs 5-12) but payoff level 2 (antagonist surrenders in single short paragraph 13); deflation detected: payoff (2) < buildup (5) | error | `drafts/chapter-11.md`: paragraphs 5-13 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with non-climax segments (correctly paced)
- Issues with the buildup quality (the buildup itself is strong)

## Expected Output Structure
- Climax segment identification with buildup/payoff rating on 1-5 scale
- Text evidence for both buildup level and payoff level
- Deflation detection where payoff < buildup
- Fix recommendation: expand the payoff to match buildup intensity, or reduce buildup to match payoff
