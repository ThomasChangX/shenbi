# Generative Test: shenbi-review-reader-pull

## Skill Under Test
`skills/shenbi-review-reader-pull/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 16 at `tests/fixtures/chapter-draft-example.md`.

## Agent Task
Run shenbi-review-reader-pull audit on chapter 16. Produce a complete reader-pull audit report including:
1. Opening hook type classification and strength assessment
2. Mid-chapter traction point count at 800-1200 word intervals
3. Chapter-end suspense type classification
4. Overall reader-pull score

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`
