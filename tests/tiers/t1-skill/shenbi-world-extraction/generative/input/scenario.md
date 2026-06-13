# Generative Test: shenbi-world-extraction

## Skill Under Test
`skills/shenbi-world-extraction/SKILL.md`

## Test Setup
A fantasy novel manuscript with 18 chapters has been analyzed. Import analysis output exists at `tests/fixtures/report-example.txt`. No world files have been generated yet.

## Agent Task
Run shenbi-world-extraction on the analyzed manuscript. The agent must:
1. Read tests/fixtures/report-example.txt and source chapters for location/faction/power references
2. Extract world rules with >=2 independent textual evidence citations per rule
3. Include violation-based inference — rules from failures and avoidances, not just successes
4. Build complete power system: level names, advancement conditions, ability boundaries, costs
5. Extract top locations with atmosphere, function, and first appearance
6. Write story_bible.md as exactly 4-paragraph narrative prose (not bullet list)
7. Write rules.md as structured format with evidence sections
8. Ensure no contradictions between extracted rules and story bible

## Seed Input
Analyzed manuscript at `tests/fixtures/report-example.txt` with source `tests/fixtures/chapter-draft-example.md` (18 chapters)
