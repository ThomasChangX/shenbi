# Generative Test: shenbi-short-packaging

## Skill Under Test
`skills/shenbi-short-packaging/SKILL.md`

## Test Setup
A 15-chapter short novel has been completed with all chapters at `tests/fixtures/chapters/`. The outline is at `tests/fixtures/short-story-map-example.md`, world building at `tests/fixtures/outline-example.md`, and author intent at `tests/fixtures/author-intent-example.md`. No packaging materials have been generated yet.

## Agent Task
Run shenbi-short-packaging for the project. The agent must:
1. Generate 3-5 title candidates, all semantically distinct
2. Generate 2-3 blurbs with zero act 3 spoilers
3. Extract 3-5 selling points, each citing specific chapter + paragraph
4. Generate a cover prompt with subject, scene, composition, color palette, and style keywords
5. Generate platform keywords matching the target platform tag taxonomy

## Seed Input
Completed short novel with `tests/fixtures/chapter-draft-example.md` (15 chapters) and `tests/fixtures/short-story-map-example.md`
