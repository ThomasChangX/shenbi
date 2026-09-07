# Bug-Hunt Test: shenbi-review-texture

## Skill Under Test
`skills/shenbi-review-texture/SKILL.md`

## Test Setup
A novel project exists with the drafted first chapter at `tests/fixtures/chapter-draft-example.md`. The chapter contains a dialogue paragraph (行68, the neighbor's speech) that reads: "觉醒检测过了，灵质海亲和度测了，基础修炼课程上了，钱借了，然后到期了。" Five parallel procedural clauses chained on 了-endings with a single 然后, enumerating routine with zero conflict or tension.

## Scenario
The agent runs a texture audit on the chapter. The audit report at `tests/fixtures/audit-report-example.md` flags this line only as a character-density (了字密度) warning and never evaluates it as a texture problem: a five-clause procedural enumeration with no conflict is not identified as a laundry-list violation.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: 行68 neighbor dialogue | Laundry-list paragraph not flagged as texture — the audit records only a 了字密度 warning for the five-clause enumeration "觉醒检测过了，灵质海亲和度测了，基础修炼课程上了，钱借了，然后到期了" and never assesses its zero-conflict sequential texture | error |

## Agent Task
Run shenbi-review-texture audit on the chapter. Find the planted defect where a laundry-list paragraph is only treated as a word-density issue rather than a texture violation.
