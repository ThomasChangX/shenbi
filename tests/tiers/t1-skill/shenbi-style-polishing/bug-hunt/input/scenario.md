# Bug-Hunt Test: shenbi-style-polishing

## Skill Under Test
`skills/shenbi-style-polishing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md`. The chapter has been polished and the result is at `tests/fixtures/chapter-draft-example.md`. A polishing report is at `tests/fixtures/report-example.txt`.

## Scenario
The polishing pass on chapter 7 has been completed. The polished version at `tests/fixtures/chapter-draft-example.md` contains a content change disguised as a style improvement. Specifically:

1. **Content violation — emotional reaction changed**: In the original draft, a character (Lin Yue) reacts to betrayal with cold, calculated silence — she presses her lips together and says nothing. After polishing, her reaction is changed to: "Lin Yue felt a surge of anger and hurt, tears welling in her eyes." This changes the character's emotional behavior and the scene's emotional tone from restrained tension to overt emotional display. This is a plot/content change, not a prose style improvement.

2. **Content violation — plot event altered**: In the original draft, Lin Yue simply leaves the room after hearing the news. The polished version adds: "She slammed the door behind her, the sound echoing through the hallway." The original had no door-slamming — this alters the character's behavior and adds a physical action that changes the scene's dynamics.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: Lin Yue's reaction scene | Content changed — emotional reaction rewritten from cold silence to tearful anger, altering character behavior and scene tone | error |
| `tests/fixtures/chapter-draft-example.md`: Lin Yue's exit | Plot event altered — door-slamming action added that was not in the original draft | error |

## Agent Task
Run shenbi-style-polishing quality check comparing the original draft with the polished version. The agent must detect that polishing changed content (character emotional reaction and behavior), not just prose style.
