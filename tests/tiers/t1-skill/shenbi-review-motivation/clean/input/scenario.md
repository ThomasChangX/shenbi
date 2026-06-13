# Clean Test: shenbi-review-motivation

## Skill Under Test
`skills/shenbi-review-motivation/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 6 at `tests/fixtures/chapter-draft-example.md`. Character profiles at `tests/fixtures/truth/character_profiles/` define character motivations. Every major action in the chapter has a complete causal chain: trigger → judgment → action → consequence.

## Scenario
No defects. All major character actions have complete causal chains. Every action has a clear trigger, judgment process, and consequence.

## Agent Task
Run shenbi-review-motivation audit on chapter 6. Expected: report zero issues.
