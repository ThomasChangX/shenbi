# Bug-Hunt Test: shenbi-review-world-rules

## Skill Under Test
`skills/shenbi-review-world-rules/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 5 at `tests/fixtures/chapter-draft-example.md`. Truth files include character profiles at `tests/fixtures/character-profile-example.md`.
The profile's 年龄 field records "穿越时23岁（现代中国大学计算机系毕业生）".
The chapter text at `tests/fixtures/chapter-draft-example.md` L20 describes the protagonist as "他一个计算机系毕业的" whose "简历石沉大海".

## Scenario
The agent runs a world-rules audit on chapter 5. The audit report at `tests/fixtures/audit-report-example.md` admits it was performed "在无外部角色档案（truth/character_profiles/ 不存在）的情况下" — no cross-check of chapter claims against the character profile was done. If the chapter's background statements contradicted the profile's 年龄 field, the audit would miss the contradiction entirely.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: L20 background statement vs `tests/fixtures/character-profile-example.md` 年龄 field | Profile cross-check gap — chapter states the protagonist is "计算机系毕业的" but the audit, run without external character archives, never verifies this against the profile's recorded 年龄 field (穿越时23岁); any numerical contradiction would be missed | error |

## Agent Task
Run shenbi-review-world-rules audit on chapter 5. Find the planted defect where chapter claims are never cross-checked against the character profile truth file.
