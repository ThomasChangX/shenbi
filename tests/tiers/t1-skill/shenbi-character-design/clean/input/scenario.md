# Clean Test: shenbi-character-design

## Skill Under Test
`skills/shenbi-character-design/SKILL.md`

## Test Setup
A novel project exists with complete, correct character design output:
- `tests/fixtures/character-profile-example.md` — unique voice markers, full arc (start/turning point/end), surface goals and deep motivations, explicit fears
- `tests/fixtures/character-profile-example.md` — distinct voice, independent motivation, explicit fears
- `tests/fixtures/character-profile-example.md` — distinct voice from protagonist, agency, explicit fears
- `tests/fixtures/characters/supporting/*.md` — minor characters with independent motivation and agency
- `tests/fixtures/character-profile-example.md` — coherent relationship matrix consistent with profiles

All characters have distinct voice profiles, grounded fears, and properly defined arcs. The relationship matrix is consistent with character profiles.

## Scenario
All character content is correct and follows all skill rules. No voice collisions, no missing arcs, no shallow motivations.

## Agent Task
Run shenbi-character-design quality check on the existing output. Expected result: report zero issues.
