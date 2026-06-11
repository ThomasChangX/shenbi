# Clean Test: shenbi-faction-builder

## Skill Under Test
`skills/shenbi-faction-builder/SKILL.md`

## Test Setup
A novel project exists with complete, correct faction output:
- `world/factions/iron-syndicate.md` — has internal factional split, interest-driven behavior, narrative prose
- `world/factions/dawn-collective.md` — has internal factional split, interest-driven behavior
- `world/factions/order-of-ash.md` — has internal factional split, interest-driven behavior
- `world/faction-relations.md` — ≥2 factions have explicit relationships
- All anchor characters referenced in faction files exist in `characters/*.md`

Every faction has internal conflict, all behavior is interest-driven, cross-faction dynamics are explicit, and behavioral patterns ("in situation X, faction does Y") are defined.

## Scenario
All faction content is correct and follows all skill rules. No monolithic factions, no missing relationships, no missing anchor characters.

## Agent Task
Run shenbi-faction-builder quality check on the existing output. Expected result: report zero issues.
