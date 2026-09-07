# Bug-Hunt Test: shenbi-review-foreshadowing

## Skill Under Test
`skills/shenbi-review-foreshadowing/SKILL.md`

## Test Setup
A novel project exists with drafted chapters at `tests/fixtures/chapter-draft-example.md` and `tests/fixtures/chapter-draft-example.md`. The foreshadowing pool at `tests/fixtures/pending-hooks-example.md` tracks hook states: PLANTED, ADVANCED, RESOLVED, ABANDONED. A hook "hook-ch1-002" was PLANTED in chapter 1 (the protagonist senses a low-frequency hum in the air that others do not seem to notice — chapter 1, paragraph 26).
In chapter 2, the perception strengthens at the chapter end ("手掌上的酥麻感又强了一点"), advancing the hook.

## Scenario
The agent runs a foreshadowing audit on chapters 1-2. The audit report at `tests/fixtures/audit-report-example.md` records the Hook 植入 check as PASS with the note "hook-ch1-001/002/003 全部植入". However, the entry carries no text evidence — no chapter citation and no specific prose passage is listed for any hook. The report never cites which paragraph or prose passage shows each hook's state in the text.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/audit-report-example.md`: Hook 植入 row | Hook verification lacks text evidence — PASS note "hook-ch1-001/002/003 全部植入" cites no chapter/paragraph or prose passage for any hook's state | error |

## Agent Task
Run shenbi-review-foreshadowing audit on chapters 1-2. Find the planted defect where hook state evidence is missing from the audit.
