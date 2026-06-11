# Clean Test: shenbi-market-radar

## Skill Under Test
`skills/shenbi-market-radar/SKILL.md`

## Test Setup
A market radar report has been correctly generated for an urban fantasy novel targeting the Qidian platform. The report is at `reports/market-radar.md`.

All output is correct:
- Every recommendation references specific leaderboard rank or trend data point
- Saturated elements (>60% occurrence in top-20) are flagged
- Each trend signal includes a differentiation suggestion
- Every checklist item is a single action with one-line rationale
- Opening strategy tied to specific genre + platform data
- >=2 competitive works named with rationale

## Scenario
All market radar output is correct and follows all skill rules.

## Agent Task
Run shenbi-market-radar quality check on the report. Expected result: report zero issues.
