# Clean Test: shenbi-review-pov

## Skill Under Test
`skills/shenbi-review-pov/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 7 at `drafts/chapter-7.md`. The chapter is in third-person limited POV from 林墨's perspective. Every piece of knowledge the POV character displays has a verified acquisition channel — either witnessed directly, told by another character in a scene where 林墨 was present, or established in prior chapters.

## Scenario
No defects. All POV character knowledge has legitimate acquisition channels. No information leakage.

## Agent Task
Run shenbi-review-pov audit on chapter 7. Expected: report zero issues.
