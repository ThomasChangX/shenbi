# Clean Test: shenbi-review-era

## Skill Under Test
`skills/shenbi-review-era/SKILL.md`

## Test Setup
A novel project exists with `tests/fixtures/novel-example.json` declaring the time period as Ming Dynasty. Drafted chapter 5 at `tests/fixtures/chapter-draft-example.md` uses only period-appropriate vocabulary, artifacts, and institutions. All cultural references are historically accurate for the declared time period.

## Scenario
No defects. All vocabulary, artifacts, and institutions are appropriate for the Ming Dynasty time period. No anachronisms.

## Agent Task
Run shenbi-review-era audit on chapter 5. Expected: report zero issues.
