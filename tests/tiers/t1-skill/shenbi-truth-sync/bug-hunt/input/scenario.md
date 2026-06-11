# Bug-Hunt Test: shenbi-truth-sync

## Skill Under Test
`skills/shenbi-truth-sync/SKILL.md`

## Test Setup
A novel project has chapters 1-18 completed. The truth sync scope is set to chapters 15-18. The truth file at `truth/character_profiles/chen-wei.md` records:
- Chen Wei's weapon: "Twin daggers, named Shadow and Shade"
- Chen Wei's current location: "Imperial City"

Chapter 17 text states:
- Chen Wei now wields a longsword named "Dawnbreaker" (he discarded his daggers in the river during the escape)
- Chen Wei is now at the "Frozen Wasteland border camp"

The truth-sync output at `sync/truth-sync-15-18.md` correctly updates Chen Wei's location to "Frozen Wasteland border camp" but fails to detect the weapon change. The daggers entry remains unchanged — "Twin daggers, named Shadow and Shade" — even though chapter 17 explicitly describes him discarding them and picking up Dawnbreaker.

## Scenario
The truth-sync output misses a contradiction between chapter 17 text and the character profile truth file. Chen Wei's weapon has fundamentally changed (daggers discarded, longsword acquired), but the sync did not detect or flag this conflict.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `sync/truth-sync-15-18.md`: weapon field for Chen Wei | Missed conflict — chapter 17 states Chen Wei discarded twin daggers and acquired longsword "Dawnbreaker", but truth-sync output does not flag this contradiction with `truth/character_profiles/chen-wei.md` which still lists "Twin daggers, named Shadow and Shade" | error |

## Agent Task
Run shenbi-truth-sync quality check on the sync output. The agent must detect that the weapon change from chapter 17 was missed and the conflict between chapter text and the truth file was not flagged.
