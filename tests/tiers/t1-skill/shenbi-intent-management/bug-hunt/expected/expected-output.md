# Expected Output: shenbi-intent-management Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Human sovereignty violation — P1 item "Consider introducing a romantic subplot between Lin and a secondary character to add emotional depth" does not originate from any human input, drift guidance, or author intent file; the AI made an autonomous creative decision | error | `truth/current_focus.md`: P1 items section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the human-provided intent items (rivalry focus, tension development)
- Issues with drift guidance integration (3 drift items correctly merged)
- Issues with priority assignments for legitimate items
- Issues with format compliance (YAML frontmatter is correct)

## Expected Output Structure
- Quality check report with finding table
- Source tracing analysis: showing the romantic subplot suggestion has no origin in human input
- Comparison of current_focus.md items against human input sources
- Confirmation that human-originated items are correctly organized
