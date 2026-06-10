# Expected Output: shenbi-power-system Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Level 4 "Spirit Sovereign" has no associated cost — violates cost enforcement (costless power) | error | `world/power-system.md`: Level 4 section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other levels (they all have explicit costs)
- Issues with the ceiling definition (top tier is properly defined with population count)
- Issues with level gap significance (gaps are qualitative)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of the missing cost at Level 4
- Severity classification for each issue
