# Clean Test: shenbi-relationship-map

## Skill Under Test
`skills/shenbi-relationship-map/SKILL.md`

## Test Setup
A novel project exists with complete, correct relationship map output:
- `characters/relationships.md` — every relationship has start state, turning points, expected end state, interest grounding, and information boundary records
- All relationship data exists only in relationships.md (no duplication in character cards)
- Information asymmetries are tracked as dramatic tension sources
- All referenced characters exist in character files

Every relationship has a complete evolution plan and is grounded in interest/emotion/bloodline/mentorship.

## Scenario
All relationship map content is correct and follows all skill rules. No missing evolution plans, no data duplication, no missing character references.

## Agent Task
Run shenbi-relationship-map quality check on the existing output. Expected result: report zero issues.
