# Clean Test: shenbi-import-analysis

## Skill Under Test
`skills/shenbi-import-analysis/SKILL.md`

## Test Setup
A novel manuscript exists at `chapters/` with 12 source chapters. The 8-pass import analysis pipeline has been correctly executed, producing output at `import/analysis/` (01_parse.md through 08_state.md).

All output is correct:
- Every extracted fact has a chapter.paragraph reference
- No fabricated facts; all non-derivable items marked "unconfirmed"
- Pipeline serial/parallel dependencies strictly respected
- All 8 pass output files are non-empty
- No contradictions between pass outputs
- Chapter/word/character counts match source files exactly
- Unconfirmed items list is exhaustive

## Scenario
All import analysis output is correct and follows all skill rules.

## Agent Task
Run shenbi-import-analysis quality check on the 8-pass output. Expected result: report zero issues.
