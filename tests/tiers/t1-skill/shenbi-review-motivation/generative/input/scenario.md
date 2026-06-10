# Generative Test: shenbi-review-motivation

## Skill Under Test
`skills/shenbi-review-motivation/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 12 at `drafts/chapter-12.md`. Character profiles at `truth/character_profiles/` define character motivations.

## Agent Task
Run shenbi-review-motivation audit on chapter 12. Produce a complete motivation audit report including:
1. Causal chain reconstruction for each major action
2. Trigger → judgment → action → consequence verification
3. Missing link detection
4. Character motivation consistency check

## Seed Input
Drafted chapter from `drafts/chapter-12.md`, character profiles from `truth/character_profiles/`
