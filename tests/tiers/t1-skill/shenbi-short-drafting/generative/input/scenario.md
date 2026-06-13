# Generative Test: shenbi-short-drafting

## Skill Under Test
`skills/shenbi-short-drafting/SKILL.md`

## Test Setup
A short novel project has a completed outline at `tests/fixtures/short-story-map-example.md` (see frontmatter `chapters:` field for chapter count), `tests/fixtures/author-intent-example.md`, `tests/fixtures/genre-config-example.json`, and `tests/fixtures/style-profile-example.md`. No chapters have been drafted yet.

## Agent Task
Run shenbi-short-drafting for the project. The agent must:
1. Generate all chapters defined in the outline, strictly in sequential order
2. Run all audit checks on each chapter before accepting it
3. Maintain cross-chapter consistency: position, timeline, information, relationships, style
4. Cap revisions at 3 rounds per chapter; fall back to best version if needed
5. Produce a batch summary with per-chapter status table (word count, audit result, revision rounds)

## Seed Input
Outline at `tests/fixtures/short-story-map-example.md` (chapter count defined in fixture frontmatter)
