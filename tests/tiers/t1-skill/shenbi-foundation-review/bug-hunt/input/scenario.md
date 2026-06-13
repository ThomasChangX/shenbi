# Bug-Hunt Test: shenbi-foundation-review

## Skill Under Test
`skills/shenbi-foundation-review/SKILL.md`

## Test Setup
A novel project's foundation has been reviewed. The foundation review at `tests/fixtures/report-example.txt` evaluates the project's core setup across 5 dimensions:
1. Premise clarity (scored 18/25)
2. Core conflict strength (scored 14/30)
3. Character foundations (scored 20/25)
4. World consistency (scored 12/20)

The total score is 64/100 (sum of dimension scores). The review gives the foundation a conditional pass with the note "needs improvement in core conflict."

## Scenario
The foundation review produces a total score of 64 and fails to trigger the core-conflict veto. The core-conflict dimension scored only 14/30, which is below the 18/30 threshold. According to the skill rules, any core-conflict score below 18/30 should trigger an unconditional veto (automatic fail), regardless of the total score. However, the review output does not flag this veto and instead gives a conditional pass.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/report-example.txt`: verdict section | Threshold enforcement failure — core-conflict score is 14/30 (below 18/30 threshold) but no core-conflict veto is triggered; the review gives a conditional pass instead of an unconditional fail | error |

## Agent Task
Run shenbi-foundation-review quality check on the review output. The agent must detect that the core-conflict veto should have been triggered given the 14/30 score but was not applied.
