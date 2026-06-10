# Bug-Hunt Test: shenbi-foreshadowing-resolve

## Skill Under Test
`skills/shenbi-foreshadowing-resolve/SKILL.md`

## Test Setup
A novel project exists with foreshadowing resolution output for volume 2 end. The `truth/pending_hooks.md` file contains several hooks, including `hook-002` (师姐身世) with `chase_power: 250` and `status: TRIGGERED`. The resolution report does not list hook-002 for immediate resolution — it has been deferred to the next volume without any resolution action.

## Scenario
The foreshadowing resolution at volume 2 end has been completed. Hook-002 (师姐身世) has Chase Power of 250, which is above the 200 threshold that triggers mandatory immediate resolution. Despite this, the resolution report defers hook-002 to the next volume with no resolution action taken. This violates the iron rule that CP > 200 requires at least partial resolution in the next chapter.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `truth/pending_hooks.md`: hook-002 entry and resolution report | Hook with CP=250 (above 200 threshold) deferred without resolution — CP red zone requires mandatory immediate action | error |

## Agent Task
Run shenbi-foreshadowing-resolve quality check on the volume 2 end resolution output. The agent must detect that a high-CP hook (CP=250) was not resolved despite exceeding the 200 threshold.
