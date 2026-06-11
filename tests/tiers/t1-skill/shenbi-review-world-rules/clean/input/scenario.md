# Clean Test: shenbi-review-world-rules

## Skill Under Test
`skills/shenbi-review-world-rules/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 7 at `drafts/chapter-7.md`. Truth files include all character profiles, world rules, and numerical data. Every numerical claim in the chapter (ages, dates, distances, counts) matches the truth files exactly.

## Scenario
No defects. All numerical claims in the chapter are consistent with truth files. All world rules are followed.

## Agent Task
Run shenbi-review-world-rules audit on chapter 7. Expected: report zero issues.
