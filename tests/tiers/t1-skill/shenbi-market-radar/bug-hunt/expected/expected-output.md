# Expected Output: shenbi-market-radar Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Data-backed claims violation — "mystery elements are trending strongly" stated with zero specific leaderboard rank or trend data point; bare assertion without evidence | error | `reports/market-radar.md`: trend identification section |
| 2 | Saturation detection failure — "reincarnation" appears in 14/20 top titles (70%) exceeding the 60% threshold but was not flagged as saturated; even recommended as selling point | error | `reports/market-radar.md`: leaderboard analysis section |
| 3 | Trend vs. imitation violation — "system-like progression" trend identified without differentiation suggestion; no guidance on avoiding imitation | error | `reports/market-radar.md`: trend identification section |
| 4 | Actionability violation — "Consider your options carefully" is not a single action and lacks one-line rationale | error | `reports/market-radar.md`: decision checklist |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with opening strategy, which is tied to specific genre + platform data
- Issues with benchmark identification (2 competitive works named with rationale)
- Issues with other checklist items that are properly actionable

## Expected Output Structure
- Quality check report covering all market radar sections
- Data citation audit for every claim
- Saturation analysis with element occurrence rates
- Trend differentiation completeness check
- Checklist actionability review
