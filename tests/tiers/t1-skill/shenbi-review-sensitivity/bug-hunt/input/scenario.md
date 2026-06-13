# Bug-Hunt Test: shenbi-review-sensitivity

## Skill Under Test
`skills/shenbi-review-sensitivity/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 6 at `tests/fixtures/chapter-draft-example.md`. The project's `tests/fixtures/novel-example.json` specifies `target_platform: "qidian"`. The platform fatigue list at `tests/fixtures/sensitive_words.txt` contains prohibited words including "傻逼", "白痴", and "脑残". Chapter 6 at paragraph 9 contains the sentence: "你这个白痴，怎么连这个都不懂！"

## Scenario
The agent runs a sensitivity audit on chapter 6. The audit report at `tests/fixtures/audit-report-example.md` does not flag the prohibited word "白痴" that appears in chapter 6 paragraph 9. The platform fatigue list clearly lists this word as prohibited for the Qidian platform, but the audit misses it.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraph 9 | Prohibited word "白痴" from platform fatigue list not flagged — word appears in dialogue but audit report does not catch it | error |

## Agent Task
Run shenbi-review-sensitivity audit on chapter 6. Find the planted defect where a prohibited word from the platform fatigue list is not flagged.
