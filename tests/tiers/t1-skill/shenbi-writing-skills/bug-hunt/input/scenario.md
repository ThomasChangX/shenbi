# Bug-Hunt Test: shenbi-writing-skills

## Skill Under Test
`skills/shenbi-writing-skills/SKILL.md`

## Test Setup
A novel project exists. The agent has used shenbi-writing-skills to create a new skill at `skills/custom-scene-transition/SKILL.md` for managing scene transitions in the novel.

## Scenario
The newly created skill at `skills/custom-scene-transition/SKILL.md` has been generated. The skill contains the following defects:

1. **Weak iron laws using "should"**: The skill's iron laws section contains rules written with non-absolute language instead of the required MUST/NEVER/ALWAYS:
   - "You should always confirm the emotional state before transitioning" (should instead of MUST)
   - "It is recommended that scene transitions include a sensory anchor" (recommended instead of MUST)
   - "Prefer to avoid abrupt POV shifts mid-scene" (prefer instead of NEVER)
   - "Writers should not leave readers confused about time jumps" (should not instead of MUST NOT/NEVER)

2. **Missing anti-rationalization table**: The skill has a DOT flowchart and red flag checklist, but the anti-rationalization table is entirely absent.

3. **Description describes what the skill does**: The frontmatter description reads: "Creates smooth scene transitions by managing emotional states, sensory anchors, and temporal markers between scenes." This describes what the skill does, not when to trigger it. The description should describe only the trigger condition (e.g., "When a scene ends and the next scene begins with a change in time, location, or POV").

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `skills/custom-scene-transition/SKILL.md`: iron laws section | Iron laws use non-absolute language — "should," "recommended," "prefer" instead of MUST/NEVER/ALWAYS | error |
| `skills/custom-scene-transition/SKILL.md`: full document | Missing anti-rationalization table — required component absent from skill | error |
| `skills/custom-scene-transition/SKILL.md`: frontmatter description | Description describes what skill does ("Creates smooth scene transitions by...") instead of when to use it | error |

## Agent Task
Run shenbi-writing-skills quality check on the newly created skill. The agent must detect the weak iron law language, the missing anti-rationalization table, and the description trap.
