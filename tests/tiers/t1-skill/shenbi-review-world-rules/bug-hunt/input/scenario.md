# Bug-Hunt Test: shenbi-review-world-rules

## Skill Under Test
`skills/shenbi-review-world-rules/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 5 at `drafts/chapter-5.md`. Truth files include character profiles at `truth/character_profiles/lin-mo.md` which records character 林墨's age as 17. The chapter text at paragraph 4 states: "林墨，今年二十五岁的小伙子，站在门口..."

## Scenario
The agent runs a world-rules audit on chapter 5. The audit report at `audit/world-rules-review-ch5.md` does not flag the age discrepancy. The truth file says 林墨 is 17, but the chapter text says 25. The audit misses this numerical contradiction entirely.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `drafts/chapter-5.md`: paragraph 4 | Character age mismatch — text says "二十五岁" (25) but truth file `truth/character_profiles/lin-mo.md` field `age` says 17; audit report does not catch this | error |

## Agent Task
Run shenbi-review-world-rules audit on chapter 5. Find the planted defect where a character's age in the text contradicts the truth file.
