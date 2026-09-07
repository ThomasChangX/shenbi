# Bug-Hunt Test: shenbi-location-builder

## Skill Under Test
`skills/shenbi-location-builder/SKILL.md`

## Test Setup
A novel project exists with location output:
- `tests/fixtures/chapter-plan-example.md` — capital city description
- `tests/fixtures/chapter-plan-example.md` — port city description
- `tests/fixtures/chapter-plan-example.md` — frontier fort description
- `tests/fixtures/chapter-plan-example.md` — overview map with distances

## Scenario
The location design has been generated. In `tests/fixtures/chapter-plan-example.md`, the chapter-end state is given as "林烽独自在锈泥巷的破屋里" (L26).
In `tests/fixtures/chapter-draft-example.md`, the room stands at the alley's very end (L86: "巷子最尽头是一间比其他更破的屋子") while the 灵能炉 also sits at the alley end (L40), yet L106 describes "中间隔了百来步和十几道墙" between them. The two fixtures' spatial descriptions of the same alley-end location are never reconciled, violating spatial consistency.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md` vs `tests/fixtures/chapter-draft-example.md` | Spatial consistency gap — memo ends with 林烽 alone in the 锈泥巷 room while the draft places both the room and the 灵能炉 at the alley's very end yet separates them by a hundred-odd steps and a dozen walls — the two descriptions are never reconciled | error |

## Agent Task
Run shenbi-location-builder quality check on the existing location output. The agent must detect the unreconciled spatial descriptions of the alley-end location across the two artifacts.
