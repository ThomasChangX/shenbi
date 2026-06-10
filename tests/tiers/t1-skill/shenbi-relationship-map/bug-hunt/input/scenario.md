# Bug-Hunt Test: shenbi-relationship-map

## Skill Under Test
`skills/shenbi-relationship-map/SKILL.md`

## Test Setup
A novel project exists with relationship map output:
- `characters/relationships.md` — relationship matrix with evolution plans
- `characters/` — character profiles (already exist)

## Scenario
The relationship map has been generated. Upon review, the relationship between the protagonist and the antagonist lists the current state ("bitter enemies") and has interest grounding (competing survival interests), but has no evolution plan — no start state, no turning points, and no expected end state are defined. This violates the evolution planning requirement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `characters/relationships.md`: protagonist-antagonist relationship entry | No evolution plan — missing start state, turning points, and expected end state | error |

## Agent Task
Run shenbi-relationship-map quality check on the existing relationship output. The agent must detect the relationship missing an evolution plan.
