# Clean Test: shenbi-sequel-writing

## Skill Under Test
`skills/shenbi-sequel-writing/SKILL.md`

## Test Setup
A novel project with 30 published chapters was paused after chapter 30. A breakpoint snapshot exists at `tests/fixtures/snapshots/chapter-030/`. The sequel-writing skill has been correctly resumed.

All output is correct:
- All 6 context categories rebuilt from files
- Drift detection completed: behavioral, voice, style, and setting drift all checked
- Human intent explicitly re-confirmed before writing started
- All published chapter checksums match snapshot manifest
- Pre-writing report complete with all sections

## Scenario
All sequel writing output is correct and follows all skill rules.

## Agent Task
Run shenbi-sequel-writing quality check on the resumed writing process. Expected result: report zero issues.
