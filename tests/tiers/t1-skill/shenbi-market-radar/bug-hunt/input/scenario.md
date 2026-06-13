# Bug-Hunt Test: shenbi-market-radar

## Skill Under Test
`skills/shenbi-market-radar/SKILL.md`

## Test Setup
A market radar report has been generated for an urban fantasy novel targeting the Qidian platform. The report is at `tests/fixtures/report-example.txt` with sections on leaderboard analysis, trend identification, opening strategy, competitive benchmarks, and decision checklist.

## Scenario
The market radar report has been completed. However, it contains unsupported claims and missing analysis:

1. **Unsupported claim**: The report states "Mystery elements are trending strongly on Qidian right now" but provides no specific leaderboard rank or trend data point. No rank number, no percentage change, no specific title or position is cited. This is a bare assertion without data backing.

2. **Missing saturation flag**: The leaderboard analysis shows that "reincarnation" appears in 14 of the top 20 titles (70% occurrence rate). This exceeds the 60% saturation threshold, but the report does not flag "reincarnation" as a saturated element and even recommends including reincarnation as a selling point.

3. **Trend without differentiation**: The report identifies "system-like progression" as a trend signal but provides no differentiation suggestion — no guidance on how to use this trend without falling into imitation. The trend is noted but the required differentiation advice is absent.

4. **Non-actionable checklist item**: The decision checklist includes the item "Consider your options carefully" which is not a single action and has no one-line rationale.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/report-example.txt`: trend identification section | Data-backed claims violation — "mystery elements are trending" stated without any specific leaderboard rank or trend data point | error |
| `tests/fixtures/report-example.txt`: leaderboard analysis section | Saturation detection failure — "reincarnation" appears in 14/20 titles (70%) but not flagged as saturated; instead recommended as selling point | error |
| `tests/fixtures/report-example.txt`: trend identification section | Trend vs. imitation violation — "system-like progression" trend identified without differentiation suggestion | error |
| `tests/fixtures/report-example.txt`: decision checklist | Actionability violation — "Consider your options carefully" is not a single action and lacks rationale | error |

## Agent Task
Run shenbi-market-radar quality check on the report. The agent must detect the unsupported claim, the missed saturation flag, the trend without differentiation, and the non-actionable checklist item.
