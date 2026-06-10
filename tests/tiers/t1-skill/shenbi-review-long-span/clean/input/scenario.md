# Clean Test: shenbi-review-long-span

## Skill Under Test
`skills/shenbi-review-long-span/SKILL.md`

## Test Setup
A novel project exists with 8 drafted chapters. The long-span audit covers the last 5 chapters (chapters 4-8). All 6-char n-gram repetition rates are within acceptable thresholds. No phrase repeats excessively across chapters.

## Scenario
No defects. All n-gram repetition rates are below the threshold. Prose is varied across chapters.

## Agent Task
Run shenbi-review-long-span audit on the last 5 chapters. Expected: report zero issues.
