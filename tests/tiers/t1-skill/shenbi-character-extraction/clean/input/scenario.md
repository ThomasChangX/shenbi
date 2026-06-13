# Clean Test: shenbi-character-extraction

## Skill Under Test
`skills/shenbi-character-extraction/SKILL.md`

## Test Setup
A novel manuscript with 15 chapters has been analyzed. The character extraction has been correctly run, producing character cards at `tests/fixtures/characters/` and `tests/fixtures/character-profile-example.md`.

All output is correct:
- Every personality tag has >=1 quoted passage with chapter.paragraph reference
- Every speech pattern section contains statistical extraction from actual dialogue
- Every character arc has chapter-specific behavioral evidence for start and turning points
- No fabricated traits; all non-derivable items marked "unconfirmed"
- All named character pairs with interaction scenes have relationship entries

## Scenario
All character extraction output is correct and follows all skill rules.

## Agent Task
Run shenbi-character-extraction quality check on the extracted character cards. Expected result: report zero issues.
