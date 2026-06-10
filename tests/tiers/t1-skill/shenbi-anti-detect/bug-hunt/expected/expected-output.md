# Expected Output: shenbi-anti-detect Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Targeted intervention violation — wholesale rewrite detected: at least 8 paragraphs without AI markers were rewritten, far exceeding the 5 identified marker points | error | `drafts/chapter-7-antidetect.md`: paragraphs without markers vs original |
| 2 | Content preservation violation — foreshadowing clue lost: the pendant detail present in the original draft was removed during the anti-detect rewrite | error | `drafts/chapter-7-antidetect.md`: pendant scene vs original |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with bounded iteration (the pass did complete)
- Issues with style preservation at the actual marker points (those rewrites are appropriate)

## Expected Output Structure
- Quality check report comparing original vs anti-detect output
- Identification of non-marker paragraphs that were rewritten
- Evidence of foreshadowing content loss
- Before/after audit comparison showing intervention scope exceeded marker points
