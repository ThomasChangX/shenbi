# Bug-Hunt Test: shenbi-review-foreshadowing

## Skill Under Test
`skills/shenbi-review-foreshadowing/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 3 and 4 at `drafts/chapter-3.md` and `drafts/chapter-4.md`. The foreshadowing pool at `truth/foreshadowing_pool.md` tracks hook states: PLANTED, ADVANCED, RESOLVED, ABANDONED. A hook "mysterious-key" was PLANTED in chapter 3 (the protagonist finds an old key under a floorboard — chapter 3, paragraph 8). In chapter 4, the key is used to open a locked door (chapter 4, paragraph 12), advancing the hook.

## Scenario
The agent runs a foreshadowing audit on chapters 3-4. The audit report at `audit/foreshadowing-review.md` records the "mysterious-key" hook as transitioning from PLANTED to ADVANCED. However, the transition entry for the ADVANCED state has no text evidence — no chapter citation and no specific prose passage is listed. The report simply says "mysterious-key: PLANTED → ADVANCED" without citing which paragraph or prose passage in chapter 4 shows the advancement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/foreshadowing-review.md`: mysterious-key ADVANCED entry | Hook state transition PLANTED → ADVANCED has no text evidence — missing chapter citation and prose passage reference | error |

## Agent Task
Run shenbi-review-foreshadowing audit on chapters 3-4. Find the planted defect where a hook state transition lacks text evidence.
