# Expected Output: shenbi-worldbuilding Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Hard Rule 3 ("spiritual energy is finite and depletes with use") contradicts Hard Rule 7 ("spiritual energy regenerates infinitely over time for all cultivators") | error | `world/rules.md`: hard rules section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with soft rules (they are flexible by definition)
- Issues with the story_bible.md prose format (it is correct)
- Issues with the undercurrent.md (it correctly seeds conflict sources)

## Expected Output Structure
- Quality check report with finding table
- Severity classification for each issue
- Specific evidence citations pointing to file and section
