# Bug-Hunt Test: shenbi-volume-consolidation

## Skill Under Test
`skills/shenbi-volume-consolidation/SKILL.md`

## Test Setup
A novel project has completed Volume 1 (chapters 1-10). The consolidation report at `consolidation/volume-1/` includes a volume summary and unresolved hooks list. The file `truth/pending_hooks.md` contains the following hooks:
- Hook H001: "The sealed letter" — status: ACTIVE (planted in chapter 3)
- Hook H002: "The merchant's warning" — status: ACTIVE (planted in chapter 5)
- Hook H003: "The eclipse prophecy" — status: ACTIVE (planted in chapter 7)
- Hook H004: "Old mentor's disappearance" — status: RESOLVED (resolved in chapter 9)
- Hook H005: "The northern signal fire" — status: ACTIVE (planted in chapter 10)

## Scenario
The consolidation report at `consolidation/volume-1/report.md` lists the unresolved hooks but omits Hook H005 "The northern signal fire". The report only lists H001, H002, and H003 as unresolved hooks. Hook H004 is correctly excluded (it is RESOLVED). However, Hook H005 was planted in the very last chapter of the volume and is ACTIVE — it should absolutely be listed.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `consolidation/volume-1/report.md`: unresolved hooks section | Unresolved hook completeness violation — Hook H005 "The northern signal fire" (status: ACTIVE, planted chapter 10) is missing from the unresolved hooks list; only H001, H002, H003 listed | error |

## Agent Task
Run shenbi-volume-consolidation quality check on the consolidation report. The agent must detect that Hook H005 is an active, unresolved hook that is missing from the report.
