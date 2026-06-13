# Generative Test: shenbi-review-character

## Skill Under Test
`skills/shenbi-review-character/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 10 at `tests/fixtures/chapter-draft-example.md`. Character truth files are at `tests/fixtures/character-profile-example.md`. The project has chapter summaries at `tests/fixtures/chapter-summaries-example.md`.

## Agent Task
Run shenbi-review-character audit on chapter 10. Produce a complete character audit report including:
1. BDI coverage for all speaking/acting characters
2. Character behavior consistency check against profiles
3. Dialogue-authenticity assessment per speaker

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, character profiles from `tests/fixtures/character-profile-example.md`, chapter summaries from `tests/fixtures/chapter-summaries-example.md`
