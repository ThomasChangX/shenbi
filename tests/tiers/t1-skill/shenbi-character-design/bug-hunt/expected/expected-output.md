# Expected Output: shenbi-character-design Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Protagonist and mentor share identical voice markers (same sentence structures, same filler word "well", same register, same sentence-length pattern) — voices are indistinguishable | error | `characters/protagonist.md`: voice profile section; `characters/mentor.md`: voice profile section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the antagonist's voice (it is distinct)
- Issues with arc definition (all arcs are properly defined)
- Issues with relationship coherence (the matrix is consistent)

## Expected Output Structure
- Quality check report with finding table
- Specific comparison of the overlapping voice markers
- Severity classification for each issue
