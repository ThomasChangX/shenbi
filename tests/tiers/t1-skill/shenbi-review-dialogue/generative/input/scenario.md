# Generative Test: shenbi-review-dialogue

## Skill Under Test
`skills/shenbi-review-dialogue/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 12 at `tests/fixtures/chapter-draft-example.md`. Voice profiles at `tests/fixtures/character-profile-example.md` define all speaking characters.

## Agent Task
Run shenbi-review-dialogue audit on chapter 12. Produce a complete dialogue audit report including:
1. Voice fingerprint matching per speaker (sentence length, vocabulary, patterns)
2. Dialogue-authenticity assessment
3. Attribution correctness check
4. Dialogue-narrative integration quality

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, character voice profiles from `tests/fixtures/character-profile-example.md`
