# Expected Output: shenbi-plot-thread-weaver Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Chapter 15 advances zero threads — no A-line, B-line, or C-line contact (blank chapter) | error | `story/thread-map.md`: Chapter 15 entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other chapters (they all advance at least one thread)
- Issues with A-line contact discipline (no A-lines exceed max_gap)
- Issues with C-line closure (all C-lines resolve within their planned span)
- Issues with priority classification (all priorities are correctly assigned)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of Chapter 15 with its empty thread assignment
- Severity classification for each issue
