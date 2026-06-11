# Expected Output: shenbi-review-texture Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Laundry-list paragraph — paragraph 11 contains 4 sequential markers (然后×2, 接着×1, 之后×1, 随后×1) with zero conflict; exceeds ≥3 sequential markers threshold with no tension | error | `drafts/chapter-7.md`: paragraph 11 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other paragraphs that have <3 sequential markers
- Issues with paragraphs that have sequential markers but also contain conflict/tension

## Expected Output Structure
- Sequential marker count table per paragraph
- Laundry-list detection flagged for paragraphs with ≥3 markers and zero conflict
- Finding table with the unflagged laundry-list paragraph
- Fix recommendation: rewrite paragraph 11 to reduce sequential markers and add conflict or tension
