# Bug-Hunt Test: shenbi-world-extraction

## Skill Under Test
`skills/shenbi-world-extraction/SKILL.md`

## Test Setup
A fantasy novel manuscript with 20 chapters has been analyzed. The world extraction skill has been run, producing `world/story_bible.md`, `world/rules.md`, `world/locations.md`, `world/factions.md`, and `world/power_system.md`.

## Scenario
The world extraction has been completed. However, a critical evidence threshold violation exists:

1. **Insufficient evidence citations**: The rule "Mana depletion causes unconsciousness after prolonged casting" at `world/rules.md` has only 1 evidence citation (chapter 12, paragraph 3). The SKILL.md requires >=2 independent textual evidence citations per rule. There is actually a second supporting passage in chapter 7, paragraph 15 where a side character collapses after extended spell use, but it was not cited.

2. **Missing violation-based inference**: All world rules in `world/rules.md` are derived solely from successful uses of the magic system. No rules are inferred from failures, near-misses, or avoidances. For example, the protagonist avoids casting in chapter 5 when exhausted — this behavioral avoidance implies a cost/risk rule but was not captured.

3. **story_bible.md format violation**: The story bible at `world/story_bible.md` is written as a bulleted reference list (12 bullet points) instead of the required 4-paragraph narrative prose format.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `world/rules.md`: mana depletion rule | Rule evidence threshold violation — only 1 citation instead of required >=2; second evidence passage in chapter 7.15 exists but was not cited | error |
| `world/rules.md`: all rules section | Violation-based inference missing — all rules derived from successful magic use only; no rules inferred from failures or avoidances | error |
| `world/story_bible.md` | Prose format violation — bulleted reference list instead of required 4-paragraph narrative prose | error |

## Agent Task
Run shenbi-world-extraction quality check on the extracted world files. The agent must detect the insufficient evidence citation, the missing violation-based inference, and the format violation in the story bible.
