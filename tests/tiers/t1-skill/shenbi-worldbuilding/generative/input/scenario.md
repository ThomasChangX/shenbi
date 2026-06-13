# Generative Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A new novel project has been initialized with `tests/fixtures/novel-example.json` and a seed outline. No worldbuilding files exist yet.

## Agent Task
Run shenbi-worldbuilding using the seed outline. Produce all required output files per the SKILL.md data contract: novel.json, genre-config.json, world/story_bible.md, world/rules.md, world/locations.md, and truth/ directory with empty templates (current_state.md, character_matrix.md, emotional_arcs.md, chapter_summaries.md). Ensure hard rules are concrete and mutually compatible, the story bible is narrative prose, and the undercurrent seeds at least 3 future conflict sources. Truth template frontmatter must include the fields type, category, and status.

## Seed Input
`tests/fixtures/outline-example.md`
