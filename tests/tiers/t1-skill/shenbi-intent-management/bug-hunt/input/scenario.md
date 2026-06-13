# Bug-Hunt Test: shenbi-intent-management

## Skill Under Test
`skills/shenbi-intent-management/SKILL.md`

## Test Setup
A novel project has the following state:
- The human author has provided intent input: "Focus on developing the rivalry between Lin and Zhao; I want more tension in their interactions."
- Drift guidance at `tests/fixtures/report-example.txt` contains 3 warning-level items about pacing, sensory detail, and dialogue voice.
- `tests/fixtures/author-intent-example.md` contains the human's overall creative vision and preferences.
- The agent runs shenbi-intent-management to update `tests/fixtures/author-intent-example.md`.

## Scenario
The output at `tests/fixtures/author-intent-example.md` contains all the human-provided intent correctly, but also includes a creative suggestion that was NOT provided by the human: a P1 priority item reading "Consider introducing a romantic subplot between Lin and a secondary character to add emotional depth." This suggestion was not present in any human input, drift guidance, or author intent file. The AI generated this creative direction autonomously.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/author-intent-example.md`: P1 items section | Human sovereignty violation — AI added a creative suggestion "Consider introducing a romantic subplot between Lin and a secondary character to add emotional depth" that does not originate from any human input or drift guidance; the AI is making a creative decision rather than only organizing human input | error |

## Agent Task
Run shenbi-intent-management quality check on the current_focus.md output. The agent must detect that a creative suggestion was added by the AI that does not originate from human input.
