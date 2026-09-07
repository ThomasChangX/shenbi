# Bug-Hunt Test: shenbi-intent-management

## Skill Under Test
`skills/shenbi-intent-management/SKILL.md`

## Test Setup
A novel project has the following state:
- The human author has provided intent input: "Focus on developing the protagonist's awakening arc; keep the tension between self-interest and conscience."
- Drift guidance at `tests/fixtures/pending-hooks-example.md` carries hook-tracking items about pacing and unresolved threads.
- `tests/fixtures/author-intent-example.md` contains the human's overall creative vision and preferences.
- The agent runs shenbi-intent-management to update `tests/fixtures/author-intent-example.md`.

## Scenario
The output at `tests/fixtures/author-intent-example.md` retains the human's declared constraints — the 创作约束 section still lists "1条副线：与老政委的师徒关系" and "1条情感线：对底层人民的共情觉醒" — but the update also appends a second emotional line (a romantic subplot for the protagonist and a secondary character) that appears in no human input, drift guidance, or prior intent file. The AI generated this creative direction autonomously, expanding the human's explicitly budgeted thread count.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/author-intent-example.md`: 创作约束 section | Human sovereignty violation — human constraints budget exactly "1条副线：与老政委的师徒关系" and "1条情感线：对底层人民的共情觉醒", but the AI update appends an extra romance subplot line that originates from no human input or drift guidance; the AI is making a creative decision rather than only organizing human input | error |

## Agent Task
Run shenbi-intent-management quality check on the intent output. The agent must detect that a creative suggestion was added by the AI that does not originate from human input.
