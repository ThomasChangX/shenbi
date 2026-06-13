# Generative Test: shenbi-review-spinoff

## Skill Under Test
`skills/shenbi-review-spinoff/SKILL.md`

## Test Setup
A spinoff novel project exists alongside a parent novel. The parent novel's chapter summaries at `tests/fixtures/chapter-summaries-example.md` record all events. Drafted spinoff chapter 6 at `tests/fixtures/chapter-draft-example.md`.

## Agent Task
Run shenbi-review-spinoff audit on spinoff chapter 6. Produce a complete spinoff audit report including:
1. Timeline comparison: spinoff chapter vs parent chapter for all referenced information
2. Information origin tracking from parent novel
3. Timeline leakage detection (info from parent ch > spinoff ch)
4. Spinoff consistency check against parent world

## Seed Input
Drafted spinoff chapter from `tests/fixtures/chapter-draft-example.md`, parent chapter summaries from `tests/fixtures/chapter-summaries-example.md`
