# Bug-Hunt Test: shenbi-canon-import

## Skill Under Test
`skills/shenbi-canon-import/SKILL.md`

## Test Setup
A fanfic project is being set up in AU (alternate universe) mode based on a popular 200-episode TV drama. The canon import has been run, producing 5 section files at `import/canon/` (world.md, character.md, event.md, relationship.md, timeline.md) and a deviation list at `import/canon/deviations.md`.

## Scenario
The canon import has been completed in AU mode. However, the output contains a silent deviation:

1. **Silent deviation**: The character canon at `import/canon/character.md` changes the protagonist's core motivation from "seeking justice for their family" (original work, episode 1) to "seeking power for personal gain." This is a significant deviation from the original character, but it is NOT declared in `import/canon/deviations.md`. In AU mode, deviations are allowed but MUST be explicitly declared.

2. **Missing source citation**: The event canon at `import/canon/event.md` lists "The betrayal at the northern fortress" but does not cite the original episode number or chapter reference. Three other event entries also lack source citations.

3. **Mode mixing**: The relationship canon at `import/canon/relationship.md` preserves the original work's relationship dynamics exactly (canon-compliant mode behavior) while the character canon diverges (AU mode behavior). The mode should be consistently applied across all sections.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `import/canon/character.md`: protagonist motivation | Silent deviation — core motivation changed from "seeking justice for family" to "seeking power for personal gain" without declaration in deviations.md | error |
| `import/canon/event.md`: 4 event entries | Evidence traceability violation — 4 events lack chapter/episode/paragraph citations | error |
| `import/canon/relationship.md` vs `import/canon/character.md` | Mode fidelity violation — relationship section is canon-compliant while character section is AU; inconsistent mode application | error |

## Agent Task
Run shenbi-canon-import quality check on the canon output. The agent must detect the undeclared character deviation, the missing source citations, and the mode inconsistency between sections.
