# Bug-Hunt Test: shenbi-character-design

## Skill Under Test
`skills/shenbi-character-design/SKILL.md`

## Test Setup
A novel project exists with character design output in `characters/`:
- `characters/protagonist.md` — protagonist profile with voice markers
- `characters/antagonist.md` — antagonist profile with voice markers
- `characters/mentor.md` — mentor character with voice markers
- `characters/relationships.md` — relationship matrix

## Scenario
The character design output has been generated. Upon review, two major characters share identical dialogue markers — their speech patterns are indistinguishable. The protagonist and the mentor both use the same sentence structures, same rhetorical tics, and same vocabulary register. This violates the voice distinctness requirement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `characters/protagonist.md` and `characters/mentor.md`: voice profile sections | Protagonist and mentor share identical speech markers: both use "short declarative sentences with rhetorical questions", same filler word "well", same register (informal), same sentence-length pattern | error |

## Agent Task
Run shenbi-character-design quality check on the existing character output. The agent must detect that two characters have indistinguishable voice profiles.
