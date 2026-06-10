# Clean Test: shenbi-review-pacing

## Skill Under Test
`skills/shenbi-review-pacing/SKILL.md`

## Test Setup
A novel project exists with 6 drafted chapters. Rhythm principles defined at `truth/rhythm_principles.md`. All last 5 chapters (chapters 2-6) are correctly classified as QUEST/FIRE/CONSTELLATION per their content and the definitions in rhythm_principles.md.

## Scenario
No defects. All chapter type classifications are correct. Pacing rhythm balance is appropriate.

## Agent Task
Run shenbi-review-pacing audit on the last 5 chapters. Expected: report zero issues.
