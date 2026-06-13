# Bug-Hunt Test: shenbi-review-era

## Skill Under Test
`skills/shenbi-review-era/SKILL.md`

## Test Setup
A novel project exists with `tests/fixtures/novel-example.json` declaring the time period as Ming Dynasty (明朝, 1368-1644). Drafted chapter 3 at `tests/fixtures/chapter-draft-example.md` is set in this Ming Dynasty period. At paragraph 7, a character says: "这个计划太给力了，我们点赞吧！" (This plan is too awesome, let's thumbs-up it!) — using modern internet-era slang terms "给力" and "点赞" that did not exist in the Ming Dynasty.

## Scenario
The agent runs an era audit on chapter 3. The audit report at `tests/fixtures/audit-report-example.md` does not flag the modern slang "给力" and "点赞" as anachronisms. These are clearly modern vocabulary that would not exist in a story set in the Ming Dynasty, but the audit misses them.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraph 7 | Anachronism not caught — modern slang "给力" and "点赞" appear in dialogue set in Ming Dynasty (1368-1644); these terms are modern internet-era vocabulary that did not exist in the declared time period | error |

## Agent Task
Run shenbi-review-era audit on chapter 3. Find the planted defect where modern slang appears in a historical setting without being flagged.
