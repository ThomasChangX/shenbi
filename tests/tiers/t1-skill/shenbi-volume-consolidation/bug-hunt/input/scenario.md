# Bug-Hunt Test: shenbi-volume-consolidation

## Skill Under Test
`skills/shenbi-volume-consolidation/SKILL.md`

## Test Setup
A novel project has completed a volume and consolidation has been run. The consolidation report at `tests/fixtures/consolidation/volume-1/` includes a volume summary and unresolved hooks list. The hook tracking file `tests/fixtures/pending-hooks-example.md` contains the following hooks:
- hook-ch1-001 (灵能修炼贷款机制) — state: PLANTED (core_hook: true)
- hook-ch1-002 (灵能感知) — state: PLANTED
- hook-ch1-003 (外部势力暗示) — state: PLANTED

## Scenario
The consolidation report at `tests/fixtures/truth-pending_hooks-ch56.md` lists per-hook tracking rows but omits any disposition for the hook "感官维度粗糙" (P0-22) — its 文本依据 is recorded as "无独立段落" and its status remains RELEVANT, yet the report records no next action for it (no cultivation step, no escalation, no defer decision). The other tracked hooks each receive an explicit presence/absence disposition.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/truth-pending_hooks-ch56.md`: P0-22 row | Unresolved hook completeness violation — hook "感官维度粗糙" (status: RELEVANT, 文本依据 "无独立段落") receives no disposition or next action while every other hook row does | error |

## Agent Task
Run shenbi-volume-consolidation quality check on the consolidation report. The agent must detect that the RELEVANT hook P0-22 is left without any disposition in the report.
