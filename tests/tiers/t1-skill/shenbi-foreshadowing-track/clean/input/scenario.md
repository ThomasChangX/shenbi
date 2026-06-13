# Clean Test: shenbi-foreshadowing-track

## Skill Under Test
`skills/shenbi-foreshadowing-track/SKILL.md`

## Test Setup
A novel project exists with correct foreshadowing tracking output for chapter 10 in `tests/fixtures/pending-hooks-example.md`:
- All 8 active hooks have been assessed in the tracking report — none skipped
- Each state transition includes specific textual evidence from chapter 10
- Core hooks (core_hook: true) are maintained — none abandoned
- 2 hooks approaching max_distance are correctly flagged as nearing expiry
- Density budget is clearly reported: 6 of 8 operations used, 2 deferred items listed

## Scenario
All foreshadowing tracking content is correct and follows all skill rules. No skipped hooks, no abandoned core hooks, no missing evidence.

## Agent Task
Run shenbi-foreshadowing-track quality check on the existing tracking output. Expected result: report zero issues.
