# Clean Test: shenbi-review-fanfic

## Skill Under Test
`skills/shenbi-review-fanfic/SKILL.md`

## Test Setup
A fanfic novel project exists with `tests/fixtures/novel-example.json` declaring `fanfic_mode: "Canon"`. Drafted chapter 3 at `tests/fixtures/chapter-draft-example.md`. All character behaviors are consistent with the source material. No character deviations from canon.

## Scenario
No defects. All character behaviors match the source material in Canon mode. No deviations, no severity misclassifications.

## Agent Task
Run shenbi-review-fanfic audit on chapter 3. Expected: report zero issues.
