# Clean Test: shenbi-canon-import

## Skill Under Test
`skills/shenbi-canon-import/SKILL.md`

## Test Setup
A fanfic project is being set up in AU mode based on a popular 200-episode TV drama. The canon import has been correctly run, producing 5 section files at `tests/fixtures/import/canon/` and a deviation list at `tests/fixtures/report-example.txt`.

All output is correct:
- AU mode consistently applied across all sections
- Every canon entry cites original work (chapter/episode/paragraph)
- All deviations from original explicitly declared in deviations.md
- World, character, event, relationship, timeline sections all present and non-empty
- Mode fidelity maintained: no silent mixing of preservation and deviation

## Scenario
All canon import output is correct and follows all skill rules.

## Agent Task
Run shenbi-canon-import quality check on the canon output. Expected result: report zero issues.
