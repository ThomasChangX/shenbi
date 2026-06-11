# Bug-Hunt Test: shenbi-volume-outlining

## Skill Under Test
`skills/shenbi-volume-outlining/SKILL.md`

## Test Setup
A novel project exists with volume outline output:
- `story/volumes/volume-1.md` — Volume 1 outline
- `story/volumes/volume-2.md` — Volume 2 outline
- `story/volumes/volume-3.md` — Volume 3 outline

## Scenario
The volume outlines have been generated. Volume 1 and Volume 3 both end with tangible hooks that bridge to the next volume. However, Volume 2 ends cleanly with a resolved conclusion — no unresolved threads, no cliffhangers, no open questions, and no hooks pointing toward Volume 3. This violates the cross-volume bridging requirement that every volume ending must leave at least one tangible hook.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `story/volumes/volume-2.md`: ending section | No cross-volume bridge — Volume 2 ends with all threads resolved, no hooks toward Volume 3 | error |

## Agent Task
Run shenbi-volume-outlining quality check on the existing volume outlines. The agent must detect that Volume 2 has no cross-volume bridge.
