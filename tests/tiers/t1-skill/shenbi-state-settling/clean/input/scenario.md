# Clean Test: shenbi-state-settling

## Skill Under Test
`skills/shenbi-state-settling/SKILL.md`

## Test Setup
A novel project has completed chapter 20 at `drafts/chapter-20.md`. The chapter explicitly states:
- Character Su Han gains a new ability called "Spirit Echo" (stated in dialogue)
- Su Han's relationship with Mei Ling shifts from allies to rivals (stated in narration)
- The setting moves from the capital city to the northern border (stated in scene description)

The settling output at `state/chapter-20-settling.md` is fully correct:
- All three explicit changes extracted with "direct" certainty
- All 9 change categories evaluated
- Changes incrementally appended to truth files (no rewriting)
- No truth file updated before human approval gate
- Cross-references consistent (e.g., new ability reflected in character profile and ability list)
- No inferred changes recorded as direct facts

## Scenario
All state settling output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-state-settling quality check on the settling output. Expected result: report zero issues.
