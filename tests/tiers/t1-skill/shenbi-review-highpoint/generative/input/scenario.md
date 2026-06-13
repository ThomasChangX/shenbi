# Generative Test: shenbi-review-highpoint

## Skill Under Test
`skills/shenbi-review-highpoint/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 17 at `tests/fixtures/chapter-draft-example.md`.

## Agent Task
Run shenbi-review-highpoint audit on chapter 17. Produce a complete highpoint audit report including:
1. Climax segment identification
2. Buildup level rating (1-5 scale) with text evidence
3. Payoff level rating (1-5 scale) with text evidence
4. Deflation detection (payoff < buildup)
5. Overall emotional arc assessment

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`
