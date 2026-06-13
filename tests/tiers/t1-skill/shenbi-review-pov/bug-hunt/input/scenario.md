# Bug-Hunt Test: shenbi-review-pov

## Skill Under Test
`skills/shenbi-review-pov/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 9 at `tests/fixtures/chapter-draft-example.md`. The chapter is written in third-person limited POV from 林墨's perspective. According to chapter summaries at `tests/fixtures/chapter-summaries-example.md`, a critical secret — that 苏晴 is secretly working for the antagonist — was revealed in a private conversation between 苏晴 and the antagonist in chapter 7. 林墨 was not present at this conversation and has no way of knowing this secret.

## Scenario
The agent runs a POV audit on chapter 9. In paragraph 6, the narrative from 林墨's perspective states: "林墨知道苏晴一直在为反派工作。" (林墨 knew that 苏晴 had been working for the antagonist all along.) However, 林墨 was never present when this information was revealed. There is no prior chapter where 林墨 learned this secret. This is an information leakage — the POV character knows something they should not know.

The audit report does not flag this information leakage.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraph 6 | Information leakage — POV character 林墨 knows 苏晴's secret alliance with the antagonist, but was never present at the revelation (ch7 private conversation); no acquisition channel exists | error |

## Agent Task
Run shenbi-review-pov audit on chapter 9. Find the planted defect where the POV character knows information they should not have access to.
