# Generative Test: shenbi-short-drafting

## Skill Under Test
`skills/shenbi-short-drafting/SKILL.md`

## Test Setup
A short novel project (10 chapters) has a completed outline at `outline/short_story_map.md`, `truth/author_intent.md`, `genre-config.json`, and `style/style_profile.md`. No chapters have been drafted yet.

## Agent Task
Run shenbi-short-drafting for the project. The agent must:
1. Generate all 10 chapters strictly in sequential order
2. Run all audit checks on each chapter before accepting it
3. Maintain cross-chapter consistency: position, timeline, information, relationships, style
4. Cap revisions at 3 rounds per chapter; fall back to best version if needed
5. Produce a batch summary with per-chapter status table (word count, audit result, revision rounds)

## Seed Input
Outline at `outline/short_story_map.md` (10-chapter short novel)
