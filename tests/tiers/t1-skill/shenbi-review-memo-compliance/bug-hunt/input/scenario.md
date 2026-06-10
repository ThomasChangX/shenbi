# Bug-Hunt Test: shenbi-review-memo-compliance

## Skill Under Test
`skills/shenbi-review-memo-compliance/SKILL.md`

## Test Setup
A novel project exists with chapter memo at `plans/chapter-7-plan.md` and drafted chapter 7 at `drafts/chapter-7.md`. The memo has 8 sections. Section "key_scenes" lists 4 required scenes:
1. Protagonist enters the abandoned temple
2. Discovery of the hidden chamber
3. Confrontation with the guardian spirit
4. Escape through the underground river

The drafted chapter only contains scenes 1 and 2. Scenes 3 and 4 are missing — there is no confrontation with the guardian spirit and no escape through the underground river.

## Scenario
The agent runs a memo-compliance audit on chapter 7. The audit report at `audit/memo-compliance-ch7.md` rates section "key_scenes" as "fulfill" — marking it as fully completed. However, only 2 of 4 required scenes are present. The section should be rated "partial" since 2 of 4 items are missing.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/memo-compliance-ch7.md`: key_scenes section verdict | Section "key_scenes" marked as "fulfill" but only 2 of 4 required scenes present (confrontation with guardian spirit and escape through underground river are missing) | error |

## Agent Task
Run shenbi-review-memo-compliance audit on chapter 7. Find the planted defect where a memo section's verdict is inflated from "partial" to "fulfill".
