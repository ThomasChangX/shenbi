# Clean Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A novel project exists with a complete, correct worldbuilding output:
- `world/rules.md` — hard rules are mutually consistent, soft rules clearly labeled
- `world/story_bible.md` — narrative prose paragraphs, no bullet-point lists
- `world/map.md` — geographical overview with consistent distances
- `world/undercurrent.md` — seeds ≥3 future conflict sources

All hard rules are concrete and testable. Each fact appears in exactly one canonical file. The structure supports long-term serialization.

## Scenario
All worldbuilding content is correct and follows all skill rules. No contradictions, no duplicates, no format violations.

## Agent Task
Run shenbi-worldbuilding quality check on the existing output. Expected result: report zero issues.
