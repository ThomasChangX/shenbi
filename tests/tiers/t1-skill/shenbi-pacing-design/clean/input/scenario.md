# Clean Test: shenbi-pacing-design

## Skill Under Test
`skills/shenbi-pacing-design/SKILL.md`

## Test Setup
A novel project exists with complete, correct pacing design:
- `tests/fixtures/chapter-plan-example.md` — every cycle has all four beats (buildup/escalation/explosion/aftermath), QUEST/FIRE/CONSTELLATION ratios all present, no more than 3 consecutive chapters of same type, pacing matches genre expectations
- `tests/fixtures/chapter-plan-example.md` — 6-8 scene types defined with explicit detection criteria

All pacing cycles are complete. The three-line balance is maintained. Monotony prevention rules are followed.

## Scenario
All pacing design content is correct and follows all skill rules. No missing beats, no monotony violations, no missing scene types.

## Agent Task
Run shenbi-pacing-design quality check on the existing output. Expected result: report zero issues.
