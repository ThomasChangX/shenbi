# Generative Test: shenbi-review-continuity

## Skill Under Test
`skills/shenbi-review-continuity/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 8-10 at `tests/fixtures/chapter-draft-example.md` (representing the full chapter range). Chapter summaries at `tests/fixtures/chapter-summaries-example.md`.

## Agent Task
Run shenbi-review-continuity audit on chapters 8-10. Produce a complete continuity audit report including:
1. Timeline extraction with all time markers listed
2. Cross-chapter timeline comparison
3. Character continuity check
4. Setting/location continuity check
5. Object continuity check

## Seed Input
Drafted chapters from `tests/fixtures/chapter-draft-example.md` (representing the full chapter range), chapter summaries from `tests/fixtures/chapter-summaries-example.md`
