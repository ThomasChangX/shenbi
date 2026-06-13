# Bug-Hunt Test: shenbi-faction-builder

## Skill Under Test
`skills/shenbi-faction-builder/SKILL.md`

## Test Setup
A novel project exists with faction output:
- `tests/fixtures/world/factions/*.md` — one file per faction
- `tests/fixtures/report-example.txt` — cross-faction relationship map

## Scenario
The faction design has been generated. Three factions are defined: the Iron Syndicate, the Dawn Collective, and the Order of Ash. The Iron Syndicate and Dawn Collective each have internal factional splits. However, the Order of Ash is described as a monolithic entity with complete unity — no internal disagreements, no factional split, no dissenting voices. This violates the internal conflict requirement that every faction must have at least one internal factional split.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: internal structure section | No internal factional split — faction described as fully unified with zero dissent | error |

## Agent Task
Run shenbi-faction-builder quality check on the existing faction output. The agent must detect the faction missing internal conflict.
