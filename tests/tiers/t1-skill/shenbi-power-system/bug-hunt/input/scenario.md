# Bug-Hunt Test: shenbi-power-system

## Skill Under Test
`skills/shenbi-power-system/SKILL.md`

## Test Setup
A novel project exists with power system output:
- `tests/fixtures/chapter-plan-example.md` — power levels, costs, boundaries, ceiling definition
- `tests/fixtures/chapter-plan-example.md` — level progression mapped to story milestones

## Scenario
The power system has been generated. Upon review, Level 4 "Spirit Sovereign" describes abilities and effects but specifies no cost for using its powers. Every other level has an explicit cost section, but Level 4's cost field is empty or missing. This violates the cost enforcement requirement that every power use must have a visible cost.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: Level 4 "Spirit Sovereign" section | No cost associated with Level 4 powers — cost field is empty/missing | error |

## Agent Task
Run shenbi-power-system quality check on the existing power system output. The agent must detect the costless power level.
