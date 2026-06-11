# Expected Output: shenbi-chapter-drafting Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | PRE_WRITE_CHECK step missing — no evidence of prerequisite verification before drafting began | error | `drafts/chapter-7.md`: full document, absence of check log |
| 2 | AI-flavor transition word density violation — "然而" (4x), "不过" (3x), "与此同时" (2x) in ~3000 words, total density exceeds 1/3000 threshold | error | `drafts/chapter-7.md`: throughout prose |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with plan compliance (the chapter follows the memo)
- Issues with voice fidelity (dialogue matches character profiles)
- Issues with show-don't-tell (emotions are shown through action)
- Issues with foreshadowing integrity (foreshadowing items are present)

## Expected Output Structure
- Quality check report with finding table
- Enumeration of both defects with evidence
- Transition word density calculation shown
- PRE_WRITE_CHECK absence clearly flagged
