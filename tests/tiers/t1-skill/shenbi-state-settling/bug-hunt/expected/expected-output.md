# Expected Output: shenbi-state-settling Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Extraction accuracy violation — "Su Han secretly distrusts Zhao Wei" recorded as a direct change, but chapter 20 never explicitly states this; it is inferred from a single pause before answering | error | `state/chapter-20-settling.md`: Su Han distrust entry |
| 2 | Certainty distinction error — the inferred distrust is tagged as "direct" (certain) when it should be tagged "implied" at most, or excluded entirely | error | `state/chapter-20-settling.md`: certainty field for Su Han distrust entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the correctly extracted changes (Spirit Echo ability, allies-to-rivals shift, capital-to-northern-border move)
- Issues with category completeness (all 9 change categories are evaluated)
- Issues with incremental correctness (append-only updates are used correctly)
- Issues with human gate (no truth file was updated before human approval)

## Expected Output Structure
- Quality check report with finding table
- Extraction accuracy analysis showing the specific chapter text vs the claimed change
- Certainty tagging comparison showing mismatch
- Confirmation that the three correctly extracted changes pass validation
