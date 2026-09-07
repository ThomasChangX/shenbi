# Bug-Hunt Test: shenbi-power-system

## Skill Under Test
`skills/shenbi-power-system/SKILL.md`

## Test Setup
A novel project exists with power system output:
- `tests/fixtures/chapter-plan-example.md` — power levels, costs, boundaries, ceiling definition
- `tests/fixtures/chapter-plan-example.md` — level progression mapped to story milestones

## Scenario
The power system has been generated. Upon review, the declared ability cluster "分解/塑形/融合" is scheduled for its first full display in chapter 4, but the plan specifies no cost for using these abilities — the cost field is empty or missing. This violates the cost enforcement requirement that every power use must have a visible cost.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: 暂不掀 row for "分解/塑形/融合" | No cost associated with the declared abilities — cost field is empty/missing | error |

## Agent Task
Run shenbi-power-system quality check on the existing power system output. The agent must detect the costless power level.
