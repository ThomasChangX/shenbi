# Bug-Hunt Test: shenbi-story-architecture

## Skill Under Test
`skills/shenbi-story-architecture/SKILL.md`

## Test Setup
A novel project exists with story architecture output:
- `tests/fixtures/chapter-plan-example.md` — narrative prose story frame with conflict layers
- `tests/fixtures/chapter-plan-example.md` — objectives and key results for the story
- `tests/fixtures/outline-example.md` — volume structure
- `tests/fixtures/pending-hooks-example.md` — foreshadowing lines

## Scenario
The story architecture has been generated. Upon review of the chapter memo (the objectives/key-results carrier), one information-change goal is vague and unmeasurable: the 章末必须发生的改变 section states the protagonist learns the debt is "金额不明确但明显是他无法靠常规劳动偿还的数字" — no concrete figure, no verifiable criterion, no chapter-range mapping. This violates the executability requirement that key results be measurable.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: 章末必须发生的改变 section | Unmeasurable key result — the goal is stated as "金额不明确但明显是他无法靠常规劳动偿还的数字" with no concrete criterion and no chapter range mapping | error |

## Agent Task
Run shenbi-story-architecture quality check on the existing architecture output. The agent must detect the vague, unmeasurable Key Result.
