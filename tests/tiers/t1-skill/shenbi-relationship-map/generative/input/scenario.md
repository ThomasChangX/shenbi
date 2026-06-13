# Generative Test: shenbi-relationship-map

## Skill Under Test
`skills/shenbi-relationship-map/SKILL.md`

## Test Setup
A novel project exists with completed character design output. No relationship map exists yet.

## Agent Task
Run shenbi-relationship-map using the character design output as context. Produce `tests/fixtures/character-profile-example.md` with a complete relationship matrix. Ensure every relationship is traceable to interest/emotion/bloodline/mentorship, information boundaries (who knows what about whom) are explicitly recorded, each relationship defines start state, turning points, and expected end state, relationship data is in relationships.md only (not duplicated in character cards), information asymmetries are tracked as dramatic tension sources, and all referenced characters exist in character files.

## Seed Input
Character output produced by shenbi-character-design from `tests/fixtures/outline-example.md`
