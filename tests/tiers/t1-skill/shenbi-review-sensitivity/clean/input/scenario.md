# Clean Test: shenbi-review-sensitivity

## Skill Under Test
`skills/shenbi-review-sensitivity/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 8 at `tests/fixtures/chapter-draft-example.md`. The project's `tests/fixtures/novel-example.json` specifies `target_platform: "qidian"`. The chapter contains no prohibited words from the platform fatigue list. All content is sensitivity-compliant.

## Scenario
No defects. No prohibited words from the platform fatigue list appear. All content follows platform rules.

## Agent Task
Run shenbi-review-sensitivity audit on chapter 8. Expected: report zero issues.
