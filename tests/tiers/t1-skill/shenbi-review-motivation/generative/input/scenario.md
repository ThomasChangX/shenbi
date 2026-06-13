# Generative Test: shenbi-review-motivation

## Skill Under Test
`skills/shenbi-review-motivation/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 12 at `tests/fixtures/chapter-draft-example.md`. Character profiles at `tests/fixtures/character-profile-example.md` define character motivations.

## Agent Task
Run shenbi-review-motivation audit on chapter 12. Produce a complete motivation audit report including:
1. Causal chain reconstruction for each major action
2. Trigger → judgment → action → consequence verification
3. Missing link detection
4. Character motivation consistency check

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, character profiles from `tests/fixtures/character-profile-example.md`
