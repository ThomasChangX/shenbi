# Clean Test: shenbi-review-dialogue

## Skill Under Test
`skills/shenbi-review-dialogue/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 4 at `tests/fixtures/chapter-draft-example.md`. Voice profiles at `tests/fixtures/truth/character_profiles/` define all speaking characters with distinct patterns. Every character's dialogue matches their voice profile baseline — sentence length, vocabulary range, and sentence patterns are consistent.

## Scenario
No defects. All dialogue lines match their respective voice_profile baselines. Sentence lengths, vocabulary, and patterns are correct for each speaker.

## Agent Task
Run shenbi-review-dialogue audit on chapter 4. Expected: report zero issues.
