# Expected Output: shenbi-length-normalizing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Narrative preservation violation — new scene added: a teahouse scene between the market walk and faction meeting that did not exist in the original, introducing new plot events and information | error | `drafts/chapter-7-normalized.md`: teahouse scene (between scenes B and C) |
| 2 | Consistency checklist missing — required checklist confirming no narrative changes is absent from the normalization report | error | `reports/chapter-7-normalize-report.md`: full document |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with word count (the normalized version achieves target length)
- Issues with voice preservation in existing scenes
- Issues with the 25% floor gate (compression ratio is 20%, within bounds)

## Expected Output Structure
- Quality check report comparing original vs normalized
- Identification of the new scene with comparison to original scene list
- Flagging of missing consistency checklist
